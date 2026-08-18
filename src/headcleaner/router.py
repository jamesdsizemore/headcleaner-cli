"""Extension → engine dispatch.

The router owns the canonical extension table. Adapters declare what they
support; the router maps an extension to an adapter instance.
"""

from __future__ import annotations

from pathlib import Path

from .engines.base import Adapter, AdapterError
from .engines.csv_json import CsvAdapter, JsonAdapter
from .engines.eml import EmlAdapter
from .engines.epub import EpubAdapter
from .engines.html import HtmlAdapter
from .engines.legacy_office import LegacyOfficeAdapter
from .engines.md import MdAdapter
from .engines.msg import MsgAdapter
from .engines.odf import OdfAdapter
from .engines.officecli import OfficeCLIAdapter
from .engines.pdf import PdfAdapter
from .engines.pst import PstAdapter
from .engines.rtf import RtfAdapter
from .engines.txt import TxtAdapter

# Order matters: the first adapter whose `supports()` returns True wins.
# Register the cheap/builtin adapters first; OfficeCLI requires a binary on PATH
# so its construction may raise — we tolerate that.
_ADAPTERS: list[Adapter] = [
    # Cheap / stdlib first
    TxtAdapter(),
    MdAdapter(),
    HtmlAdapter(),
    CsvAdapter(),
    JsonAdapter(),
    EmlAdapter(),
    RtfAdapter(),
    MsgAdapter(),
    EpubAdapter(),
    OdfAdapter(),
    PdfAdapter(),
    # Legacy Office error-path
    LegacyOfficeAdapter(),
    # PST is best-effort: raises AdapterError on missing binary
    PstAdapter(),
]

# The Office adapter is optional. Register it only when office_oxide or
# OfficeCLI is available; otherwise all unrelated commands remain usable.
try:
    _ADAPTERS.append(OfficeCLIAdapter())
except AdapterError:
    pass

# v0.9.0: zsv SIMD CSV adapter (liquidaty/zsv, MIT). Inserted at the
# CsvAdapter position so that when the zsv binary is on PATH, ZsvAdapter
# replaces CsvAdapter for .csv/.tsv. When zsv is not installed, ZsvAdapter's
# extensions are empty (it claims nothing) and the entry is silently dropped.
try:
    from .engines.zsv import ZsvAdapter as _ZsvAdapter

    _zsv_instance = _ZsvAdapter()
    if _zsv_instance.extensions:
        # Find the CsvAdapter in _ADAPTERS and replace it in place.
        for _i, _a in enumerate(_ADAPTERS):
            if _a.name == "csv":
                _ADAPTERS[_i] = _zsv_instance
                break
        else:
            # CsvAdapter not present (unusual); append.
            _ADAPTERS.append(_zsv_instance)
except Exception:
    pass  # zsv not installed or failed to construct; skip silently

# Opt-in all2md fallback adapter (formats headcleaner does not have a
# native adapter for: jupyter, latex, rst, sourcecode, enex, chm, etc.).
# Tolerated if all2md is not installed (registers nothing).
try:
    from .engines.all2md_engine import All2mdAdapter as _All2mdAdapter

    _ADAPTERS.append(_All2mdAdapter())
except Exception:
    pass  # all2md not installed or failed to construct; skip silently

_plugins_loaded = False


def adapters() -> list[Adapter]:
    """Return the registered adapters (read-only snapshot).

    On first call, also discovers any third-party adapters registered
    via the `headcleaner_plugin` entry point group (see plugins.py).
    Discovery is idempotent — subsequent calls return the same list.
    """
    global _plugins_loaded
    if not _plugins_loaded:
        from .plugins import discover_once

        discover_once(_ADAPTERS)
        _plugins_loaded = True
    return list(_ADAPTERS)


def get_adapter(path: Path) -> Adapter | None:
    """Return the adapter that handles `path`, or None if no engine supports it."""
    for adapter in adapters():
        try:
            if adapter.supports(path):
                return adapter
        except AdapterError:
            # OfficeCLI binary missing — skip silently; other engines still try
            continue
    return None


def registered_extensions() -> set[str]:
    """All extensions any registered adapter can handle (for the CLI help text)."""
    out: set[str] = set()
    for a in adapters():
        out.update(a.extensions)
    return out
