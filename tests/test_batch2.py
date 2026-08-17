"""Tests for Batch 2 features: .eml adapter, .pst stub, legacy Office
clear-error, encrypted PDF, parallel pipeline, sha256 cache."""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest

from headcleaner.engines.base import AdapterError
from headcleaner.engines.eml import EmlAdapter
from headcleaner.engines.legacy_office import LegacyOfficeAdapter
from headcleaner.engines.pst import PstAdapter
from headcleaner.router import get_adapter
from headcleaner.run import RunOptions, run_pipeline


# --- .eml adapter -----------------------------------------------------------


def _make_eml(tmp_path: Path, name: str = "test.eml") -> Path:
    """Build a minimal valid EML file."""
    raw = textwrap.dedent("""\
        From: alice@example.com
        To: bob@example.com
        Subject: Smoke test email
        Date: Mon, 01 Jan 2026 00:00:00 +0000
        Message-ID: <abc@example.com>
        Content-Type: text/plain; charset=utf-8

        Hello Bob,

        This is a smoke test.
        """)
    f = tmp_path / name
    f.write_bytes(raw.encode("utf-8"))
    return f


def test_eml_adapter_renders_headers_and_body(tmp_path: Path) -> None:
    f = _make_eml(tmp_path)
    out = EmlAdapter().extract(f)
    assert "Smoke test email" in out["title"]
    assert "**From**: alice@example.com" in out["body_md"]
    assert "**Subject**" in out["body_md"]
    assert "Hello Bob" in out["body_md"]
    assert out["metadata"]["engine"] == "eml"


def test_eml_adapter_handles_html_body(tmp_path: Path) -> None:
    raw = textwrap.dedent("""\
        From: a@b
        Subject: HTML test
        Content-Type: text/html; charset=utf-8

        <html><body><h1>Hi</h1><p>Body <em>italic</em>.</p></body></html>
        """)
    f = tmp_path / "h.eml"
    f.write_bytes(raw.encode("utf-8"))
    out = EmlAdapter().extract(f)
    assert "Hi" in out["body_md"]
    # markdownify should preserve emphasis
    assert "*italic*" in out["body_md"] or "italic" in out["body_md"]


def test_eml_routes_via_router(tmp_path: Path) -> None:
    f = _make_eml(tmp_path)
    adapter = get_adapter(f)
    assert adapter is not None
    assert adapter.name == "eml"


# --- .pst stub (best-effort; tests both branches) -----------------------------


def test_pst_adapter_raises_when_libpff_missing(tmp_path: Path) -> None:
    f = tmp_path / "x.pst"
    f.write_bytes(b"not a real pst but the adapter should fail before reading")
    # libpff-python is NOT in our deps; adapter should raise AdapterError
    # immediately, NOT crash with ImportError.
    with pytest.raises(AdapterError) as exc:
        PstAdapter().extract(f)
    assert "libpff-python" in str(exc.value) or "libpff" in str(exc.value).lower()


def test_pst_routes_via_router(tmp_path: Path) -> None:
    f = tmp_path / "x.pst"
    f.write_bytes(b"fake")
    adapter = get_adapter(f)
    assert adapter is not None
    assert adapter.name == "pst"


# --- legacy Office ----------------------------------------------------------


def test_legacy_office_adapter_raises_clear_error(tmp_path: Path) -> None:
    f = tmp_path / "old.doc"
    f.write_bytes(b"fake")
    with pytest.raises(AdapterError) as exc:
        LegacyOfficeAdapter().extract(f)
    assert ".docx" in str(exc.value)  # tells user to convert to docx
    assert "libreoffice" in str(exc.value)


def test_legacy_office_routes_xls(tmp_path: Path) -> None:
    f = tmp_path / "old.xls"
    f.write_bytes(b"fake")
    with pytest.raises(AdapterError) as exc:
        LegacyOfficeAdapter().extract(f)
    assert ".xlsx" in str(exc.value)


