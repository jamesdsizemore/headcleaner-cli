"""End-to-end tests for the `headcleaner view` CLI subcommand (v0.10.0)."""
from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from headcleaner.cli import cli


@pytest.fixture
def bundle(tmp_path: Path) -> Path:
    """OKF bundle with 3 concepts and links between them."""
    d = tmp_path / "okf"
    (d / "concepts").mkdir(parents=True)
    (d / "concepts" / "a.md").write_text(
        "---\ntype: Document\ntitle: A\n---\n\n# A\n\nSee [B](b.md).", encoding="utf-8")
    (d / "concepts" / "b.md").write_text(
        "---\ntype: Document\ntitle: B\n---\n\n# B\n\nSee [C](c.md).", encoding="utf-8")
    (d / "concepts" / "c.md").write_text(
        "---\ntype: Document\ntitle: C\n---\n\n# C", encoding="utf-8")
    return d


def test_view_writes_default_viz_html(bundle: Path, tmp_path: Path):
    """`headcleaner view <bundle>` writes <bundle>/viz.html by default."""
    runner = CliRunner()
    result = runner.invoke(cli, ["view", str(bundle)])
    assert result.exit_code == 0, result.output
    assert (bundle / "viz.html").exists()
    assert "rendered 3 concepts, 2 links" in result.output


def test_view_respects_out_flag(bundle: Path, tmp_path: Path):
    """`headcleaner view <bundle> -o out.html` writes to the named path."""
    out = tmp_path / "custom.html"
    runner = CliRunner()
    result = runner.invoke(cli, ["view", str(bundle), "-o", str(out)])
    assert result.exit_code == 0, result.output
    assert out.exists()


def test_view_layout_option(bundle: Path, tmp_path: Path):
    """`--layout grid` propagates to the HTML."""
    out = tmp_path / "out.html"
    runner = CliRunner()
    result = runner.invoke(cli, ["view", str(bundle), "-o", str(out), "--layout", "grid"])
    assert result.exit_code == 0, result.output
    html = out.read_text(encoding="utf-8")
    assert "'grid'" in html or '"grid"' in html


def test_view_missing_bundle_errors(tmp_path: Path):
    """Non-existent bundle path produces a clear error."""
    runner = CliRunner()
    result = runner.invoke(cli, ["view", str(tmp_path / "nope")])
    # click returns exit code 2 for missing path arg
    assert result.exit_code != 0


def test_view_help_in_docstring():
    """Help text mentions the upstream credit + key features."""
    runner = CliRunner()
    result = runner.invoke(cli, ["view", "--help"])
    assert result.exit_code == 0
    assert "scaccogatto" in result.output
    assert "viz" in result.output.lower() or "graph" in result.output.lower()


def test_view_in_subcommand_list():
    """`headcleaner --help` lists `view`."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "view" in result.output