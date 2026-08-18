from __future__ import annotations

import json

import pytest

from headcleaner.diagnostics import Diagnostic, ExtractionMetrics, compute_confidence
from headcleaner.emit.manifest import FileResult, RunRecord


def test_diagnostic_is_frozen_and_uses_stable_severity() -> None:
    diagnostic = Diagnostic(
        "OCR_UNAVAILABLE", "warning", "OCR is unavailable", {"tool": "tesseract"}
    )

    assert diagnostic.code == "OCR_UNAVAILABLE"
    with pytest.raises((AttributeError, TypeError)):
        diagnostic.severity = "error"  # type: ignore[misc]
    with pytest.raises(ValueError, match="severity"):
        Diagnostic("OCR_UNAVAILABLE", "fatal", "nope", {})


def test_confidence_is_bounded_and_exposes_named_contributions() -> None:
    metrics = ExtractionMetrics(
        character_count=12,
        element_counts={"paragraph": 1},
        engine_attempts=["txt"],
        confidence_inputs={"required_anchors_ok": True, "ocr_warning": False},
    )

    confidence, contributions = compute_confidence(metrics)

    assert confidence == 1.0
    assert contributions == {
        "engine_success": 0.3,
        "non_empty_extraction": 0.4,
        "required_anchors": 0.2,
        "structural_content": 0.1,
    }


def test_manifest_serializes_diagnostics_metrics_and_confidence_stably() -> None:
    result = FileResult(
        source_path="source.txt",
        relpath="source.txt",
        engine="txt",
        sha256="abc",
        md_path="out/source.txt.md",
        okf_path=None,
        status="ok",
        diagnostics=[
            Diagnostic("OCR_UNAVAILABLE", "warning", "OCR is unavailable", {"b": 2, "a": 1})
        ],
        metrics=ExtractionMetrics(character_count=4, engine_attempts=["txt"]),
        confidence=0.7,
    )
    record = RunRecord(results=[result])

    data = json.loads(record.to_json())

    assert data["results"][0]["diagnostics"][0]["code"] == "OCR_UNAVAILABLE"
    assert data["results"][0]["metrics"]["character_count"] == 4
    assert data["results"][0]["confidence"] == 0.7
