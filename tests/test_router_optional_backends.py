"""Regression test for optional Office backend router registration."""

from __future__ import annotations

import importlib

from headcleaner.engines.base import AdapterError


def test_router_starts_without_an_office_backend(monkeypatch) -> None:
    import headcleaner.engines.officecli as office_module
    import headcleaner.router as router_module

    original_init = office_module.OfficeCLIAdapter.__init__

    def unavailable(self, *args, **kwargs) -> None:
        raise AdapterError("no Office backend")

    monkeypatch.setattr(office_module.OfficeCLIAdapter, "__init__", unavailable)
    try:
        router = importlib.reload(router_module)
        assert {".txt", ".pdf", ".doc"}.issubset(router.registered_extensions())
        assert ".docx" not in router.registered_extensions()
    finally:
        monkeypatch.setattr(office_module.OfficeCLIAdapter, "__init__", original_init)
        importlib.reload(router_module)
