from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from headcleaner.cli import cli


def test_benchmark_emits_fixture_metrics_and_updates_explicit_baseline(tmp_path: Path) -> None:
    fixtures = tmp_path / "fixtures"
    fixtures.mkdir()
    (fixtures / "note.txt").write_text("# Heading\n\nRetained anchor\n", encoding="utf-8")
    (fixtures / "expectations.json").write_text(
        json.dumps({"note.txt": {"text_anchors": ["Retained anchor"], "headings": ["Heading"]}}),
        encoding="utf-8",
    )
    baseline = tmp_path / "baseline.json"

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["benchmark", str(fixtures), "--baseline", str(baseline), "--update-baseline", "--json"],
    )

    assert result.exit_code == 0, result.output
    report = json.loads(result.output)
    assert report["schema_version"] == "1.0"
    assert report["summary"]["fixture_count"] == 1
    assert report["fixtures"][0]["metrics"] == {
        "heading_order": 1.0,
        "output_exists": 1.0,
        "table_anchor_recall": 1.0,
        "text_anchor_recall": 1.0,
    }
    assert baseline.exists()
    assert not (fixtures / ".benchmark-output").exists()


def test_benchmark_fails_when_expected_anchor_is_missing(tmp_path: Path) -> None:
    fixtures = tmp_path / "fixtures"
    fixtures.mkdir()
    (fixtures / "note.txt").write_text("Only actual text\n", encoding="utf-8")
    (fixtures / "expectations.json").write_text(
        json.dumps({"note.txt": {"text_anchors": ["missing anchor"]}}), encoding="utf-8"
    )

    result = CliRunner().invoke(cli, ["benchmark", str(fixtures), "--json"])

    assert result.exit_code != 0
    assert "text_anchor_recall" in result.output
