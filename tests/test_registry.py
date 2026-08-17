"""Tests for v0.13.0: cross-bundle search + @slug registry."""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from headcleaner import registry as _registry
from headcleaner.mcp import (
    BundleRegistry,
    okf_search,
    okf_registry_list,
    okf_registry_add,
    okf_registry_remove,
    okf_registry_resolve,
)


# ---------------------------------------------------------------------------
# Registry file helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def reg_path(tmp_path: Path) -> Path:
    return tmp_path / "registry.toml"


# ---------------------------------------------------------------------------
# Registry file tests
# ---------------------------------------------------------------------------


class TestRegistryFile:
    def test_empty_when_missing(self, tmp_path: Path):
        # Use a path that doesn't exist
        nonexistent = tmp_path / "nope.toml"
        assert _registry.load_registry(path=nonexistent) == {}

    def test_add_and_load_roundtrip(self, reg_path: Path):
        _registry.add_slug("docs", "/some/path", path=reg_path)
        loaded = _registry.load_registry(path=reg_path)
        assert "docs" in loaded
        assert loaded["docs"] == Path("/some/path").resolve()

    def test_add_validates_slug(self, reg_path: Path):
        with pytest.raises(ValueError, match="invalid slug"):
            _registry.add_slug("", "/x", path=reg_path)
        with pytest.raises(ValueError, match="invalid slug"):
            _registry.add_slug("@bad", "/x", path=reg_path)
        with pytest.raises(ValueError, match="invalid slug"):
            _registry.add_slug("has space", "/x", path=reg_path)

    def test_remove_is_noop_when_absent(self, reg_path: Path):
        mapping = _registry.remove_slug("nope", path=reg_path)
        assert mapping == {}

    def test_resolve_with_known_slug(self, reg_path: Path):
        _registry.add_slug("docs", "/some/path", path=reg_path)
        slug, bundle_path = _registry.resolve_slug("@docs/readme", path=reg_path)
        assert slug == "docs"
        assert bundle_path == Path("/some/path").resolve()

    def test_resolve_without_at_prefix(self, reg_path: Path):
        slug, bundle_path = _registry.resolve_slug("plain text", path=reg_path)
        assert slug is None
        assert bundle_path is None

    def test_resolve_unknown_slug(self, reg_path: Path):
        slug, bundle_path = _registry.resolve_slug("@unknown/x", path=reg_path)
        assert slug == "unknown"
        assert bundle_path is None


# ---------------------------------------------------------------------------
# Cross-bundle search tests
# ---------------------------------------------------------------------------


def _write_bundle(path: Path, name: str, concepts: list[tuple[str, str]]) -> None:
    """Write a minimal OKF bundle: index.md + N concept files."""
    path.mkdir(parents=True, exist_ok=True)
    for slug, body in concepts:
        (path / f"{slug}.md").write_text(
            f"---\ntype: Document\ntitle: {slug}\n---\n\n# {slug}\n\n{body}\n",
            encoding="utf-8",
        )


class TestCrossBundleSearch:
    def test_single_bundle_default(self, tmp_path: Path):
        b1 = tmp_path / "b1"
        _write_bundle(b1, "b1", [("alpha", "first"), ("beta", "second")])
        reg = BundleRegistry()
        reg.add("b1", b1)
        hits = okf_search(reg, "first", bundle_name=None, limit=20)
        assert len(hits) == 1
        assert hits[0]["title"] == "alpha"
        assert "bundle" not in hits[0]

    def test_all_bundles_search(self, tmp_path: Path):
        b1 = tmp_path / "b1"
        b2 = tmp_path / "b2"
        _write_bundle(b1, "b1", [("alpha", "shared term here")])
        _write_bundle(b2, "b2", [("beta", "shared term there")])
        reg = BundleRegistry()
        reg.add("b1", b1)
        reg.add("b2", b2)
        hits = okf_search(reg, "shared", bundle_name=None, limit=20, all_bundles=True)
        assert len(hits) == 2
        bundle_names = {h["bundle"] for h in hits}
        assert bundle_names == {"b1", "b2"}

    def test_all_bundles_tags_every_hit(self, tmp_path: Path):
        b1 = tmp_path / "b1"
        b2 = tmp_path / "b2"
        _write_bundle(b1, "b1", [("alpha", "needle")])
        _write_bundle(b2, "b2", [("beta", "no hit")])
        reg = BundleRegistry()
        reg.add("b1", b1)
        reg.add("b2", b2)
        hits = okf_search(reg, "needle", bundle_name=None, limit=20, all_bundles=True)
        assert len(hits) == 1
        assert hits[0]["bundle"] == "b1"

    def test_no_bundles_returns_empty(self):
        reg = BundleRegistry()
        hits = okf_search(reg, "anything", bundle_name=None, limit=20)
        assert hits == []


# ---------------------------------------------------------------------------
# Registry MCP tool tests
# ---------------------------------------------------------------------------


class TestRegistryTools:
    def test_list_initially_empty(self, reg_path, monkeypatch):
        monkeypatch.setattr(_registry, "registry_path", lambda: reg_path)
        assert okf_registry_list() == []

    def test_add_then_list(self, reg_path, monkeypatch):
        monkeypatch.setattr(_registry, "registry_path", lambda: reg_path)
        result = okf_registry_add(slug="docs", bundle_path="/some/where")
        assert result["ok"] is True
        assert result["slug"] == "docs"
        items = okf_registry_list()
        assert len(items) == 1
        assert items[0]["slug"] == "docs"

    def test_remove(self, reg_path, monkeypatch):
        monkeypatch.setattr(_registry, "registry_path", lambda: reg_path)
        okf_registry_add(slug="docs", bundle_path="/some/where")
        result = okf_registry_remove(slug="docs")
        assert result["ok"] is True
        assert okf_registry_list() == []

    def test_resolve_known_slug(self, reg_path, monkeypatch):
        monkeypatch.setattr(_registry, "registry_path", lambda: reg_path)
        okf_registry_add(slug="docs", bundle_path="/some/where")
        result = okf_registry_resolve("@docs/foo")
        assert result["ok"] is True
        assert result["slug"] == "docs"
        assert result["concept"] == "foo"

    def test_resolve_unknown_slug(self, reg_path, monkeypatch):
        monkeypatch.setattr(_registry, "registry_path", lambda: reg_path)
        result = okf_registry_resolve("@unknown/x")
        assert result["ok"] is False
        assert "unknown" in result["error"]