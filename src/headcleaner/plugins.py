"""Plugin discovery for headcleaner (v0.13.x — bonus item).

Third parties can ship custom adapters as separate packages without
forking headcleaner. Just register them in the `headcleaner_plugin` entry
point group::

    # In yourplugin/pyproject.toml
    [project.entry-points."headcleaner_plugin"]
    my_format = "yourplugin.adapters:MyFormatAdapter"

Then `headcleaner convert` will pick up `MyFormatAdapter` automatically
once `yourplugin` is installed in the same environment.

Discovery is lazy and safe — if `importlib.metadata` is unavailable or a
specific entry point fails to import, we log and skip. Use the CLI
subcommand `headcleaner agents` (planned) or the doctor check
`headcleaner doctor --verbose` (future) to see loaded plugins.
"""

from __future__ import annotations

import logging
import sys
from collections.abc import Iterable
from importlib import metadata as _metadata

from .engines.base import Adapter

_log = logging.getLogger(__name__)

PLUGIN_GROUP = "headcleaner_plugin"
EMBEDDING_PROVIDER_GROUP = "headcleaner_embedding_provider"


def _iter_entry_points(
    group: str = PLUGIN_GROUP,
) -> Iterable[tuple[str, _metadata.EntryPoint]]:
    """Yield (name, entry_point) pairs from an isolated plugin group.

    Tolerates environments where importlib.metadata is unavailable (very
    old Pythons) by returning an empty iterator.
    """
    try:
        eps = _metadata.entry_points()
    except Exception as e:
        _log.debug("entry_points() failed: %s", e)
        return ()

    # Python 3.10+ returns EntryPoints (selectable); older returns dict.
    if hasattr(eps, "select"):
        selected = eps.select(group=group)
    else:
        selected = eps.get(group, [])  # type: ignore[union-attr]
    return [(ep.name, ep) for ep in selected]


def _iter_embedding_entry_points() -> Iterable[tuple[str, _metadata.EntryPoint]]:
    """Yield embedding-provider plugins without mixing them with adapters."""
    return _iter_entry_points(EMBEDDING_PROVIDER_GROUP)


def load_plugins(into: list[Adapter]) -> list[tuple[str, str, str]]:
    """Discover third-party adapters via entry points and append them.

    Returns a list of (status, name, detail) tuples for logging / debugging:
        ("loaded", "my_format", "yourplugin.adapters.MyFormatAdapter")
        ("error", "broken_format", "ImportError: ...")

    Adapter objects are appended to `into`. Adapters that fail to load
    or fail the ABC check are skipped with a warning on stderr.
    """
    results: list[tuple[str, str, str]] = []
    for name, ep in _iter_entry_points():
        try:
            obj = ep.load()
        except Exception as e:
            results.append(("error", name, f"{type(e).__name__}: {e}"))
            print(
                f"  ✗ plugin {name!r} failed to load: {type(e).__name__}: {e}",
                file=sys.stderr,
            )
            continue

        # The entry point may be a class (instantiate it) or an instance.
        if isinstance(obj, type) and issubclass(obj, Adapter):
            try:
                instance = obj()
            except Exception as e:
                results.append(("error", name, f"instantiate failed: {e}"))
                print(
                    f"  ✗ plugin {name!r} class {obj!r} failed to instantiate: {e}",
                    file=sys.stderr,
                )
                continue
            into.append(instance)
            results.append(("loaded", name, f"{obj.__module__}.{obj.__name__}"))
        elif isinstance(obj, Adapter):
            into.append(obj)
            results.append(("loaded", name, f"{type(obj).__module__}.{type(obj).__name__}"))
        else:
            results.append(
                ("error", name, f"entry point is not an Adapter: {type(obj).__name__}"),
            )
            print(
                f"  ✗ plugin {name!r} is not an Adapter subclass/instance: {type(obj).__name__}",
                file=sys.stderr,
            )
    return results


def discover_once(into: list[Adapter] | None = None) -> list[tuple[str, str, str]]:
    """Idempotent plugin discovery. Default `into` is the global adapter list.

    Use this from `router.adapters()` so plugin adapters are picked up
    exactly once, the first time the router is queried.
    """
    if into is None:
        from . import router as _router

        into = _router._ADAPTERS  # type: ignore[attr-defined]
    return load_plugins(into)


def load_embedding_providers() -> tuple[dict[str, object], list[tuple[str, str, str]]]:
    """Load explicit embedding-provider plugins with a small structural contract.

    Plugins register under ``headcleaner_embedding_provider`` and must expose a
    provider instance (or zero-argument class) with ``name``, ``model_id``,
    ``dimension``, ``version``, and ``embed``. Broken plugins are recorded and
    skipped rather than changing the selected built-in provider.
    """
    providers: dict[str, object] = {}
    results: list[tuple[str, str, str]] = []
    required = ("name", "model_id", "dimension", "version", "embed")
    for entry_name, entry_point in _iter_embedding_entry_points():
        try:
            loaded = entry_point.load()
            provider = loaded() if isinstance(loaded, type) else loaded
        except Exception as exc:
            results.append(("error", entry_name, f"{type(exc).__name__}: {exc}"))
            continue

        if not all(hasattr(provider, attribute) for attribute in required) or not callable(
            getattr(provider, "embed", None)
        ):
            results.append(("error", entry_name, "entry point is not an EmbeddingProvider"))
            continue

        provider_name = str(provider.name)
        if not provider_name or provider_name in providers:
            results.append(
                ("error", entry_name, f"duplicate or empty provider name: {provider_name!r}")
            )
            continue
        providers[provider_name] = provider
        results.append(("loaded", entry_name, str(provider.model_id)))
    return providers, results
