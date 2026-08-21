"""Read-only, evidence-first projections for human review.

A review packet never changes a concept. It is an offline projection of the
existing frontmatter state and source citations; decisions stay in
:mod:`headcleaner.review`, which remains the sole state authority.
"""

from __future__ import annotations

import html
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .review import _read_concept


@dataclass(frozen=True)
class ReviewPacket:
    """Immutable evidence projection for one concept."""

    concept_ref: str
    review_state: str
    diagnostics: tuple[dict[str, Any], ...]
    policy_findings: tuple[dict[str, Any], ...]
    diff_refs: tuple[str, ...]
    citations: tuple[dict[str, Any], ...]


def _concept_path(bundle_root: Path, concept_ref: str) -> Path:
    candidate = (bundle_root / concept_ref).resolve()
    try:
        candidate.relative_to(bundle_root.resolve())
    except ValueError as exc:
        raise ValueError("concept_ref must stay within bundle_root") from exc
    return candidate


def build_packet(bundle_root: Path, concept_ref: str) -> ReviewPacket:
    """Build a read-only, JSON-serializable evidence projection."""
    concept = _concept_path(Path(bundle_root), concept_ref)
    record = _read_concept(concept)
    if record is None:
        raise ValueError(f"not a valid concept: {concept_ref}")
    frontmatter, _, _ = record
    sources = frontmatter.get("sources") or []
    citations = tuple(item for item in sources if isinstance(item, dict))
    diagnostics = tuple(
        item for item in (frontmatter.get("diagnostics") or []) if isinstance(item, dict)
    )
    policy_findings = tuple(
        item for item in (frontmatter.get("policy_findings") or []) if isinstance(item, dict)
    )
    diff_refs = tuple(str(item) for item in (frontmatter.get("diff_refs") or []))
    return ReviewPacket(
        concept_ref=concept_ref.replace("\\", "/"),
        review_state=str(frontmatter.get("verified", "human:pending")),
        diagnostics=diagnostics,
        policy_findings=policy_findings,
        diff_refs=diff_refs,
        citations=citations,
    )


def render_packet(packet: ReviewPacket, *, format: str = "json") -> str:
    """Render an offline packet as deterministic JSON or self-contained HTML."""
    payload = asdict(packet)
    if format == "json":
        return json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True)
    if format != "html":
        raise ValueError("format must be 'json' or 'html'")
    encoded = html.escape(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))
    return (
        "<!doctype html><meta charset=\"utf-8\"><title>HeadCleaner review packet</title>"
        "<main><h1>Review packet</h1><pre>" + encoded + "</pre></main>"
    )
