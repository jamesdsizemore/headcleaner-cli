"""Tests for the plugin protocol (v0.13.x bonus)."""
from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from headcleaner.engines.base import Adapter
from headcleaner.plugins import (
    PLUGIN_GROUP,
    _iter_entry_points,
    discover_once,
    load_plugins,
)


class _FakeAdapter(Adapter):
    name = "fake-plugin-adapter"
    extensions: ClassVar[tuple[str, ...]] = (".fakeplg",)

    def supports(self, source: Path) -> bool:  # type: ignore[override]
        return source.suffix.lower() in self.extensions

    def extract(self, source: Path):  # type: ignore[override]
        return {
            "title": source.stem,
            "body_md": f"fake body for {source.name}",
            "metadata": {},
            "attachments": [],
        }


class _BrokenAdapter:
    """Returned by an entry point — but it's not an Adapter subclass/instance."""
    pass


def _make_ep(name: str, value, group: str = PLUGIN_GROUP):
    """Construct an EntryPoint with the given name → target value."""
    from importlib.metadata import EntryPoint

    return EntryPoint(name=name, group=group, value=value)


def test_iter_entry_points_safe_when_metadata_unavailable(monkeypatch):
    """If entry_points() raises, _iter_entry_points returns empty (not error)."""
    import headcleaner.plugins as _p

    def boom():
        raise RuntimeError("no metadata")

    monkeypatch.setattr(_p._metadata, "entry_points", boom)
    assert list(_iter_entry_points()) == []


def test_load_plugins_class_adapter(monkeypatch):
    """A class-based entry point is instantiated and appended."""
    ep = _make_ep(
        "fake_via_class",
        f"{__name__}:_FakeAdapter",
    )

    # Patch _iter_entry_points to yield our fake ep
    import headcleaner.plugins as _p

    monkeypatch.setattr(_p, "_iter_entry_points", lambda: [(ep.name, ep)])

    target: list[Adapter] = []
    results = load_plugins(target)
    assert any(r[0] == "loaded" and r[1] == "fake_via_class" for r in results)
    assert any(isinstance(a, _FakeAdapter) for a in target)


def test_load_plugins_rejects_non_adapter(monkeypatch):
    ep = _make_ep("broken", f"{__name__}:_BrokenAdapter")
    import headcleaner.plugins as _p

    monkeypatch.setattr(_p, "_iter_entry_points", lambda: [(ep.name, ep)])

    target: list[Adapter] = []
    results = load_plugins(target)
    assert any(r[0] == "error" for r in results)
    assert target == []  # nothing appended


def test_load_plugins_tolerates_load_failure(monkeypatch):
    ep = _make_ep("bad-target", "nonexistent.module:Missing")
    import headcleaner.plugins as _p

    monkeypatch.setattr(_p, "_iter_entry_points", lambda: [(ep.name, ep)])

    target: list[Adapter] = []
    results = load_plugins(target)
    assert any(r[0] == "error" for r in results)
    assert target == []


def test_discover_once_into_explicit_list():
    """discover_once with an explicit list appends there (no global state)."""
    target: list[Adapter] = []
    results = discover_once(target)
    # With no plugins installed in this env, results should be empty or
    # only contain valid entries.
    for status, _, _ in results:
        assert status in {"loaded", "error"}


def test_router_adapters_includes_builtins(monkeypatch):
    """Built-in adapters are still returned even if plugin discovery is empty."""
    from headcleaner import router as _router

    # Reset the discovery flag so it runs fresh in this test
    monkeypatch.setattr(_router, "_plugins_loaded", False)
    monkeypatch.setattr("headcleaner.plugins._iter_entry_points", lambda: [])
    adapters = _router.adapters()
    # Should still have the 14 built-in adapters
    assert len(adapters) >= 14
    assert any(a.name == "officecli" for a in adapters)


def test_router_adapters_idempotent(monkeypatch):
    """Repeated calls to router.adapters() return the same length list."""
    from headcleaner import router as _router

    monkeypatch.setattr(_router, "_plugins_loaded", False)
    monkeypatch.setattr("headcleaner.plugins._iter_entry_points", lambda: [])
    a1 = _router.adapters()
    a2 = _router.adapters()
    assert len(a1) == len(a2)


def test_get_adapter_discovers_and_routes_to_plugin(monkeypatch):
    """The conversion routing path triggers discovery, not just adapters()."""
    from headcleaner import plugins as _plugins
    from headcleaner import router as _router

    ep = _make_ep("fake_via_router", f"{__name__}:_FakeAdapter")
    monkeypatch.setattr(_router, "_ADAPTERS", list(_router._ADAPTERS))
    monkeypatch.setattr(_router, "_plugins_loaded", False)
    monkeypatch.setattr(_plugins, "_iter_entry_points", lambda: [(ep.name, ep)])

    adapter = _router.get_adapter(Path("document.fakeplg"))

    assert isinstance(adapter, _FakeAdapter)
    assert ".fakeplg" in _router.registered_extensions()


def test_iter_entry_points_returns_named_pairs(monkeypatch):
    """Real importlib entry-point objects are normalized to (name, object)."""
    import headcleaner.plugins as _p

    ep = _make_ep("fake_pair", f"{__name__}:_FakeAdapter")

    class _EntryPoints(list):
        def select(self, *, group):
            return self if group == PLUGIN_GROUP else []

    monkeypatch.setattr(_p._metadata, "entry_points", lambda: _EntryPoints([ep]))

    assert list(_iter_entry_points()) == [("fake_pair", ep)]
