"""Contracts for real PST fixture integrity and Windows readpst discovery."""

from __future__ import annotations

import hashlib
from pathlib import Path

from headcleaner.engines.pst import _readpst_available, _windows_readpst_paths

FIXTURE = Path(__file__).parent / "fixtures" / "outlook.pst"
FIXTURE_SHA256 = "df01707f76d0e24ab913cf1ffeffa6eaf9c1d590e02102c7ed26bb3ac51d4e24"


def test_public_pst_fixture_is_real_and_pinned() -> None:
    """The checked-in CC-BY fixture is a stable, non-mocked PST binary."""
    data = FIXTURE.read_bytes()
    assert data.startswith(b"!BDN")
    assert hashlib.sha256(data).hexdigest() == FIXTURE_SHA256
    assert (FIXTURE.parent / "ATTRIBUTION.md").is_file()


def test_readpst_honors_explicit_windows_override(monkeypatch, tmp_path: Path) -> None:
    binary = tmp_path / "readpst.exe"
    binary.write_bytes(b"fixture")
    monkeypatch.setenv("HEADCLEANER_READPST", str(binary))

    assert _readpst_available() == str(binary)


def test_windows_readpst_candidates_cover_msys2_installations() -> None:
    paths = _windows_readpst_paths({"MSYS2_ROOT": r"C:\tools\msys64"})
    normalized = {str(path).replace("/", "\\") for path in paths}

    assert r"C:\tools\msys64\usr\bin\readpst.exe" in normalized
    assert r"C:\tools\msys64\ucrt64\bin\readpst.exe" in normalized
