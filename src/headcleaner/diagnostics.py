"""Stable extraction diagnostics and measurable confidence inputs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TypeAlias

JSONScalar: TypeAlias = str | int | float | bool | None  # noqa: UP040 -- host syntax check is Python 3.11.
_SEVERITIES = frozenset({"info", "warning", "error"})


@dataclass(frozen=True)
class Diagnostic:
    """A stable, machine-readable extraction observation."""

    code: str
    severity: str
    message: str
    evidence: dict[str, JSONScalar]

    def __post_init__(self) -> None:
        if self.severity not in _SEVERITIES:
            raise ValueError(f"severity must be one of {sorted(_SEVERITIES)}")
        if not self.code or self.code != self.code.upper():
            raise ValueError("diagnostic code must be non-empty uppercase")


@dataclass(frozen=True)
class ExtractionMetrics:
    """Non-semantic, measurable inputs recorded for each extraction."""

    page_count: int | None = None
    character_count: int = 0
    element_counts: dict[str, int] = field(default_factory=dict)
    engine_attempts: list[str] = field(default_factory=list)
    ocr_used: bool = False
    detected_languages: list[str] = field(default_factory=list)
    confidence_inputs: dict[str, JSONScalar] = field(default_factory=dict)


def compute_confidence(metrics: ExtractionMetrics) -> tuple[float, dict[str, float]]:
    """Return bounded, explicitly-measurable confidence and its contributions."""
    contributions = {
        "non_empty_extraction": 0.4 if metrics.character_count > 0 else 0.0,
        "engine_success": 0.3 if metrics.engine_attempts else 0.0,
        "required_anchors": 0.2 if metrics.confidence_inputs.get("required_anchors_ok") else 0.0,
        "structural_content": 0.1 if any(metrics.element_counts.values()) else 0.0,
    }
    if metrics.confidence_inputs.get("ocr_warning"):
        contributions["engine_success"] = max(0.0, contributions["engine_success"] - 0.1)
    return min(1.0, max(0.0, sum(contributions.values()))), contributions
