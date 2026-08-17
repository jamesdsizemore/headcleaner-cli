"""Tests for the glob REPL (Eng #44 full impl)."""

from __future__ import annotations

from pathlib import Path

from headcleaner.glob_repl import count_matches, list_matches


def test_count_matches_returns_correct_number(tmp_path: Path) -> None:
    """count_matches counts files matching a glob (fnmatch semantics)."""
    (tmp_path / "a.pdf").write_text("x")
    (tmp_path / "b.pdf").write_text("x")
    (tmp_path / "c.txt").write_text("x")
    (tmp_path / "deep").mkdir()
    (tmp_path / "deep" / "d.pdf").write_text("x")  # nested; rglob should find it
    assert count_matches(tmp_path, "*.pdf") == 3  # case-sensitive: 'd.pdf' matches
    assert count_matches(tmp_path, "*.txt") == 1
    assert count_matches(tmp_path, "*.docx") == 0


def test_count_matches_returns_zero_for_missing_dir(tmp_path: Path) -> None:
    """count_matches returns 0 when root doesn't exist."""
    assert count_matches(tmp_path / "nope", "*") == 0


def test_list_matches_respects_limit(tmp_path: Path) -> None:
    """list_matches caps the result list at `limit`."""
    for i in range(15):
        (tmp_path / f"file_{i}.txt").write_text("x")
    out = list_matches(tmp_path, "*.txt", limit=5)
    assert len(out) == 5


def test_list_matches_returns_empty_for_no_match(tmp_path: Path) -> None:
    """list_matches returns [] when nothing matches."""
    (tmp_path / "a.pdf").write_text("x")
    assert list_matches(tmp_path, "*.docx", limit=10) == []


def test_list_matches_handles_missing_root(tmp_path: Path) -> None:
    """list_matches returns [] when root doesn't exist."""
    assert list_matches(tmp_path / "nope", "*", limit=10) == []
