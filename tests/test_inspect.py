from __future__ import annotations

import zipfile
from pathlib import Path

from headcleaner.inspect import inspect_file


def test_inspection_quarantines_traversal_archive_without_extracting_members(tmp_path: Path) -> None:
    source = tmp_path / "hostile.zip"
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr("../escape.txt", "not extracted")

    result = inspect_file(source)

    assert result.disposition == "quarantine"
    assert result.declared_type == "zip"
    assert result.detected_type == "zip"
    assert result.archive_summary["member_count"] == 1
    assert result.findings[0]["code"] == "archive_traversal"
    assert not (tmp_path / "escape.txt").exists()


def test_inspection_quarantines_known_signature_mismatch(tmp_path: Path) -> None:
    source = tmp_path / "masquerade.docx"
    source.write_bytes(b"%PDF-1.7\nnot an Office document")

    result = inspect_file(source)

    assert result.disposition == "quarantine"
    assert result.declared_type == "docx"
    assert result.detected_type == "pdf"
    assert result.findings == (
        {"code": "type_mismatch", "declared": "docx", "detected": "pdf"},
    )


def test_inspection_quarantines_encrypted_archive_without_reading_members(tmp_path: Path) -> None:
    source = tmp_path / "encrypted.zip"
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr("secret.txt", b"do not read")
    payload = bytearray(source.read_bytes())
    for signature, flag_offset in ((b"PK\x03\x04", 6), (b"PK\x01\x02", 8)):
        index = payload.index(signature)
        payload[index + flag_offset] |= 0x01
    source.write_bytes(payload)

    result = inspect_file(source)

    assert result.disposition == "quarantine"
    assert result.encryption is True
    assert result.findings == ({"code": "archive_encrypted"},)


def test_inspection_quarantines_macro_indicator_from_inventory_only(tmp_path: Path) -> None:
    source = tmp_path / "macro.docx"
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr("word/VBAPROJECT.BIN", b"not executed")

    result = inspect_file(source)

    assert result.disposition == "quarantine"
    assert result.macro_indicators == ("word/VBAPROJECT.BIN",)
    assert result.findings == (
        {"code": "macro_indicator", "members": ("word/VBAPROJECT.BIN",)},
    )
