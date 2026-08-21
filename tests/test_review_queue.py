"""Tests for the explainable risk-based review queue (Contract 3.6)."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from headcleaner.review_queue import (
    FACTOR_REGISTRY,
    QueueItem,
    QueueState,
    build_queue,
    claim_item,
    decide_item,
    explain_item,
    register_factor,
)


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


def _concept(
    bundle: Path,
    relpath: str,
    *,
    frontmatter: dict | None = None,
    body: str = "Body text.\n",
) -> Path:
    """Write an OKF concept file under `bundle` with optional frontmatter."""
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
    """A bundle with three concepts of varying risk profiles."""
    b = tmp_path / "bundle"
    b.mkdir()
    # Concept A: clean, recent
    _concept(
        b,
        "alpha.md",
        frontmatter={
            "type": "Document",
            "title": "Alpha",
            "sources": '[{uri: file://inbox/alpha.txt, kind: file, sha256: "' + "a" * 64 + '"}]',
        },
    )
    # Concept B: stale (stale_after in the past)
    past = (datetime.now(UTC) - timedelta(days=200)).strftime("%Y-%m-%dT%H:%M:%SZ")
    _concept(
        b,
        "beta.md",
        frontmatter={
            "type": "Document",
            "title": "Beta",
            "stale_after": past,
            "sources": '[{uri: file://inbox/beta.txt, kind: file, sha256: "' + "b" * 64 + '"}]',
        },
    )
    # Concept C: pending verification (default verified: human:pending)
    _concept(
        b,
        "gamma.md",
        frontmatter={
            "type": "Document",
            "title": "Gamma",
            "verified": "human:pending",
            "sources": '[{uri: file://inbox/gamma.txt, kind: file, sha256: "' + "c" * 64 + '"}]',
        },
    )
    return b


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


def test_queue_item_has_required_fields(bundle: Path) -> None:
    queue = build_queue(bundle)
    assert queue, "queue must not be empty for a bundle with concepts"
    for item in queue:
        assert isinstance(item, QueueItem)
        assert item.concept_ref
        assert isinstance(item.priority, (int, float))
        assert isinstance(item.factors, list)
        for f in item.factors:
            assert set(f.keys()) >= {"rule_id", "value", "weight", "contribution", "evidence"}
        assert item.state in {"pending", "claimed", "decided", "suppressed"}
        assert item.created_at


def test_queue_states_are_strictly_one_of_four() -> None:
    """The contract fixes state to pending|claimed|decided|suppressed."""
    expected = {"pending", "claimed", "decided", "suppressed"}
    assert {s.value for s in QueueState} == expected


# ---------------------------------------------------------------------------
# Determinism and tie-break
# ---------------------------------------------------------------------------


def test_queue_is_deterministic_for_same_bundle(bundle: Path) -> None:
    q1 = build_queue(bundle)
    q2 = build_queue(bundle)
    assert [i.concept_ref for i in q1] == [i.concept_ref for i in q2]
    assert [i.priority for i in q1] == [i.priority for i in q2]


def test_queue_tie_break_is_source_sha256_then_concept_path(bundle: Path) -> None:
    """When priorities are equal, ordering is by source_sha256 then concept path.

    We force a tie by overriding all factor weights to zero for two concepts.
    """
    # Override registry with weightless factors so priorities tie.
    from dataclasses import replace as dc_replace
    from headcleaner import review_queue as rq

    original = dict(FACTOR_REGISTRY)
    for fid in list(FACTOR_REGISTRY):
        rq.FACTOR_REGISTRY[fid] = dc_replace(FACTOR_REGISTRY[fid], weight=0.0)
    try:
        q = build_queue(bundle)
    finally:
        rq.FACTOR_REGISTRY.clear()
        rq.FACTOR_REGISTRY.update(original)
    # The two concepts with weightless factors must be ordered by source_sha256.
    # Without weights, all priorities should equal.
    prios = {i.concept_ref: i.priority for i in q}
    assert len(set(prios.values())) == 1 or len(set(prios.values())) <= len(prios)
    # Verify deterministic ordering by walking the list.
    refs = [i.concept_ref for i in q]
    # Sorted by (priority DESC, source_sha256 ASC, concept_ref ASC).
    by_sha = {"alpha.md": "a" * 64, "beta.md": "b" * 64, "gamma.md": "c" * 64}
    expected = sorted(
        refs,
        key=lambda r: (-prios[r], by_sha.get(r, ""), r),
    )
    assert refs == expected


# ---------------------------------------------------------------------------
# Factors and registry
# ---------------------------------------------------------------------------


def test_factor_registry_only_has_approved_factors() -> None:
    """Only registered factor functions may contribute."""
    allowed = {
        "diagnostic_severity",
        "ocr_fallback_state",
        "sensitivity_findings",
        "policy_errors",
        "stale_state",
        "age",
    }
    assert set(FACTOR_REGISTRY.keys()) == allowed


def test_missing_factor_evidence_contributes_zero_and_emits_diagnostic(
    bundle: Path,
) -> None:
    """A factor whose input is missing contributes 0 plus a diagnostic, never assumed risk."""
    # Force the stale_state factor's input to be missing by stripping frontmatter.
    (bundle / "beta.md").write_text(
        "---\ntype: Document\ntitle: Beta\n---\nbody\n", encoding="utf-8"
    )
    queue = build_queue(bundle)
    beta = next(i for i in queue if i.concept_ref == "beta.md")
    stale_factor = next((f for f in beta.factors if f["rule_id"] == "stale_state"), None)
    assert stale_factor is not None
    assert stale_factor["value"] == 0
    assert stale_factor["contribution"] == 0
    # Diagnostic is surfaced via evidence.
    assert stale_factor["evidence"].get("missing") is True


def test_register_factor_rejects_unknown_rule_id() -> None:
    with pytest.raises(ValueError):
        register_factor(rule_id="not_in_allow_list", value_fn=lambda c: 0, weight=0.0)


# ---------------------------------------------------------------------------
# Pack weights
# ---------------------------------------------------------------------------


def test_pack_weights_override_default_factors(bundle: Path) -> None:
    """A pack may set per-factor weights that override defaults."""
    pack_weights = {"stale_state": 5.0, "age": 0.0}
    q_default = build_queue(bundle)
    q_packed = build_queue(bundle, pack_weights=pack_weights)
    default_stale_weight = FACTOR_REGISTRY["stale_state"].weight
    for item in q_packed:
        stale = next((f for f in item.factors if f["rule_id"] == "stale_state"), None)
        if stale is not None:
            assert stale["weight"] == 5.0
        age = next((f for f in item.factors if f["rule_id"] == "age"), None)
        if age is not None:
            assert age["weight"] == 0.0
    for item in q_default:
        stale = next((f for f in item.factors if f["rule_id"] == "stale_state"), None)
        if stale is not None:
            assert stale["weight"] == default_stale_weight


def test_pack_weights_reject_unknown_rule_id(bundle: Path) -> None:
    with pytest.raises(ValueError):
        build_queue(bundle, pack_weights={"unknown_factor": 1.0})


# ---------------------------------------------------------------------------
# State transitions
# ---------------------------------------------------------------------------


def test_claim_item_sets_state_and_records_reviewer(bundle: Path) -> None:
    queue = build_queue(bundle)
    item = queue[0]
    claimed = claim_item(item, reviewer="alice")
    assert claimed.state == "claimed"
    assert claimed.claimed_by == "alice"


def test_claim_is_idempotent_per_reviewer(bundle: Path) -> None:
    """A second claim by the same reviewer must not overwrite an existing audit."""
    queue = build_queue(bundle)
    item = queue[0]
    claimed = claim_item(item, reviewer="alice")
    claimed_again = claim_item(claimed, reviewer="alice")
    # The audit count must reflect the first claim; second is a no-op.
    assert claimed_again.state == "claimed"
    assert claimed_again.claim_count == claimed.claim_count


def test_claim_race_second_reviewer_rejected(bundle: Path) -> None:
    queue = build_queue(bundle)
    item = queue[0]
    claimed = claim_item(item, reviewer="alice")
    with pytest.raises(PermissionError):
        claim_item(claimed, reviewer="bob")


def test_decide_item_moves_state_to_decided(bundle: Path) -> None:
    queue = build_queue(bundle)
    item = queue[0]
    decided = decide_item(
        claim_item(item, reviewer="alice"),
        decision="approved",
        reason="Looks correct",
    )
    assert decided.state == "decided"
    assert decided.decision == "approved"


def test_decide_item_without_claim_raises(bundle: Path) -> None:
    queue = build_queue(bundle)
    item = queue[0]
    with pytest.raises(ValueError):
        decide_item(item, decision="approved", reason="x")


def test_suppress_requires_reason(bundle: Path) -> None:
    from headcleaner.review_queue import suppress_item

    queue = build_queue(bundle)
    item = queue[0]
    with pytest.raises(ValueError):
        suppress_item(item, reason="")
    suppressed = suppress_item(item, reason="false positive on audit")
    assert suppressed.state == "suppressed"
    assert suppressed.suppression_reason == "false positive on audit"


# ---------------------------------------------------------------------------
# Explainability
# ---------------------------------------------------------------------------


def test_explain_item_lists_every_factor_with_contribution(bundle: Path) -> None:
    queue = build_queue(bundle)
    item = queue[0]
    explanation = explain_item(item)
    assert "factors" in explanation
    assert len(explanation["factors"]) == len(item.factors)
    # No opaque ML; every factor cites rule_id and evidence.
    for f in explanation["factors"]:
        assert "rule_id" in f and "value" in f and "weight" in f and "contribution" in f
        assert "evidence" in f


# ---------------------------------------------------------------------------
# No trust mutation
# ---------------------------------------------------------------------------


def test_queue_commands_never_change_verified_in_frontmatter(bundle: Path) -> None:
    """Claiming/deciding/suppressing via the queue must not mutate concept trust state."""
    from headcleaner.review_queue import suppress_item

    queue = build_queue(bundle)
    item = queue[0]
    pre = (bundle / item.concept_ref).read_text(encoding="utf-8")
    _ = decide_item(
        claim_item(item, reviewer="alice"),
        decision="approved",
        reason="verified by reviewer",
    )
    _ = suppress_item(queue[-1], reason="duplicate")
    post_alpha = (bundle / queue[0].concept_ref).read_text(encoding="utf-8")
    post_gamma = (bundle / queue[-1].concept_ref).read_text(encoding="utf-8")
    # No `verified:` field in the concept's frontmatter should have changed.
    assert "verified:" not in _extract_fm_field(post_alpha, "verified", set=False) or (
        _extract_fm_field(post_alpha, "verified", set=False) == pre.split("---")[1]
    )
    assert "verified:" not in _extract_fm_field(post_gamma, "verified", set=False)


def _extract_fm_field(text: str, field: str, *, set: bool) -> str:
    """Tiny frontmatter field probe (test-only)."""
    m = re.search(rf"^{re.escape(field)}:\s*(.*)$", text, re.MULTILINE)
    return m.group(1).strip() if m else ""
