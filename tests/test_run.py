"""End-to-end test of the run_pipeline orchestrator."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from headcleaner import router
from headcleaner.engines.base import Adapter, AdapterError
from headcleaner.run import RunOptions, run_pipeline


def test_run_pipeline_emits_md_and_okf(mixed_dir: Path, tmp_path: Path) -> None:
    out = tmp_path / "out"
    record = run_pipeline(RunOptions(input_root=mixed_dir, output_root=out, fmt="both"))

    results_by_status = {r.status for r in record.results}
    assert "failed" not in results_by_status

    # MD output
    md_files = list((out / "_md").rglob("*.md"))
    assert len(md_files) >= 4

    # OKF output
    okf_files = list((out / "okf").rglob("*.md"))
    assert len(okf_files) >= 4

    # Manifest
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["tool"] == "headcleaner"
    assert manifest["format"] == "both"
    assert all(r["status"] == "ok" for r in manifest["results"])
    assert all(r["duration_seconds"] >= 0 for r in manifest["results"])

    # Conversion report: emitted automatically after every non-dry conversion.
    report = (out / "REPORT.md").read_text(encoding="utf-8")
    assert "headcleaner conversion report" in report
    assert "Per-engine breakdown" in report
    assert "Avg time" in report
    assert "Error rate" in report


def test_run_pipeline_md_only(mixed_dir: Path, tmp_path: Path) -> None:
    out = tmp_path / "out"
    record = run_pipeline(RunOptions(input_root=mixed_dir, output_root=out, fmt="md"))
    assert all(r.md_path for r in record.results)
    assert all(r.okf_path is None for r in record.results)


def test_run_pipeline_okf_only(mixed_dir: Path, tmp_path: Path) -> None:
    out = tmp_path / "out"
    record = run_pipeline(RunOptions(input_root=mixed_dir, output_root=out, fmt="okf"))
    assert all(r.okf_path for r in record.results)
    assert all(r.md_path is None for r in record.results)


def test_run_pipeline_writes_conversion_report(mixed_dir: Path, tmp_path: Path) -> None:
    out = tmp_path / "out"

    record = run_pipeline(RunOptions(input_root=mixed_dir, output_root=out, fmt="md"))

    report = (out / "REPORT.md").read_text(encoding="utf-8")
    assert "# headcleaner conversion report" in report
    assert f"| **Total** | {len(record.results)} |" in report
    assert "## Per-engine breakdown" in report


def test_run_pipeline_dry_run_does_not_write_report(mixed_dir: Path, tmp_path: Path) -> None:
    out = tmp_path / "out"

    run_pipeline(
        RunOptions(input_root=mixed_dir, output_root=out, fmt="md", dry_run=True),
    )

    assert not (out / "REPORT.md").exists()


@pytest.mark.parametrize("jobs", [1, 2])
def test_run_pipeline_does_not_silently_fallback_from_requested_engine(
    tmp_path: Path, jobs: int
) -> None:
    (tmp_path / "note.txt").write_text("engine policy", encoding="utf-8")

    record = run_pipeline(
        RunOptions(
            input_root=tmp_path,
            output_root=tmp_path / "out",
            fmt="md",
            requested_engine="html",
            jobs=jobs,
        )
    )

    assert len(record.results) == 1
    assert record.results[0].status == "skipped"
    assert record.results[0].engine is None
    assert record.results[0].error == "no adapter"


def test_run_pipeline_retries_only_typed_adapter_failures_when_fallback_is_allowed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class Primary(Adapter):
        name = "primary"
        extensions = {".fallback"}

        def extract(self, source: Path, *, progress=None) -> dict:
            raise AdapterError("primary unavailable")

    class Fallback(Adapter):
        name = "fallback"
        extensions = {".fallback"}

        def extract(self, source: Path, *, progress=None) -> dict:
            return {"title": "fallback", "body_md": "recovered"}

    monkeypatch.setattr(router, "_ADAPTERS", [Primary(), Fallback()])
    (tmp_path / "note.fallback").write_text("source", encoding="utf-8")

    record = run_pipeline(
        RunOptions(
            input_root=tmp_path,
            output_root=tmp_path / "out",
            fmt="md",
            allow_fallback=True,
            use_cache=False,
        )
    )

    assert len(record.results) == 1
    assert record.results[0].status == "ok"
    assert record.results[0].engine == "fallback"
    assert record.results[0].metrics is not None
    assert record.results[0].metrics.engine_attempts == ["primary", "fallback"]
    assert [diagnostic.code for diagnostic in record.results[0].diagnostics] == [
        "ENGINE_ATTEMPT_FAILED",
        "ENGINE_ATTEMPT_SUCCEEDED",
    ]
    manifest = json.loads((tmp_path / "out" / "manifest.json").read_text(encoding="utf-8"))
    assert [diagnostic["code"] for diagnostic in manifest["results"][0]["diagnostics"]] == [
        "ENGINE_ATTEMPT_FAILED",
        "ENGINE_ATTEMPT_SUCCEEDED",
    ]


def test_run_pipeline_does_not_retry_untyped_adapter_errors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[str] = []

    class Primary(Adapter):
        name = "primary"
        extensions = {".untyped"}

        def extract(self, source: Path, *, progress=None) -> dict:
            calls.append(self.name)
            raise RuntimeError("unexpected failure")

    class Fallback(Adapter):
        name = "fallback"
        extensions = {".untyped"}

        def extract(self, source: Path, *, progress=None) -> dict:
            calls.append(self.name)
            return {"title": "fallback", "body_md": "should not run"}

    monkeypatch.setattr(router, "_ADAPTERS", [Primary(), Fallback()])
    (tmp_path / "note.untyped").write_text("source", encoding="utf-8")

    record = run_pipeline(
        RunOptions(
            input_root=tmp_path,
            output_root=tmp_path / "out",
            fmt="md",
            allow_fallback=True,
            use_cache=False,
        )
    )

    assert calls == ["primary"]
    assert record.results[0].status == "failed"
    assert record.results[0].error == "RuntimeError: unexpected failure"
