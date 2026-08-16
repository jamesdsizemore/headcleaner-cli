"""Legacy Office adapter — `.doc`, `.xls`, `.ppt` (pre-2007 binary formats).

These formats are NOT supported by OfficeCLI. This adapter exists to
emit a clear, actionable error message instead of a generic "no adapter"
skip — telling users exactly how to convert the file.

Two recovery paths:
  1. `libreoffice --convert-to docx old.doc` then run headcleaner on
     the resulting .docx
  2. Use dedicated parsers (antiword for .doc, xlrd for .xls) — not
     bundled by headcleaner to avoid pulling heavy C deps
"""
from __future__ import annotations

from pathlib import Path

from .base import Adapter, AdapterError


class LegacyOfficeAdapter(Adapter):
    name = "legacy_office"
    extensions = {".doc", ".xls", ".ppt"}

    def extract(self, source: Path) -> dict:
        ext = source.suffix.lower()
        converter = {
            ".doc": "libreoffice --convert-to docx",
            ".xls": "libreoffice --convert-to xlsx",
            ".ppt": "libreoffice --convert-to pptx",
        }.get(ext, "libreoffice --convert-to (modern format)")

        raise AdapterError(
            f"Legacy Office format {ext} is not supported by headcleaner "
            f"(OfficeCLI only handles .docx/.xlsx/.pptx). Convert first with:\n"
            f"  {converter} {source.name}\n"
            f"Then run headcleaner on the converted file. "
            f"Tracked in ENHANCEMENTS.md #13."
        )
