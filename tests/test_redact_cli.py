from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from headcleaner.cli import cli


def test_redact_cli_is_proposal_only_unless_derivative_is_explicit(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    (bundle / "note.md").write_text(
        "---\ntype: Document\n---\nAPI key: sk-abcdefghijklmnopqrstuvwxyz123456\n",
        encoding="utf-8",
    )
    runner = CliRunner()

    proposal = runner.invoke(cli, ["redact", str(bundle), "--json"])
    assert proposal.exit_code == 0, proposal.output
    assert "sk-" not in proposal.output
    assert not (bundle / "_redacted").exists()

    write = runner.invoke(cli, ["redact", str(bundle), "--write-derivative", "--json"])
    assert write.exit_code == 0, write.output
    assert (bundle / "_redacted" / "note.md").is_file()
