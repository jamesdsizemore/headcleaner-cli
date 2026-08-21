"""Evidence-based readiness grades (Contract 3.7).

Grades are evidence-based suitability signals: they summarise how ready a
concept is for the requested profile, but they never claim that the content
was human-reviewed and they never overwrite concept trust state.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml


MAX_SCORE: float = 1.0


DEDUCTION_ALLOW_LIST: tuple[str, ...] = (
    "citation_completeness",
    "chunk_integrity",
    "ocr_table_diagnostics",
    "redaction_state",
    "freshness",
    "policy",
    "human_review",
)


PROFILES: dict[str, dict[str, Any]] = {
    "default": {
        "description": "default suitability for general consumption",
        "thresholds": {
            "blocked_below": 0.0,
            "needs_review_below": 0.5,
            "conditional_below": 0.85,
            "ready_min": 0.85,
        },
    },
    "rag": {
        "description": "RAG/agent retrieval: prefers human-reviewed, fresh, complete citations",
        "thresholds": {
            "blocked_below": 0.0,
            "needs_review_below": 0.6,
            "conditional_below": 0.9,
            "ready_min": 0.9,
        },
    },
    "publication": {
        "description": "publication: requires human review and no redaction findings",
        "thresholds": {
            "blocked_below": 0.0,
            "needs_review_below": 0.7,
            "conditional_below": 0.95,
            "ready_min": 0.95,
        },
    },
}


_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)


@dataclass(frozen=True)
class ReadinessReport:
    concept_ref: str
    grade: str
    score: float
    deductions: list[dict[str, Any]] = field(default_factory=list)
    requirements: list[dict[str, Any]] = field(default_factory=list)
    schema_version: str = "1"


def _parse_frontmatter(text: str) -> dict[str, Any]:
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {}
    try:
        return yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        return {}


def _concepts_in_bundle(bundle_root: Path) -> list[str]:
    if not bundle_root.is_dir():
        return []
    return sorted(
        str(p.relative_to(bundle_root)).replace("\\", "/")
        for p in bundle_root.rglob("*.md")
        if p.name not in {"index.md", "log.md"}
    )


# ---------------------------------------------------------------------------
# Deductions — each starts from MAX_SCORE and subtracts documented amounts.
# Missing inputs yield deductions, never optimistic zeros.
# ---------------------------------------------------------------------------


def _deduction(
    rule_id: str, value: float, threshold: float, contribution: float, citation: str
) -> dict[str, Any]:
    return {
        "rule_id": rule_id,
        "value": value,
        "threshold": threshold,
        "contribution": contribution,
        "citation": citation,
    }


def _citation_completeness(fm: dict[str, Any]) -> dict[str, Any] | None:
    """-0.1 if the concept lacks a sources[] entry."""
    sources = fm.get("sources")
    if not isinstance(sources, list) or not sources:
        return _deduction(
            "citation_completeness", 0.0, 1.0, -0.1, "frontmatter.sources is missing"
        )
    return None


def _chunk_integrity(fm: dict[str, Any]) -> dict[str, Any] | None:
    """-0.1 if chunk_count is missing or zero."""
    cc = fm.get("chunk_count")
    if not isinstance(cc, int) or cc <= 0:
        return _deduction(
            "chunk_integrity", float(cc or 0), 1.0, -0.1, "frontmatter.chunk_count <= 0"
        )
    return None


def _ocr_table_diagnostics(fm: dict[str, Any]) -> dict[str, Any] | None:
    """-0.1 if metrics.ocr_used is true (lower fidelity)."""
    metrics = fm.get("metrics") or {}
    if not isinstance(metrics, dict):
        return None
    if metrics.get("ocr_used") is True:
        return _deduction(
            "ocr_table_diagnostics",
            1.0,
            0.0,
            -0.1,
            "metrics.ocr_used=true (OCR fallback observed)",
        )
    return None


def _redaction_state(fm: dict[str, Any]) -> dict[str, Any] | None:
    """-0.2 per redaction finding on the concept (cap at -0.4)."""
    findings = fm.get("redaction_findings")
    if not isinstance(findings, list) or not findings:
        return None
    n = len(findings)
    return _deduction(
        "redaction_state",
        float(n),
        0.0,
        float(max(-0.4, -0.2 * n)),
        f"redaction_findings count={n}",
    )


def _freshness(fm: dict[str, Any]) -> dict[str, Any] | None:
    """-0.2 if stale_after is in the past; -0.1 if missing or unparseable."""
    raw = fm.get("stale_after")
    ts: datetime | None = None
    if isinstance(raw, datetime):
        ts = raw.astimezone(UTC) if raw.tzinfo else raw.replace(tzinfo=UTC)
    elif isinstance(raw, str):
        try:
            ts = datetime.strptime(raw, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
        except ValueError:
            ts = None
    if ts is None:
        return _deduction(
            "freshness", 0.0, 1.0, -0.1, "frontmatter.stale_after missing or unparseable"
        )
    if ts < datetime.now(UTC):
        return _deduction(
            "freshness", 0.0, 1.0, -0.2, f"stale_after is in the past"
        )
    return None


def _policy(fm: dict[str, Any]) -> dict[str, Any] | None:
    """-0.3 per policy error finding (cap at -0.6)."""
    findings = fm.get("policy_findings") or []
    if not isinstance(findings, list):
        return None
    errors = [f for f in findings if isinstance(f, dict) and f.get("severity") == "error"]
    if not errors:
        return None
    n = len(errors)
    return _deduction(
        "policy",
        float(n),
        0.0,
        float(max(-0.6, -0.3 * n)),
        f"policy_findings errors count={n}",
    )


def _human_review(fm: dict[str, Any]) -> dict[str, Any] | None:
    """-0.3 if verified is missing or human:pending; 0 if human:reviewed."""
    v = fm.get("verified")
    if not isinstance(v, str):
        return _deduction(
            "human_review", 0.0, 1.0, -0.3, "frontmatter.verified missing"
        )
    if v == "human:pending":
        return _deduction("human_review", 0.0, 1.0, -0.3, "verified=human:pending")
    if v == "human:reviewed":
        return None
    return _deduction(
        "human_review", 0.0, 1.0, -0.3, f"verified value not recognised: {v!r}"
    )


_DEDUCTION_FNS = {
    "citation_completeness": _citation_completeness,
    "chunk_integrity": _chunk_integrity,
    "ocr_table_diagnostics": _ocr_table_diagnostics,
    "redaction_state": _redaction_state,
    "freshness": _freshness,
    "policy": _policy,
    "human_review": _human_review,
}


# ---------------------------------------------------------------------------
# Grade assignment
# ---------------------------------------------------------------------------


def _grade_for_score(score: float, profile: str) -> str:
    thresholds = PROFILES[profile]["thresholds"]
    if score <= thresholds["blocked_below"]:
        return "blocked"
    if score < thresholds["needs_review_below"]:
        return "blocked"
    if score < thresholds["conditional_below"]:
        return "needs_review"
    if score < thresholds["ready_min"]:
        return "conditional"
    return "ready"


def _requirements_for(deductions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """For each deduction, surface the rule + threshold + citation as a requirement."""
    return [
        {
            "rule_id": d["rule_id"],
            "value": d["value"],
            "threshold": d["threshold"],
            "citation": d["citation"],
        }
        for d in deductions
    ]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def build_report(bundle_root: Path, *, profile: str = "default") -> list[ReadinessReport]:
    if profile not in PROFILES:
        raise ValueError(f"unknown profile: {profile!r}; valid={sorted(PROFILES)}")

    reports: list[ReadinessReport] = []
    for concept_ref in _concepts_in_bundle(bundle_root):
        text = (bundle_root / concept_ref).read_text(encoding="utf-8")
        fm = _parse_frontmatter(text)
        deductions: list[dict[str, Any]] = []
        for rule_id, fn in _DEDUCTION_FNS.items():
            d = fn(fm)
            if d is not None:
                deductions.append(d)
        score = round(max(0.0, min(MAX_SCORE, MAX_SCORE + sum(d["contribution"] for d in deductions))), 9)
        grade = _grade_for_score(score, profile)
        reports.append(
            ReadinessReport(
                concept_ref=concept_ref,
                grade=grade,
                score=score,
                deductions=deductions,
                requirements=_requirements_for(deductions),
                schema_version="1",
            )
        )
    return reports


def explain_report(report: ReadinessReport) -> dict[str, Any]:
    return {
        "concept_ref": report.concept_ref,
        "grade": report.grade,
        "score": report.score,
        "deductions": list(report.deductions),
        "requirements": list(report.requirements),
        "schema_version": report.schema_version,
    }
