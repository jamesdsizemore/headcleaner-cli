"""Tests for the Batch 4d skeleton modules (notion, attest, glob_repl)."""
from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from headcleaner.attest import build_attestation, canonical_hash
from headcleaner.glob_repl import count_matches
from headcleaner.notion import NotionImportError, detect_export


# --- Eng #36: attest -----------------------------------------------------

def test_canonical_hash_is_deterministic(tmp_path: Path) -> None:
    """canonical_hash returns the same SHA-256 for the same content."""
    f = tmp_path / "x.md"
    f.write_text("hello", encoding="utf-8")
    a = canonical_hash(f)
    b = canonical_hash(f)
    assert a == b
    assert len(a) == 64


def test_build_attestation_enumerates_concepts(tmp_path: Path) -> None:
    """build_attestation enumerates concepts and computes a real Merkle root (v0.7 full impl)."""
    bundle = tmp_path / "okf"
    bundle.mkdir()
    (bundle / "a.md").write_text(
        "---\ntype: Document\n---\nA body.\n", encoding="utf-8"
    )
    (bundle / "b.md").write_text(
        "---\ntype: Document\n---\nB body.\n", encoding="utf-8"
    )
    payload = build_attestation(bundle)
    assert payload["concept_count"] == 2
    assert "a.md" in payload["concepts"]
    assert "b.md" in payload["concepts"]
    # v0.7: real Merkle root (no signature without a key)
    assert payload["merkle_root"] is not None
    assert payload["signature"] is None
    assert payload["public_key"] is None


def test_build_attestation_skips_index_log(tmp_path: Path) -> None:
    """index.md and log.md are not concepts — must be skipped."""
    bundle = tmp_path / "okf"
    bundle.mkdir()
    (bundle / "index.md").write_text("# Index\n", encoding="utf-8")
    (bundle / "log.md").write_text("# Log\n", encoding="utf-8")
    payload = build_attestation(bundle)
    assert payload["concept_count"] == 0


# --- Eng #31: notion -----------------------------------------------------

def test_detect_export_on_real_zip(tmp_path: Path) -> None:
    """detect_export reads a synthetic Notion export zip."""
    export = tmp_path / "notion-export.zip"
    with zipfile.ZipFile(export, "w") as zf:
        zf.writestr("Database.csv", "Name,Title\nFoo,Bar")
        zf.writestr("Page 1.md", "# Page 1\n")
        zf.writestr("Page 2.md", "# Page 2\n")
        zf.writestr("attachments/img.png", b"\x89PNG")

    counts = detect_export(export)
    assert counts["databases"] == 1
    assert counts["pages"] == 2
    assert counts["files"] >= 1


def test_detect_export_missing_path(tmp_path: Path) -> None:
    """detect_export raises NotionImportError when the path is missing."""
    with pytest.raises(NotionImportError):
        detect_export(tmp_path / "no-such-file.zip")


def test_import_notion_export_returns_count(tmp_path: Path) -> None:
    """import_notion_export returns the number of imported concepts (v0.7 full impl)."""
    from headcleaner.notion import import_notion_export
    export = tmp_path / "notion.zip"
    with zipfile.ZipFile(export, "w") as zf:
        zf.writestr("x.md", "# x\nbody")
    n = import_notion_export(export, tmp_path / "out")
    assert isinstance(n, int)
    assert n >= 1


# --- Eng #44: glob REPL --------------------------------------------------

def test_count_matches_returns_correct_number(tmp_path: Path) -> None:
    """count_matches correctly counts files matching a glob."""
    (tmp_path / "a.pdf").write_text("x")
    (tmp_path / "b.pdf").write_text("x")
    (tmp_path / "c.txt").write_text("x")
    assert count_matches(tmp_path, "*.pdf") == 2
    assert count_matches(tmp_path, "*.txt") == 1
    assert count_matches(tmp_path, "*.docx") == 0