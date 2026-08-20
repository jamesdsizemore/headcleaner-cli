"""Deterministic quality-corpus benchmark runner."""

from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path
from typing import Any

from . import __version__
from .run import RunOptions, run_pipeline

SCHEMA_VERSION = "1.0"
_EXPECTATIONS = "expectations.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _recall(expected: list[str], rendered: str) -> float:
    if not expected:
        return 1.0
    return sum(anchor in rendered for anchor in expected) / len(expected)


def _headings(rendered: str) -> list[str]:
    return [line.lstrip("#").strip() for line in rendered.splitlines() if line.startswith("#")]


def _load_expectations(fixtures: Path) -> dict[str, dict[str, Any]]:
    path = fixtures / _EXPECTATIONS
    if not path.exists():
        raise ValueError(f"missing fixture metadata: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("fixture metadata must be an object keyed by relative path")
    return data


def run_benchmark(
    fixtures: Path, *, baseline: Path | None = None, update_baseline: bool = False
) -> dict[str, Any]:
    """Convert fixture corpus and return deterministic component metrics."""
    fixtures = fixtures.resolve()
    expectations = _load_expectations(fixtures)
    output = Path(tempfile.mkdtemp(prefix="headcleaner-benchmark-"))
    record = run_pipeline(
        RunOptions(input_root=fixtures, output_root=output, fmt="md", use_cache=False)
    )
    rows: list[dict[str, Any]] = []
    for result in sorted(record.results, key=lambda item: item.relpath):
        if result.relpath not in expectations:
            continue
        expected = expectations[result.relpath]
        source = fixtures / result.relpath
        rendered_path = output / "_md" / f"{result.relpath}.md"
        rendered = rendered_path.read_text(encoding="utf-8") if rendered_path.exists() else ""
        expected_headings = expected.get("headings", [])
        headings_ok = _headings(rendered)[: len(expected_headings)] == expected_headings
        metrics = {
            "text_anchor_recall": _recall(expected.get("text_anchors", []), rendered),
            "heading_order": 1.0 if headings_ok else 0.0,
            "table_anchor_recall": _recall(expected.get("table_anchors", []), rendered),
            "output_exists": 1.0 if rendered_path.exists() else 0.0,
        }
        rows.append(
            {
                "fixture_id": result.relpath,
                "source_sha256": _sha256(source),
                "status": "ok" if all(value == 1.0 for value in metrics.values()) else "regressed",
                "metrics": metrics,
                "warnings": [],
            }
        )
    if len(rows) != len(expectations):
        raise ValueError("fixture metadata references an unknown or unsupported fixture")
    report = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": record.finished_at,
        "tool_version": __version__,
        "fixtures": rows,
        "summary": {
            "fixture_count": len(rows),
            "passed": sum(row["status"] == "ok" for row in rows),
            "failed": sum(row["status"] != "ok" for row in rows),
        },
    }
    baseline_report = {key: value for key, value in report.items() if key != "generated_at"}
    if update_baseline:
        if baseline is None:
            raise ValueError("--update-baseline requires --baseline PATH")
        baseline.parent.mkdir(parents=True, exist_ok=True)
        baseline.write_text(
            json.dumps(baseline_report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    elif baseline is not None and baseline.exists():
        if json.loads(baseline.read_text(encoding="utf-8")) != baseline_report:
            raise ValueError("metric regression against baseline")
    failed_metrics = sorted(
        {name for row in rows for name, value in row["metrics"].items() if value < 1.0}
    )
    if failed_metrics:
        raise ValueError(f"metric regression: {', '.join(failed_metrics)}")
    return report
