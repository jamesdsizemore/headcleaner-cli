from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from headcleaner.diagnostics import Diagnostic, ExtractionMetrics, compute_confidence
from headcleaner.emit.manifest import FileResult, RunRecord
from headcleaner.emit.report import build_report
from headcleaner.run import RunOptions, run_pipeline


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


def test_report_includes_shared_confidence_and_diagnostic_summary() -> None:
    text = build_report(
        [
            {
                "relpath": "source.txt",
                "engine": "txt",
                "status": "ok",
                "confidence": 0.7,
                "diagnostics": [{"code": "OCR_UNAVAILABLE", "severity": "warning"}],
            }
        ],
        started_at=datetime(2026, 1, 1, tzinfo=UTC),
        finished_at=datetime(2026, 1, 1, tzinfo=UTC),
        bundle_root="fixtures",
    )

    assert "## Extraction diagnostics" in text
    assert "Average confidence" in text
    assert "OCR_UNAVAILABLE" in text


def test_json_pipeline_event_uses_file_result_diagnostics(tmp_path: Path, capsys) -> None:
    source = tmp_path / "note.txt"
    source.write_text("diagnostic fixture", encoding="utf-8")

    run_pipeline(
        RunOptions(input_root=tmp_path, output_root=tmp_path / "out", fmt="md", json_output=True)
    )

    events = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    file_event = next(event for event in events if event["event"] == "file")
    assert file_event["metrics"]["character_count"] > 0
    assert 0.0 <= file_event["confidence"] <= 1.0
