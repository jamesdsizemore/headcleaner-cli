"""Explainable risk-based review queue (Contract 3.6).

Queue items are derived from OKF concept frontmatter + bundle metadata.
Priority is a sum of weighted factor contributions; only registered factor
functions may contribute, and missing evidence contributes zero plus a
diagnostic — never assumed risk. Queue commands are read/write to the queue
audit log only; they never mutate concept trust state.
"""

from __future__ import annotations

import enum
import hashlib
import re
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Iterable

import yaml

from .normalize import default_stale_after


# ---------------------------------------------------------------------------
# Public surface
# ---------------------------------------------------------------------------


class QueueState(str, enum.Enum):
    PENDING = "pending"
    CLAIMED = "claimed"
    DECIDED = "decided"
    SUPPRESSED = "suppressed"


@dataclass(frozen=True)
class FactorSpec:
    """A registered factor function and its default weight."""

    rule_id: str
    value_fn: Callable[[dict[str, Any]], tuple[float, dict[str, Any]]]
    weight: float = 1.0


@dataclass(frozen=True)
class QueueItem:
    concept_ref: str
    priority: float
    factors: list[dict[str, Any]] = field(default_factory=list)
    state: str = QueueState.PENDING.value
    created_at: str = ""
    source_sha256: str = ""
    claimed_by: str | None = None
    claim_count: int = 0
    decision: str | None = None
    decision_reason: str | None = None
    suppression_reason: str | None = None
    decided_by: str | None = None
    score_version: str = "1"


# ---------------------------------------------------------------------------
# Concept frontmatter parsing (small, deterministic, no external state)
# ---------------------------------------------------------------------------


_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def _parse_frontmatter(text: str) -> dict[str, Any]:
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {}
    try:
        return yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        return {}


def _bundle_source_sha(bundle_root: Path, concept_ref: str) -> str:
    """Compute the source_sha256 for a concept from its OKF sources[] entry.

    Falls back to a SHA of the concept body if no sources entry is available.
    """
    md_path = bundle_root / concept_ref
    text = md_path.read_text(encoding="utf-8")
    fm = _parse_frontmatter(text)
    sources = fm.get("sources") or []
    if isinstance(sources, list):
        for src in sources:
            if isinstance(src, dict) and isinstance(src.get("sha256"), str):
                if len(src["sha256"]) == 64:
                    return src["sha256"]
    # Fall back to a deterministic hash of the body.
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Factor registry
# ---------------------------------------------------------------------------


