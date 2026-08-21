"""Tests for evidence-based readiness grades (Contract 3.7)."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path

import jsonschema
import pytest

from headcleaner.readiness import (
    DEDUCTION_ALLOW_LIST,
    MAX_SCORE,
    PROFILES,
    ReadinessReport,
    build_report,
    explain_report,
)

SCHEMA_PATH = Path("docs/schemas/readiness.schema.json")


def _concept(
    bundle: Path,
    relpath: str,
    *,
    frontmatter: dict | None = None,
    body: str = "body\n",
) -> Path:
    fm = frontmatter or {"type": "Document", "title": relpath}
    md = bundle / relpath
    md.parent.mkdir(parents=True, exist_ok=True)
    lines = ["---\n"]
    for k, v in fm.items():
        lines.append(f"{k}: {v}\n")
    lines.append("---\n")
    lines.append(body)
    md.write_text("".join(lines), encoding="utf-8")
    return md


@pytest.fixture
def bundle(tmp_path: Path) -> Path:
    b = tmp_path / "bundle"
    b.mkdir()
    # Concept A: clean, recent, no redaction, no policy errors, reviewed.
    future = (datetime.now(UTC) + timedelta(days=180)).strftime("%Y-%m-%dT%H:%M:%SZ")
    _concept(
        b,
        "alpha.md",
        frontmatter={
            "type": "Document",
            "title": "Alpha",
            "verified": "human:reviewed",
            "chunk_count": 5,
            "stale_after": future,
            "sources": '[{uri: file://inbox/a, kind: file, sha256: "' + "a" * 64 + '"}]',
        },
    )
    # Concept B: stale, pending review, has redaction findings.
    _concept(
        b,
        "beta.md",
        frontmatter={
            "type": "Document",
            "title": "Beta",
            "verified": "human:pending",
            "stale_after": (datetime.now(UTC) - timedelta(days=200)).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            ),
            "redaction_findings": '[{id: r1, category: secret}]',
            "sources": '[{uri: file://inbox/b, kind: file, sha256: "' + "b" * 64 + '"}]',
        },
    )
    return b


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


def test_grade_values_are_strictly_four() -> None:
    assert set(PROFILES.keys()) <= {"default", "rag", "publication"}


def test_max_score_is_documented_constant() -> None:
    assert MAX_SCORE == 1.0


def test_deduction_allow_list_matches_documented_fields() -> None:
    expected = {
        "citation_completeness",
        "chunk_integrity",
        "ocr_table_diagnostics",
        "redaction_state",
        "freshness",
        "policy",
        "human_review",
    }
    assert set(DEDUCTION_ALLOW_LIST) == expected


# ---------------------------------------------------------------------------
# Grade assignment
# ---------------------------------------------------------------------------


def test_clean_reviewed_concept_yields_ready(bundle: Path) -> None:
    reports = build_report(bundle)
    alpha = next(r for r in reports if r.concept_ref == "alpha.md")
    assert alpha.grade == "ready"
    assert alpha.score == pytest.approx(MAX_SCORE, abs=1e-9)
    assert isinstance(alpha.requirements, list)


def test_stale_unreviewed_concept_yields_blocked_or_needs_review(bundle: Path) -> None:
    reports = build_report(bundle)
    beta = next(r for r in reports if r.concept_ref == "beta.md")
    assert beta.grade in {"blocked", "needs_review", "conditional"}
    # The pending verified + stale_after + redaction_findings must show as deductions.
    rule_ids = {d["rule_id"] for d in beta.deductions}
    assert "freshness" in rule_ids
    assert "human_review" in rule_ids
    assert "redaction_state" in rule_ids


def test_missing_input_yields_deduction_not_optimistic(bundle: Path) -> None:
    # Strip alpha's verified field entirely.
    (bundle / "alpha.md").write_text(
        "---\ntype: Document\ntitle: Alpha\n---\nbody\n", encoding="utf-8"
    )
    reports = build_report(bundle)
    alpha = next(r for r in reports if r.concept_ref == "alpha.md")
    # Missing verified → human_review deduction; never an optimistic 'ready'.
    rule_ids = {d["rule_id"] for d in alpha.deductions}
    assert "human_review" in rule_ids
    assert alpha.grade != "ready"


def test_unknown_profile_fails_explicitly(bundle: Path) -> None:
    with pytest.raises(ValueError):
        build_report(bundle, profile="nope")


# ---------------------------------------------------------------------------
# Explainability
# ---------------------------------------------------------------------------


def test_explain_report_includes_every_deduction_with_citation(bundle: Path) -> None:
    reports = build_report(bundle)
    for r in reports:
        explanation = explain_report(r)
        assert explanation["concept_ref"] == r.concept_ref
        assert explanation["grade"] == r.grade
        assert "deductions" in explanation
        for d in explanation["deductions"]:
            assert set(d.keys()) >= {
                "rule_id",
                "value",
                "threshold",
                "contribution",
                "citation",
            }


# ---------------------------------------------------------------------------
# Determinism + schema validation
# ---------------------------------------------------------------------------


def test_report_is_deterministic(bundle: Path) -> None:
    r1 = build_report(bundle)
    r2 = build_report(bundle)
    assert [x.concept_ref for x in r1] == [x.concept_ref for x in r2]
    assert [x.grade for x in r1] == [x.grade for x in r2]


def test_report_validates_against_schema(bundle: Path) -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.Draft7Validator.check_schema(schema)
    for r in build_report(bundle):
        jsonschema.validate(explain_report(r), schema)


def test_schema_rejects_overwrite_of_verified(bundle: Path) -> None:
    """A readiness report must never carry a field that overwrites verified."""
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    bad = {
        "concept_ref": "x.md",
        "grade": "ready",
        "score": 1.0,
        "deductions": [],
        "requirements": [],
        "schema_version": "1",
        "verified_by_readiness": True,
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad, schema)


# ---------------------------------------------------------------------------
# No trust mutation
# ---------------------------------------------------------------------------


def test_build_report_does_not_modify_concept_frontmatter(bundle: Path) -> None:
    pre_alpha = (bundle / "alpha.md").read_text(encoding="utf-8")
    pre_beta = (bundle / "beta.md").read_text(encoding="utf-8")
    build_report(bundle)
    assert (bundle / "alpha.md").read_text(encoding="utf-8") == pre_alpha
    assert (bundle / "beta.md").read_text(encoding="utf-8") == pre_beta


def test_report_never_contains_reviewed_claim_for_unreviewed_input(bundle: Path) -> None:
    reports = build_report(bundle)
    beta = next(r for r in reports if r.concept_ref == "beta.md")
    explanation = explain_report(beta)
    blob = json.dumps(explanation, sort_keys=True)
    assert "verified_by_human" not in blob
    assert "human_reviewed" not in blob or "needs_human_review" in blob
