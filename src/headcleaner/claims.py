"""Bounded deterministic stale and potential-conflict candidate detection."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date
from typing import Any

MAX_CLAIMS_PER_DOCUMENT = 5000


@dataclass(frozen=True)
class ClaimCandidate:
    id: str
    kind: str
    normalized_value: str
    source_chunk_id: str
    citation: dict[str, Any]
    extraction_rule: str
    status: str = "unverified"
    suppression_reason: str | None = None


@dataclass(frozen=True)
class Finding:
    id: str
    type: str
    severity: str
    claim_ids: tuple[str, ...]
    evidence: tuple[dict[str, Any], ...]
    rule_id: str


def _claim(
    kind: str, value: str, chunk: dict[str, Any], suppression_reason: str | None = None
) -> ClaimCandidate:
    normalized = " ".join(value.casefold().split())
    identifier = hashlib.sha256(f"{kind}\0{normalized}\0{chunk['id']}".encode()).hexdigest()
    return ClaimCandidate(
        identifier,
        kind,
        normalized,
        str(chunk["id"]),
        dict(chunk["citation"]),
        f"claims/{kind}",
        "suppressed" if suppression_reason else "unverified",
        suppression_reason,
    )


def analyze_claims(
    chunks: Iterable[dict[str, Any]],
    *,
    stale_after: str | None = None,
    today: str | None = None,
    cap: int = MAX_CLAIMS_PER_DOCUMENT,
    suppressions: Mapping[str, str] | None = None,
    scope: str = "bundle",
    stale_after_by_source: Mapping[str, str] | None = None,
) -> tuple[list[ClaimCandidate], list[Finding]]:
    if scope not in {"bundle", "source"}:
        raise ValueError("claims scope must be bundle or source")
    suppressions = suppressions or {}
    claims: list[ClaimCandidate] = []
    citations_by_source: dict[str, dict[str, Any]] = {}
    for chunk in chunks:
        citation = dict(chunk["citation"])
        source_sha256 = str(citation.get("source_sha256", "missing-source"))
        citations_by_source.setdefault(source_sha256, citation)
        text = str(chunk.get("text", ""))
        for kind, pattern in (
            ("owner", r"(?im)^owner:\s*(.+)$"),
            ("amount", r"\$([0-9][0-9,]*(?:\.\d{2})?)\b"),
            ("status_label", r"(?im)^status:\s*(.+)$"),
            ("date", r"\b\d{4}-\d{2}-\d{2}\b"),
        ):
            for match in re.finditer(pattern, text):
                if len(claims) >= cap:
                    finding = Finding(
                        hashlib.sha256(b"CLAIMS_TOO_MANY").hexdigest(),
                        "claims_too_many",
                        "warning",
                        (),
                        (),
                        "CLAIMS_TOO_MANY",
                    )
                    return claims, [finding]
                claims.append(
                    _claim(
                        kind,
                        match.group(1) if match.groups() else match.group(0),
                        chunk,
                        suppressions.get(kind),
                    )
                )
    findings: list[Finding] = []
    by_kind_and_scope: dict[tuple[str, str], list[ClaimCandidate]] = {}
    for claim in claims:
        if claim.status == "suppressed":
            continue
        scope_key = (
            "bundle"
            if scope == "bundle"
            else str(claim.citation.get("source_sha256", "missing-source"))
        )
        by_kind_and_scope.setdefault((claim.kind, scope_key), []).append(claim)
    for (kind, _scope_key), values in by_kind_and_scope.items():
        for index, left in enumerate(values):
            for right in values[index + 1 :]:
                if left.normalized_value != right.normalized_value:
                    findings.append(
                        Finding(
                            hashlib.sha256((left.id + right.id).encode()).hexdigest(),
                            "potential_conflict",
                            "warning",
                            (left.id, right.id),
                            (left.citation, right.citation),
                            f"claims/{kind}/unequal/{scope}",
                        )
                    )
    stale_by_source = stale_after_by_source or {}
    for source_sha256, source_stale_after in sorted(stale_by_source.items()):
        if date.fromisoformat(source_stale_after) >= date.fromisoformat(
            today or date.today().isoformat()
        ):
            continue
        findings.append(
            Finding(
                hashlib.sha256(
                    ("stale\0" + source_sha256 + source_stale_after).encode()
                ).hexdigest(),
                "stale",
                "warning",
                (),
                (citations_by_source.get(source_sha256, {"source_sha256": source_sha256}),),
                "lifecycle/stale_after",
            )
        )
    if stale_after and date.fromisoformat(stale_after) < date.fromisoformat(
        today or date.today().isoformat()
    ):
        findings.append(
            Finding(
                hashlib.sha256(("stale\0" + stale_after).encode()).hexdigest(),
                "stale",
                "warning",
                (),
                (),
                "lifecycle/stale_after",
            )
        )
    return claims, findings