_FACTOR_ALLOW_LIST = frozenset(
    {
        "diagnostic_severity",
        "ocr_fallback_state",
        "sensitivity_findings",
        "policy_errors",
        "stale_state",
        "age",
    }
)


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _is_stale(fm: dict[str, Any]) -> tuple[float, dict[str, Any]]:
    """stale_state factor: returns (1.0, evidence) when stale_after is in the past."""
    raw = fm.get("stale_after")
    if not raw or not isinstance(raw, str):
        return 0.0, {"missing": True, "field": "stale_after", "ts": _now()}
    try:
        ts = datetime.strptime(raw, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    except ValueError:
        return 0.0, {"missing": True, "field": "stale_after", "ts": _now()}
    now = datetime.now(UTC)
    if ts < now:
        days = (now - ts).days
        return 1.0, {"field": "stale_after", "days_overdue": days, "ts": _now()}
    return 0.0, {"field": "stale_after", "days_overdue": 0, "ts": _now()}


def _is_pending_review(fm: dict[str, Any]) -> tuple[float, dict[str, Any]]:
    """diagnostic_severity factor: returns 1.0 when verified=human:pending."""
    v = fm.get("verified")
    if not isinstance(v, str):
        return 0.0, {"missing": True, "field": "verified", "ts": _now()}
    if v == "human:pending":
        return 1.0, {"field": "verified", "value": v, "ts": _now()}
    return 0.0, {"field": "verified", "value": v, "ts": _now()}


def _ocr_fallback(fm: dict[str, Any]) -> tuple[float, dict[str, Any]]:
    """ocr_fallback_state factor: returns 1.0 when ocr_used=True in metadata."""
    meta = fm.get("metrics") or {}
    if not isinstance(meta, dict):
        return 0.0, {"missing": True, "field": "metrics.ocr_used", "ts": _now()}
    used = meta.get("ocr_used")
    if used is True:
        return 1.0, {"field": "metrics.ocr_used", "value": True, "ts": _now()}
    return 0.0, {"field": "metrics.ocr_used", "value": bool(used), "ts": _now()}


def _sensitivity(fm: dict[str, Any]) -> tuple[float, dict[str, Any]]:
    """sensitivity_findings factor: returns 1.0 when redaction findings present."""
    findings = fm.get("redaction_findings")
    if isinstance(findings, list) and findings:
        return float(len(findings)), {
            "field": "redaction_findings",
            "count": len(findings),
            "ts": _now(),
        }
    return 0.0, {"missing": True, "field": "redaction_findings", "ts": _now()}


def _policy_errors(fm: dict[str, Any]) -> tuple[float, dict[str, Any]]:
    """policy_errors factor: returns 1.0 when at least one policy error finding present."""
    findings = fm.get("policy_findings") or []
    if not isinstance(findings, list):
        return 0.0, {"missing": True, "field": "policy_findings", "ts": _now()}
    errors = [f for f in findings if isinstance(f, dict) and f.get("severity") == "error"]
    if errors:
        return 1.0, {
            "field": "policy_findings",
            "error_count": len(errors),
            "ts": _now(),
        }
    return 0.0, {"field": "policy_findings", "error_count": 0, "ts": _now()}


def _age_days(fm: dict[str, Any]) -> tuple[float, dict[str, Any]]:
    """age factor: returns days since generated timestamp, normalised to [0, 1] over 365 days."""
    raw = fm.get("generated")
    if not isinstance(raw, str):
        return 0.0, {"missing": True, "field": "generated", "ts": _now()}
    try:
        ts = datetime.strptime(raw, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    except ValueError:
        return 0.0, {"missing": True, "field": "generated", "ts": _now()}
    days = (datetime.now(UTC) - ts).days
    if days <= 0:
        return 0.0, {"field": "generated", "days": days, "ts": _now()}
    normalised = min(1.0, days / 365.0)
    return normalised, {"field": "generated", "days": days, "ts": _now()}


FACTOR_REGISTRY: dict[str, FactorSpec] = {
    "diagnostic_severity": FactorSpec("diagnostic_severity", _is_pending_review, weight=1.0),
    "ocr_fallback_state": FactorSpec("ocr_fallback_state", _ocr_fallback, weight=1.0),
    "sensitivity_findings": FactorSpec("sensitivity_findings", _sensitivity, weight=1.0),
    "policy_errors": FactorSpec("policy_errors", _policy_errors, weight=1.0),
    "stale_state": FactorSpec("stale_state", _is_stale, weight=1.0),
    "age": FactorSpec("age", _age_days, weight=0.5),
}


def register_factor(
    *,
    rule_id: str,
    value_fn: Callable[[dict[str, Any]], tuple[float, dict[str, Any]]],
    weight: float = 1.0,
) -> FactorSpec:
    if rule_id not in _FACTOR_ALLOW_LIST:
        raise ValueError(f"rule_id must be one of {sorted(_FACTOR_ALLOW_LIST)}")
    spec = FactorSpec(rule_id=rule_id, value_fn=value_fn, weight=weight)
    FACTOR_REGISTRY[rule_id] = spec
    return spec


# ---------------------------------------------------------------------------
# Queue construction
# ---------------------------------------------------------------------------


def _concepts_in_bundle(bundle_root: Path) -> list[str]:
    if not bundle_root.is_dir():
        return []
    return sorted(
        str(p.relative_to(bundle_root)).replace("\\", "/")
        for p in bundle_root.rglob("*.md")
        if p.name not in {"index.md", "log.md"}
    )


def _priority_for_item(
    concept_ref: str,
    factors: list[dict[str, Any]],
) -> float:
    return round(sum(float(f["contribution"]) for f in factors), 9)


def build_queue(
    bundle_root: Path,
    *,
    pack_weights: dict[str, float] | None = None,
) -> list[QueueItem]:
    """Build the deterministic queue for a bundle.

    `pack_weights` is an optional mapping from rule_id → weight that overrides
    the default `FACTOR_REGISTRY` weights for this build. The mapping keys
    must still come from the approved allow list.
    """
    pack_weights = pack_weights or {}
    for rule_id in pack_weights:
        if rule_id not in _FACTOR_ALLOW_LIST:
            raise ValueError(f"pack weight for unknown rule_id: {rule_id}")

    queue: list[QueueItem] = []
    for concept_ref in _concepts_in_bundle(bundle_root):
        text = (bundle_root / concept_ref).read_text(encoding="utf-8")
        fm = _parse_frontmatter(text)
        factors: list[dict[str, Any]] = []
        for rule_id, spec in FACTOR_REGISTRY.items():
            weight = float(pack_weights.get(rule_id, spec.weight))
            value, evidence = spec.value_fn(fm)
            contribution = round(value * weight, 9)
            factors.append(
                {
                    "rule_id": rule_id,
                    "value": value,
                    "weight": weight,
                    "contribution": contribution,
                    "evidence": evidence,
                }
            )
        # Refresh stale_after default if missing so the frontmatter is well-formed.
        if "stale_after" not in fm:
            fm["stale_after"] = default_stale_after()
        priority = _priority_for_item(concept_ref, factors)
        queue.append(
            QueueItem(
                concept_ref=concept_ref,
                priority=priority,
                factors=factors,
                state=QueueState.PENDING.value,
                created_at=_now(),
                source_sha256=_bundle_source_sha(bundle_root, concept_ref),
            )
        )
    # Sort by (-priority, source_sha256, concept_ref) — deterministic.
    queue.sort(key=lambda i: (-i.priority, i.source_sha256, i.concept_ref))
    return queue


# ---------------------------------------------------------------------------
# State transitions
# ---------------------------------------------------------------------------


def claim_item(item: QueueItem, *, reviewer: str) -> QueueItem:
    if not reviewer:
        raise ValueError("reviewer is required")
    if item.state == QueueState.CLAIMED.value:
        if item.claimed_by == reviewer:
            return item  # idempotent for the same reviewer
        raise PermissionError(
            f"item already claimed by {item.claimed_by}; duplicate claim rejected"
        )
    if item.state in {QueueState.DECIDED.value, QueueState.SUPPRESSED.value}:
        raise ValueError(f"item is {item.state} and cannot be claimed")
    return replace(
        item,
        state=QueueState.CLAIMED.value,
        claimed_by=reviewer,
        claim_count=item.claim_count + 1,
    )


def decide_item(item: QueueItem, *, decision: str, reason: str) -> QueueItem:
    if item.state != QueueState.CLAIMED.value:
        raise ValueError("only CLAIMED items can be decided")
    if decision not in {"approved", "rejected", "needs_changes"}:
        raise ValueError("decision must be approved|rejected|needs_changes")
    if not reason:
        raise ValueError("decision reason is required")
    return replace(
        item,
        state=QueueState.DECIDED.value,
        decision=decision,
        decision_reason=reason,
        decided_by=item.claimed_by,
    )


def suppress_item(item: QueueItem, *, reason: str) -> QueueItem:
    if not reason:
        raise ValueError("suppression reason is required")
    return replace(
        item,
        state=QueueState.SUPPRESSED.value,
        suppression_reason=reason,
    )


# ---------------------------------------------------------------------------
# Explainability
# ---------------------------------------------------------------------------


def explain_item(item: QueueItem) -> dict[str, Any]:
    """Return a structured explanation of one queue item."""
    return {
        "concept_ref": item.concept_ref,
        "source_sha256": item.source_sha256,
        "priority": item.priority,
        "state": item.state,
        "score_version": item.score_version,
        "factors": [
            {
                "rule_id": f["rule_id"],
                "value": f["value"],
                "weight": f["weight"],
                "contribution": f["contribution"],
                "evidence": f["evidence"],
            }
            for f in item.factors
        ],
    }
