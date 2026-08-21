from __future__ import annotations

import json
import zipfile
from pathlib import Path

from click.testing import CliRunner

from headcleaner.cli import cli


def test_inspect_cli_json_quarantines_hostile_archive(tmp_path: Path) -> None:
    source = tmp_path / "hostile.zip"
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr("../escape.txt", "unsafe")

    result = CliRunner().invoke(cli, ["inspect", str(source), "--json"])

    assert result.exit_code == 1, result.output
    payload = json.loads(result.output)
    assert payload["disposition"] == "quarantine"
    assert payload["findings"][0]["code"] == "archive_traversal"
