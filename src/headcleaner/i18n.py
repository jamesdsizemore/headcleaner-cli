"""Runtime gettext support for HeadCleaner.

Catalogs are compiled during development and shipped with the package, so end
users need neither gettext command-line tools nor Babel at runtime. Locale
selection is process-local and deterministic: ``--lang`` wins, followed by
``HEADCLEANER_LANG`` and finally English.
"""

from __future__ import annotations

import gettext
import os
from contextvars import ContextVar
from pathlib import Path

DOMAIN = "headcleaner"
LOCALE_DIR = Path(__file__).with_name("locales")
SUPPORTED_LOCALES = ("en", "es", "zh_CN")

_locale: ContextVar[str] = ContextVar("headcleaner_locale", default="en")


def normalize_locale(value: str | None) -> str:
    """Normalize user-friendly locale spellings to shipped gettext catalog names."""
    candidate = (value or os.environ.get("HEADCLEANER_LANG") or "en").strip()
    candidate = candidate.replace("-", "_").split(".", 1)[0]
    aliases = {"zh": "zh_CN", "zh_cn": "zh_CN", "en_us": "en", "en_gb": "en"}
    candidate = aliases.get(candidate.lower(), candidate.lower())
    if candidate not in SUPPORTED_LOCALES:
        return "en"
    return candidate


def set_locale(value: str | None) -> str:
    """Activate a shipped locale for the current process context and return it."""
    locale_name = normalize_locale(value)
    _locale.set(locale_name)
    return locale_name


def get_locale() -> str:
    """Return the normalized active locale."""
    return _locale.get()


def translation(locale_name: str | None = None) -> gettext.NullTranslations:
    """Load a shipped catalog, falling back safely to the English source strings."""
    language = normalize_locale(locale_name or get_locale())
    return gettext.translation(DOMAIN, localedir=LOCALE_DIR, languages=[language], fallback=True)


def tr(message: str) -> str:
    """Translate a stable message identifier under the active locale."""
    return translation().gettext(message)
