"""Tests for the all2md fallback adapter (v0.8.0)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from headcleaner.engines.all2md_engine import (
    ALL2MD_EXTRA_EXTENSIONS,
    All2mdAdapter,
    all2md_available,
)


def test_all2md_available_returns_bool() -> None:
    """all2md_available returns a bool."""
    assert isinstance(all2md_available(), bool)


@pytest.mark.skipif(not all2md_available(), reason="all2md not installed")
def test_adapter_constructs_with_all2md() -> None:
    """Adapter constructs when all2md is installed."""
    adapter = All2mdAdapter()
    assert adapter.name == "all2md"


def test_extra_extensions_include_ipynb() -> None:
    """Jupyter notebooks are in the extra extensions."""
    assert ".ipynb" in ALL2MD_EXTRA_EXTENSIONS


def test_extra_extensions_include_latex() -> None:
    """LaTeX files are in the extra extensions."""
    assert ".latex" in ALL2MD_EXTRA_EXTENSIONS
    assert ".tex" in ALL2MD_EXTRA_EXTENSIONS


def test_extra_extensions_include_sourcecode() -> None:
    """Source code files are in the extra extensions."""
    for ext in [".py", ".js", ".ts", ".go", ".rs"]:
        assert ext in ALL2MD_EXTRA_EXTENSIONS


def test_extra_extensions_does_not_include_office() -> None:
    """Office formats are NOT in all2md's set (we have native OfficeCLI / office_oxide)."""
    assert ".docx" not in ALL2MD_EXTRA_EXTENSIONS
    assert ".xlsx" not in ALL2MD_EXTRA_EXTENSIONS
    assert ".pptx" not in ALL2MD_EXTRA_EXTENSIONS


@pytest.mark.skipif(not all2md_available(), reason="all2md not installed")
def test_adapter_extracts_json(tmp_path: Path) -> None:
    """Adapter extracts JSON files via all2md."""
    p = tmp_path / "data.json"
    p.write_text(json.dumps({"name": "test", "value": 42}), encoding="utf-8")
    adapter = All2mdAdapter()
    result = adapter.extract(p)
    assert "body_md" in result
    assert "name" in result["body_md"]
    assert result["metadata"]["backend"] == "all2md"


@pytest.mark.skipif(not all2md_available(), reason="all2md not installed")
def test_adapter_calls_progress(tmp_path: Path) -> None:
    """Adapter reports at least one progress tick."""
    p = tmp_path / "data.json"
    p.write_text("{}", encoding="utf-8")
    progress_calls: list[tuple[int, int]] = []

    def progress(cur: int, total: int) -> None:
        progress_calls.append((cur, total))

    adapter = All2mdAdapter()
    adapter.extract(p, progress=progress)
    assert len(progress_calls) >= 1


@pytest.mark.skipif(not all2md_available(), reason="all2md not installed")
def test_router_picks_all2md_for_ipynb(tmp_path: Path) -> None:
    """The router returns All2mdAdapter for .ipynb files."""
    from headcleaner.router import get_adapter

    p = tmp_path / "notebook.ipynb"
    p.write_text(
        json.dumps({"cells": [], "metadata": {}, "nbformat": 4, "nbformat_minor": 5}),
        encoding="utf-8",
    )
    adapter = get_adapter(p)
    assert adapter is not None
    assert adapter.name == "all2md"


def test_router_does_not_break_without_all2md() -> None:
    """If all2md is not installed, the router still returns valid adapters for native formats."""
    from headcleaner.router import get_adapter

    p = Path("tests/fixtures/sample.xlsx")
    adapter = get_adapter(p)
    # Either officecli or office_oxide handles xlsx; both have name "officecli"
    assert adapter is not None
    assert adapter.name == "officecli"
