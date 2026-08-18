from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from headcleaner.cli import cli
from headcleaner.render_verify import verify_render


def test_verify_render_reports_unavailable_without_writing_artifacts(tmp_path: Path) -> None:
    source = tmp_path / "source.unknown"
    output = tmp_path / "output.md"
    source.write_text("source", encoding="utf-8")
    output.write_text("# output\n", encoding="utf-8")

    report = verify_render(source, output, output_dir=tmp_path / "verification")

    assert report.status == "unavailable"
    assert report.page_results == ()
    assert report.warnings
    assert not (tmp_path / "verification").exists()


def test_verify_render_persists_text_markdown_structural_report(tmp_path: Path) -> None:
    source = tmp_path / "source.txt"
    output = tmp_path / "output.md"
    source.write_text("Heading\n\nShared anchor\n", encoding="utf-8")
    output.write_text("# Heading\n\nShared anchor\n", encoding="utf-8")

    report = verify_render(source, output, output_dir=tmp_path / "verification")

    assert report.status == "ok"
    assert report.renderer == "text-structural"
    assert report.page_results[0]["text_anchors_match"] is True
    persisted = list((tmp_path / "verification").glob("*/report.json"))
    assert len(persisted) == 1


def test_verify_render_cli_emits_json_for_advisory_result(tmp_path: Path) -> None:
    source = tmp_path / "source.txt"
    output = tmp_path / "output.md"
    source.write_text("source", encoding="utf-8")
    output.write_text("different", encoding="utf-8")

    result = CliRunner().invoke(cli, ["verify-render", str(source), str(output), "--json"])

    assert result.exit_code == 0
    assert '"status": "ok"' in result.output
