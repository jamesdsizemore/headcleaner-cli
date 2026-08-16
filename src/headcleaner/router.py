"""Extension → engine dispatch.

The router owns the canonical extension table. Adapters declare what they
support; the router maps an extension to an adapter instance.
"""
from __future__ import annotations

from pathlib import Path

from .engines.base import Adapter, AdapterError
from .engines.csv_json import CsvAdapter, JsonAdapter
from .engines.eml import EmlAdapter
from .engines.html import HtmlAdapter
from .engines.legacy_office import LegacyOfficeAdapter
from .engines.md import MdAdapter
from .engines.officecli import OfficeCLIAdapter
from .engines.pdf import PdfAdapter
from .engines.pst import PstAdapter
from .engines.txt import TxtAdapter


# Order matters: the first adapter whose `supports()` returns True wins.
# Register the cheap/builtin adapters first; OfficeCLI requires a binary on PATH
# so its construction may raise — we tolerate that.
_ADAPTERS: list[Adapter] = [
    TxtAdapter(),
    MdAdapter(),
    HtmlAdapter(),
    CsvAdapter(),
    PdfAdapter(),
    JsonAdapter(),
    EmlAdapter(),
    PstAdapter(),  # best-effort; raises AdapterError if libpff-python missing
    LegacyOfficeAdapter(),  # raises AdapterError with actionable hint
    OfficeCLIAdapter(),
]


def adapters() -> list[Adapter]:
    """Return the registered adapters (read-only snapshot)."""
    return list(_ADAPTERS)


def get_adapter(path: Path) -> Adapter | None:
    """Return the adapter that handles `path`, or None if no engine supports it."""
    for adapter in _ADAPTERS:
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
    for a in _ADAPTERS:
        out.update(a.extensions)
    return out
