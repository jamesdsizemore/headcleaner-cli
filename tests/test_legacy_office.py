"""Tests for real LibreOffice-backed legacy Office conversion."""

from __future__ import annotations

import shutil
import subprocess
import zipfile
from pathlib import Path
from unittest.mock import ANY

import pytest

from headcleaner.engines.base import AdapterError
from headcleaner.engines.legacy_office import LegacyOfficeAdapter


class _ModernAdapter:
    def __init__(self) -> None:
        self.seen: Path | None = None

    def extract(self, source: Path, *, progress=None) -> dict:
        self.seen = source
        return {
            "title": "Converted",
            "body_md": "# Converted\n",
            "metadata": {"engine": "officecli", "source_format": source.suffix},
            "attachments": [],
        }


def test_legacy_office_requires_a_discoverable_libreoffice_binary(tmp_path: Path) -> None:
    source = tmp_path / "legacy.doc"
    source.write_bytes(b"not a real document")

    adapter = LegacyOfficeAdapter(binary="missing-libreoffice")

    with pytest.raises(AdapterError, match="LibreOffice"):
        adapter.extract(source)


def test_legacy_office_converts_then_extracts_with_modern_adapter(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    source = tmp_path / "legacy.doc"
    source.write_bytes(b"legacy doc")
    modern = _ModernAdapter()
    commands: list[list[str]] = []

    def fake_run(command: list[str], **_kwargs) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        out_dir = Path(command[command.index("--outdir") + 1])
        (out_dir / "legacy.docx").write_bytes(b"modern docx")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr("headcleaner.engines.legacy_office.shutil.which", lambda _: "libreoffice")
    monkeypatch.setattr("headcleaner.engines.legacy_office.subprocess.run", fake_run)

    adapter = LegacyOfficeAdapter(binary="libreoffice", modern_adapter_factory=lambda: modern)
    result = adapter.extract(source)

    assert commands == [
        [
            "libreoffice",
            "--headless",
            ANY,
            "--convert-to",
            "docx",
            "--outdir",
            ANY,
            str(source),
        ]
    ]
    assert modern.seen is not None
    assert modern.seen.suffix == ".docx"
    assert result["metadata"]["legacy_source_format"] == ".doc"
    assert result["metadata"]["converted_with"] == "libreoffice"


def test_legacy_office_surfaces_converter_stderr(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    source = tmp_path / "legacy.xls"
    source.write_bytes(b"legacy xls")

    monkeypatch.setattr("headcleaner.engines.legacy_office.shutil.which", lambda _: "libreoffice")
    monkeypatch.setattr(
        "headcleaner.engines.legacy_office.subprocess.run",
        lambda command, **_kwargs: subprocess.CompletedProcess(command, 1, "", "corrupt input"),
    )


@pytest.mark.parametrize(
    ("source_suffix", "target_suffix"),
    [(".doc", ".docx"), (".xls", ".xlsx"), (".ppt", ".pptx")],
)
def test_legacy_office_real_libreoffice_round_trip(
    tmp_path: Path, source_suffix: str, target_suffix: str
) -> None:
    """Exercise real LibreOffice conversion when its binary is provisioned."""
    binary = shutil.which("libreoffice") or shutil.which("soffice")
    if binary is None:
        pytest.skip("LibreOffice is not installed; CI runs this in its dedicated integration job")

    source = _make_real_legacy_fixture(tmp_path, binary, source_suffix)
    modern = _ModernAdapter()

    def capture_modern(converted: Path, *, progress=None) -> dict:
        assert converted.suffix == target_suffix
        assert converted.is_file()
        assert zipfile.is_zipfile(converted), "LibreOffice did not produce an OOXML archive"
        return modern.extract(converted, progress=progress)

    class CapturingAdapter:
        def extract(self, converted: Path, *, progress=None) -> dict:
            return capture_modern(converted, progress=progress)

    result = LegacyOfficeAdapter(binary=binary, modern_adapter_factory=CapturingAdapter).extract(
        source
    )

    assert result["metadata"]["legacy_source_format"] == source_suffix
    assert result["metadata"]["converted_format"] == target_suffix


def _make_real_legacy_fixture(tmp_path: Path, binary: str, suffix: str) -> Path:
    """Create a valid binary Office input using LibreOffice from a tiny ODF document."""
    from odf.draw import Page
    from odf.opendocument import OpenDocumentPresentation, OpenDocumentSpreadsheet, OpenDocumentText
    from odf.table import Table, TableCell, TableRow
    from odf.text import P

    if suffix == ".doc":
        document = OpenDocumentText()
        document.text.addElement(P(text="HeadCleaner legacy DOC fixture"))
        odf_path = tmp_path / "fixture.odt"
    elif suffix == ".xls":
        document = OpenDocumentSpreadsheet()
        table = Table(name="Sheet1")
        row = TableRow()
        cell = TableCell(valuetype="string")
        cell.addElement(P(text="HeadCleaner legacy XLS fixture"))
        row.addElement(cell)
        table.addElement(row)
        document.spreadsheet.addElement(table)
        odf_path = tmp_path / "fixture.ods"
    else:
        document = OpenDocumentPresentation()
        document.presentation.addElement(Page(name="Slide 1", masterpagename="Default"))
        odf_path = tmp_path / "fixture.odp"

    document.save(str(odf_path))
    assert odf_path.is_file()
    profile = tmp_path / f"source-profile-{suffix.removeprefix('.')}"
    profile.mkdir()
    completed = subprocess.run(
        [
            binary,
            "--headless",
            f"-env:UserInstallation={profile.as_uri()}",
            "--convert-to",
            suffix.removeprefix("."),
            "--outdir",
            str(tmp_path),
            str(odf_path),
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    source = tmp_path / f"fixture{suffix}"
    assert completed.returncode == 0, completed.stderr or completed.stdout
    assert source.is_file(), completed.stderr or completed.stdout
    return source
