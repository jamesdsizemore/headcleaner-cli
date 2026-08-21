from __future__ import annotations

from click.testing import CliRunner

from headcleaner.cli import cli


def test_policy_explain_prints_the_selected_shipped_rule() -> None:
    result = CliRunner().invoke(
        cli,
        ["policy", "explain", "--pack", "research", "--rule", "sources-required"],
    )

    assert result.exit_code == 0, result.output
    assert "sources-required" in result.output
    assert "sources.missing" in result.output
    assert "A source citation is required." in result.output
