"""Tests for the folder walker (walk.py)."""

from __future__ import annotations

from pathlib import Path

from headcleaner.walk import walk, manifest_json, sha256_of


def test_walk_finds_supported_files(mixed_dir: Path) -> None:
    paths = [sf.relpath.as_posix() for sf in walk(mixed_dir)]
    assert "test.docx" in paths
    assert "test.pdf" in paths
    assert "test.html" in paths
    assert "test.txt" in paths


def test_walk_finds_nested_files(mixed_dir: Path) -> None:
    paths = [sf.relpath.as_posix() for sf in walk(mixed_dir)]
    assert "sub/nested.pdf" in paths


def test_walk_skips_hidden_files(mixed_dir: Path) -> None:
    paths = [sf.relpath.as_posix() for sf in walk(mixed_dir)]
    assert not any(p.startswith(".") for p in paths)


def test_walk_respects_include_glob(mixed_dir: Path) -> None:
    paths = [sf.path.name for sf in walk(mixed_dir, include_glob=["*.txt"])]
    assert paths == ["test.txt"]


def test_walk_respects_exclude_glob(mixed_dir: Path) -> None:
    paths = [sf.path.name for sf in walk(mixed_dir, exclude_glob=["*.pdf"])]
    assert "test.pdf" not in paths
    assert "sub/nested.pdf" not in paths
    assert "test.docx" in paths


def test_walk_raises_on_missing_root(tmp_path: Path) -> None:
    import pytest as _pt

    with _pt.raises(NotADirectoryError):
        list(walk(tmp_path / "does-not-exist"))


def test_sha256_of_is_deterministic(tmp_path: Path) -> None:
    f = tmp_path / "a.txt"
    f.write_text("hello", encoding="utf-8")
    h1 = sha256_of(f)
    h2 = sha256_of(f)
    assert h1 == h2
    assert len(h1) == 64  # SHA-256 hex


def test_manifest_json_is_valid(mixed_dir: Path) -> None:
    import json

    m = json.loads(manifest_json(mixed_dir))
    assert m["count"] == 5  # 4 root + 1 nested
    assert all("sha256" in f and len(f["sha256"]) == 64 for f in m["files"])
    assert all(f["engine"] is not None for f in m["files"])
    assert all(f["supported"] is True for f in m["files"])
