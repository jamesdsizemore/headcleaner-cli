"""Localization contracts for CLI and TUI runtime strings."""

from __future__ import annotations

import warnings
from pathlib import Path

from click.testing import CliRunner

from headcleaner.cli import cli
from headcleaner.i18n import get_locale, set_locale, tr
from headcleaner.run import RunOptions
from headcleaner.tui import HeadCleanerApp


def test_gettext_catalogs_translate_spanish_and_simplified_chinese() -> None:
    set_locale("es")
    assert get_locale() == "es"
    assert tr("input") == "entrada"

    set_locale("zh-CN")
    assert get_locale() == "zh_CN"
    assert tr("input") == "输入"


def test_cli_lang_option_localizes_plain_runtime_output(tmp_path: Path) -> None:
    source = tmp_path / "in"
    source.mkdir()
    output = tmp_path / "out"

    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        result = CliRunner().invoke(
            cli,
            ["--lang", "es", "convert", str(source), "--output", str(output), "--no-tui"],
        )

    assert not any("parameter --tui is used more than once" in str(w.message) for w in captured)
    assert result.exit_code == 0, result.output
    assert "entrada:" in result.output
    assert "salida:" in result.output
    assert "completado" in result.output


def test_tui_uses_the_active_catalog_for_status_labels(tmp_path: Path) -> None:
    set_locale("zh-CN")
    opts = RunOptions(input_root=tmp_path, output_root=tmp_path / "out")

    app = HeadCleanerApp(opts)

    assert "运行中" in app._status_label()
