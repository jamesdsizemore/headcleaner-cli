"""Opt-in, deterministic redaction proposals and immutable bundle derivatives."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path

_SECRET = re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")


@dataclass(frozen=True)
class RedactionFinding:
    id: str
    category: str
    detector: str
    confidence: float
    citation: str
    replacement: str
    status: str
    value_sha256: str
    start: int
    end: int
    concept_ref: str
    suppression_reason: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "category": self.category,
            "detector": self.detector,
            "confidence": self.confidence,
            "citation": self.citation,
            "replacement": self.replacement,
            "status": self.status,
            "value_sha256": self.value_sha256,
            "concept_ref": self.concept_ref,
            "suppression_reason": self.suppression_reason,
        }

    def to_dict_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True)


def propose_redactions(
    bundle_root: Path, *, suppress_categories: dict[str, str] | None = None
) -> list[RedactionFinding]:
    """Find deterministic secret candidates without writing or retaining values."""
    root = Path(bundle_root)
    suppress_categories = suppress_categories or {}
    findings: list[RedactionFinding] = []
    for path in sorted(root.rglob("*.md")):
        if "_redacted" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        concept_ref = path.relative_to(root).as_posix()
        for ordinal, match in enumerate(_SECRET.finditer(text), start=1):
            value = match.group(0)
            findings.append(
                RedactionFinding(
                    id=f"redaction/{concept_ref}/{ordinal}",
                    category="secret",
                    detector="regex/openai-key/v1",
                    confidence=1.0,
                    citation=f"{concept_ref}:offset:{match.start()}",
                    replacement="[REDACTED:secret]",
                    status="suppressed" if "secret" in suppress_categories else "proposed",
                    value_sha256=hashlib.sha256(value.encode("utf-8")).hexdigest(),
                    start=match.start(),
                    end=match.end(),
                    concept_ref=concept_ref,
                    suppression_reason=suppress_categories.get("secret"),
                )
            )
    return findings


def write_derivative(bundle_root: Path, findings: list[RedactionFinding]) -> Path:
    """Write a separate redacted copy; canonical bundle content is never changed."""
    root = Path(bundle_root)
    output = root / "_redacted"
    by_ref: dict[str, list[RedactionFinding]] = {}
    for finding in findings:
        by_ref.setdefault(finding.concept_ref, []).append(finding)
    for source in sorted(root.rglob("*.md")):
        if "_redacted" in source.parts:
            continue
        rel = source.relative_to(root)
        target = output / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        text = source.read_text(encoding="utf-8")
        for finding in sorted(by_ref.get(rel.as_posix(), []), key=lambda item: item.start, reverse=True):
            if finding.status == "suppressed":
                continue
            text = text[: finding.start] + finding.replacement + text[finding.end :]
        if text.startswith("---\n"):
            text = text.replace("---\n", f"---\ncanonical_concept: {rel.as_posix()}\n", 1)
        target.write_text(text, encoding="utf-8")
    report = output / "redaction-report.json"
    report.write_text(json.dumps([item.to_dict() for item in findings], indent=2, sort_keys=True), encoding="utf-8")
    return output
