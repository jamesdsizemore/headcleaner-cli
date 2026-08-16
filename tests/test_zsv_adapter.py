"""Tests for the zsv SIMD CSV adapter (v0.9.0).

These tests rely on the zsv binary being on PATH. If zsv is not installed,
most tests are skipped via the ``zsv_available`` guard.
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest

from headcleaner.engines.zsv import ZsvAdapter, zsv_available


@pytest.fixture(scope="session")
def zsv_on_path() -> None:
    """Make sure zsv is on PATH for the duration of the test session.

    If not present, the zsv_available() check will skip all but the
    structural tests below.
    """
    zsv_dir = Path("C:/tmp/zsv-bin")
    if zsv_dir.exists() and zsv_dir.is_dir():
        zsv_exe = zsv_dir / ("zsv.exe" if os.name == "nt" else "zsv")
        if zsv_exe.exists():
            current = os.environ.get("PATH", "")
            if str(zsv_dir) not in current:
                os.environ["PATH"] = str(zsv_dir) + os.pathsep + current


def test_zsv_available_returns_bool(zsv_on_path: None) -> None:
    """zsv_available returns a bool."""
    assert isinstance(zsv_available(), bool)


@pytest.mark.skipif(not zsv_available(), reason="zsv binary not on PATH")
def test_adapter_constructs_with_zsv(zsv_on_path: None) -> None:
    """Adapter constructs and claims .csv/.tsv when zsv is installed."""
    a = ZsvAdapter()
    assert a.name == "zsv"
    assert ".csv" in a.extensions
    assert ".tsv" in a.extensions


@pytest.mark.skipif(zsv_available(), reason="zsv is installed; this tests the no-zsv path")
def test_adapter_no_zsv_extensions_empty(zsv_on_path: None) -> None:
    """Without zsv on PATH, the adapter claims no extensions (router skips it)."""
    a = ZsvAdapter()
    assert a.extensions == set()


@pytest.mark.skipif(not zsv_available(), reason="zsv binary not on PATH")
def test_adapter_extracts_basic_csv(zsv_on_path: None, tmp_path: Path) -> None:
    """Adapter reads a basic CSV via zsv check + stdlib parse, emits GFM table."""
    p = tmp_path / "data.csv"
    p.write_text("name,score,city\nAlice,92,NYC\nBob,87,LA\n", encoding="utf-8")
    a = ZsvAdapter()
    result = a.extract(p)
    assert "name" in result["body_md"]
    assert "Alice" in result["body_md"]
    assert "Bob" in result["body_md"]
    assert result["metadata"]["backend"] == "zsv"
    assert result["metadata"]["zsv_validated"] is True


@pytest.mark.skipif(not zsv_available(), reason="zsv binary not on PATH")
def test_adapter_handles_empty_csv(zsv_on_path: None, tmp_path: Path) -> None:
    """Adapter handles an empty CSV gracefully."""
    p = tmp_path / "empty.csv"
    p.write_text("", encoding="utf-8")
    a = ZsvAdapter()
    result = a.extract(p)
    assert "empty" in result["body_md"].lower() or result["body_md"].strip() == ""


@pytest.mark.skipif(not zsv_available(), reason="zsv binary not on PATH")
def test_adapter_calls_progress(zsv_on_path: None, tmp_path: Path) -> None:
    """Adapter reports progress ticks."""
    p = tmp_path / "rows.csv"
    rows = ["col1,col2\n"] + [f"a{i},b{i}\n" for i in range(50)]
    p.write_text("".join(rows), encoding="utf-8")
    progress_calls: list[tuple[int, int]] = []

    def progress(cur: int, total: int) -> None:
        progress_calls.append((cur, total))

    a = ZsvAdapter()
    a.extract(p, progress=progress)
    assert len(progress_calls) >= 1


@pytest.mark.skipif(not zsv_available(), reason="zsv binary not on PATH")
def test_adapter_escapes_pipes(zsv_on_path: None, tmp_path: Path) -> None:
    """Cells containing pipes get escaped for GFM tables."""
    p = tmp_path / "pipes.csv"
    p.write_text("name,note\nAlice,has|pipe\n", encoding="utf-8")
    a = ZsvAdapter()
    result = a.extract(p)
    assert "has\\|pipe" in result["body_md"]


@pytest.mark.skipif(not zsv_available(), reason="zsv binary not on PATH")
def test_router_picks_zsv_for_csv(zsv_on_path: None, tmp_path: Path) -> None:
    """When zsv is installed, the ZsvAdapter is registered and routable for .csv."""
    from headcleaner.router import _ADAPTERS, get_adapter

    # The router registers zsv at import time only if zsv is on PATH then.
    # If PATH was set after the router was first imported (the common case
    # under pytest), force a reload so the registration block re-runs.
    import importlib
    import headcleaner.router
    importlib.reload(headcleaner.router)
    from headcleaner.router import _ADAPTERS, get_adapter

    registered_names = [a.name for a in _ADAPTERS]
    assert "zsv" in registered_names, f"ZsvAdapter not registered; got {registered_names}"

    p = tmp_path / "test.csv"
    p.write_text("a,b\n1,2\n", encoding="utf-8")
    adapter = get_adapter(p)
    assert adapter is not None
    assert adapter.name == "zsv"


@pytest.mark.skipif(not zsv_available(), reason="zsv binary not on PATH")
def test_adapter_tsv_file(zsv_on_path: None, tmp_path: Path) -> None:
    """Adapter handles .tsv files via zsv's --tab-delim flag fallback to dialect sniff."""
    p = tmp_path / "data.tsv"
    p.write_text("name\tscore\nAlice\t92\n", encoding="utf-8")
    a = ZsvAdapter()
    result = a.extract(p)
    assert "Alice" in result["body_md"]
    assert result["metadata"]["source_format"] == ".tsv"