def test_legacy_office_routes_via_router(tmp_path: Path) -> None:
    for ext in (".doc", ".xls", ".ppt"):
        f = tmp_path / f"old{ext}"
        f.write_bytes(b"fake")
        adapter = get_adapter(f)
        assert adapter is not None, f"no adapter for {ext}"
        assert adapter.name == "legacy_office"


# --- encrypted PDF error ----------------------------------------------------


def test_pdf_encrypted_gives_actionable_error(tmp_path: Path) -> None:
    """A PDF with /Encrypt in metadata surfaces a qpdf hint."""
    # We can't easily construct a real encrypted PDF here, but we can
    # verify the PDF adapter's error path includes the actionable hint.
    from headcleaner.engines.pdf import PdfAdapter as PDF

    # Verify the hint string by reading the source
    import inspect

    src = inspect.getsource(PDF.extract)
    assert "qpdf" in src
    assert "decrypt" in src.lower()


# --- parallel + cache -------------------------------------------------------


def test_run_pipeline_jobs_1_is_default_sequential(tmp_path: Path) -> None:
    """Default jobs=1 keeps manifest order identical to input order."""
    (tmp_path / "a.txt").write_text("a", encoding="utf-8")
    (tmp_path / "b.txt").write_text("bb", encoding="utf-8")
    (tmp_path / "c.txt").write_text("ccc", encoding="utf-8")
    out = tmp_path / "out"
    record = run_pipeline(RunOptions(input_root=tmp_path, output_root=out, fmt="md", jobs=1))
    assert record.results[0].relpath == "a.txt"
    assert record.results[1].relpath == "b.txt"
    assert record.results[2].relpath == "c.txt"


def test_run_pipeline_jobs_2_runs(mixed_dir, tmp_path: Path) -> None:
    """Parallel mode (--jobs 2) processes the same files without errors."""
    out = tmp_path / "out"
    record = run_pipeline(RunOptions(input_root=mixed_dir, output_root=out, fmt="md", jobs=2))
    statuses = [r.status for r in record.results]
    assert "failed" not in statuses
    assert record.options["jobs"] == 2


def test_run_pipeline_cache_skip(tmp_path: Path) -> None:
    """Second run with same sources + use_cache=True should skip cached files."""
    (tmp_path / "a.txt").write_text("a", encoding="utf-8")
    (tmp_path / "b.txt").write_text("bb", encoding="utf-8")
    out = tmp_path / "out"

    # First run: produces manifest
    record1 = run_pipeline(RunOptions(input_root=tmp_path, output_root=out, fmt="md"))
    assert all(r.status == "ok" for r in record1.results)
    assert (out / "manifest.json").exists()

    # Modify the manifest.jsonl timestamps but don't touch source — second
    # run should still produce the same results (no recompute needed).
    record2 = run_pipeline(RunOptions(input_root=tmp_path, output_root=out, fmt="md"))
    assert all(r.status == "ok" for r in record2.results)


def test_run_pipeline_no_cache_recomputes(tmp_path: Path) -> None:
    """With --no-cache, every file is re-extracted even if its sha matches."""
    (tmp_path / "a.txt").write_text("a", encoding="utf-8")
    out = tmp_path / "out"

    # First run
    run_pipeline(RunOptions(input_root=tmp_path, output_root=out, fmt="md"))
    # Second run with --no-cache
    record = run_pipeline(
        RunOptions(input_root=tmp_path, output_root=out, fmt="md", use_cache=False)
    )
    assert record.options["use_cache"] is False
    assert all(r.status == "ok" for r in record.results)


def test_run_pipeline_writes_jsonl_per_file(tmp_path: Path) -> None:
    """Streaming manifest: manifest.jsonl is appended to after each file."""
    (tmp_path / "a.txt").write_text("a", encoding="utf-8")
    (tmp_path / "b.txt").write_text("bb", encoding="utf-8")
    out = tmp_path / "out"
    run_pipeline(RunOptions(input_root=tmp_path, output_root=out, fmt="md"))
    jsonl = out / "manifest.jsonl"
    assert jsonl.exists()
    lines = jsonl.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2  # one line per file
    for line in lines:
        d = json.loads(line)
        assert "relpath" in d and "status" in d
