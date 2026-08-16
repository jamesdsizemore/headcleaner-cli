"""Tests for normalize.py — CanonicalDoc and frontmatter builders."""
from __future__ import annotations

from pathlib import Path

from headcleaner.normalize import normalize, default_generated, default_stale_after, CanonicalDoc
from headcleaner.walk import SourceFile


def _make_source(path: Path) -> SourceFile:
    return SourceFile(path=path, relpath=Path(path.name), size_bytes=path.stat().st_size)


def _make_doc(tmp_path: Path, name: str, body: str = "hello"):
    """Helper: build a CanonicalDoc whose source lives at tmp_path/name."""
    f = tmp_path / name
    f.write_text(body, encoding="utf-8")
    sf = _make_source(f)
    return normalize(sf, {"title": name, "body_md": body}, engine="txt")


def test_normalize_basic(tmp_path: Path) -> None:
    doc = _make_doc(tmp_path, "x.txt", "hello")
    assert doc.title == "x.txt"
    assert doc.source_sha256 and len(doc.source_sha256) == 64
    assert doc.source_uri.startswith("file:///")
    assert doc.engine == "txt"
    assert doc.source_format == ".txt"


def test_canonical_doc_okf_frontmatter_required_keys(tmp_path: Path) -> None:
    doc = _make_doc(tmp_path, "x.txt", "hi")
    fm = doc.to_okf_frontmatter()
    # OKF v0.2 §4.1: `type` is the ONLY always-required key
    assert "type" in fm and isinstance(fm["type"], str) and fm["type"]
    # We fill in the recommended + trust family automatically
    assert "title" in fm
    assert "description" in fm
    assert "resource" in fm and fm["resource"].startswith("file://")
    assert isinstance(fm["tags"], list)
    # v0.2 trust family
    assert fm["status"] == "unverified"
    assert fm["verified"] == "human:pending"
    assert isinstance(fm["sources"], list) and fm["sources"]
    assert fm["sources"][0]["uri"].startswith("file://")
    assert len(fm["sources"][0]["sha256"]) == 64
    assert fm["generated"].startswith("human:")


def test_canonical_doc_md_frontmatter(tmp_path: Path) -> None:
    doc = _make_doc(tmp_path, "x.txt", "hi")
    fm = doc.to_md_frontmatter()
    for key in ("title", "source", "format", "engine", "sha256", "generated_at"):
        assert key in fm, f"missing MD frontmatter key: {key}"
    assert fm["engine"] == "txt"


def test_default_generated_uses_env_user() -> None:
    import os
    os.environ["USER"] = "tester"
    g = default_generated()
    assert g.startswith("human:tester")


def test_default_stale_after_is_future_date() -> None:
    from datetime import datetime, timezone
    s = default_stale_after()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    assert s > today  # strictly after today
