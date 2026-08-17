"""Tests for the conversion report emitter."""
from __future__ import annotations

import datetime as _dt
from pathlib import Path

from headcleaner.emit.report import build_report, write_report

NOW = _dt.datetime(2026, 8, 16, 12, 0, 0)
LATER = _dt.datetime(2026, 8, 16, 12, 5, 30)


SAMPLE_RECORDS = [
    {
        "relpath": "notes.docx",
        "engine": "officecli",
        "status": "ok",
        "sha256": "abc",
        "duration_seconds": 0.2,
    },
    {
        "relpath": "data.csv",
        "engine": "csv",
        "status": "ok",
        "sha256": "def",
        "duration_seconds": 0.4,
    },
    {
        "relpath": "broken.pdf",
        "engine": "pdf",
        "status": "failed",
        "error": "EOF marker missing",
        "duration_seconds": 0.6,
    },
    {
        "relpath": "skip.txt",
        "engine": "txt",
        "status": "skipped",
        "reason": "no extension match",
    },
]


def test_build_report_includes_summary():
    text = build_report(
        SAMPLE_RECORDS,
        started_at=NOW,
        finished_at=LATER,
        bundle_root="./inbox",
    )
    assert "headcleaner conversion report" in text
    assert "Files processed" in text
    assert "**2**" in text  # 2 OK
    assert "Failed" in text
    assert "./inbox" in text


def test_build_report_per_engine_breakdown():
    text = build_report(
        SAMPLE_RECORDS,
        started_at=NOW,
        finished_at=LATER,
        bundle_root="./inbox",
    )
    assert "Per-engine breakdown" in text
    assert "officecli" in text
    assert "pdf" in text
    assert "csv" in text
    assert "Error rate" in text
    assert "Avg time" in text
    assert "0.200s" in text
    assert "100.0%" in text  # pdf has one failed record


def test_build_report_lists_errors():
    text = build_report(
        SAMPLE_RECORDS,
        started_at=NOW,
        finished_at=LATER,
        bundle_root="./inbox",
    )
    assert "Top errors" in text
    assert "broken.pdf" in text
    assert "EOF marker missing" in text


def test_build_report_handles_no_errors():
    records = [
        {"relpath": "a.md", "engine": "md", "status": "ok"},
        {"relpath": "b.md", "engine": "md", "status": "ok"},
    ]
    text = build_report(
        records,
        started_at=NOW,
        finished_at=LATER,
        bundle_root="./inbox",
    )
    assert "Top errors" not in text
    assert "Success rate" in text
    assert "100.0%" in text


def test_build_report_handles_empty():
    text = build_report(
        [],
        started_at=NOW,
        finished_at=LATER,
        bundle_root="./inbox",
    )
    assert "Total** | 0" in text


def test_build_report_labels_missing_engine_as_unknown():
    text = build_report(
        [{"relpath": "unsupported.bin", "engine": None, "status": "skipped"}],
        started_at=NOW,
        finished_at=LATER,
        bundle_root="./inbox",
    )

    assert "| `unknown` | 1 |" in text


def test_write_report_creates_file(tmp_path: Path):
    out = tmp_path / "REPORT.md"
    path = write_report(
        out,
        SAMPLE_RECORDS,
        started_at=NOW,
        finished_at=LATER,
        bundle_root="./inbox",
    )
    assert path == out
    assert path.exists()
    assert "headcleaner conversion report" in path.read_text(encoding="utf-8")


def test_wall_clock_renders():
    text = build_report(
        SAMPLE_RECORDS,
        started_at=NOW,
        finished_at=LATER,
        bundle_root="./inbox",
    )
    # 5 minutes 30 seconds = 330s
    assert "330.0s" in text


def test_error_pipe_escaped():
    records = [
        {"relpath": "x", "engine": "y", "status": "failed", "error": "msg|with|pipes"},
    ]
    text = build_report(
        records,
        started_at=NOW,
        finished_at=LATER,
        bundle_root=".",
    )
    # Pips should be escaped so they don't break the table
    assert "msg\\|with\\|pipes" in text
