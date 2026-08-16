"""RTF adapter (Eng #8) — Rich Text Format files.

Uses `striprtf` for robust RTF stripping. Falls back to a tiny inline
parser if the dep is missing.
"""
from __future__ import annotations

from pathlib import Path

from .base import Adapter

try:
    from striprtf import rtf_to_text as _strip_rtf
except ImportError:  # pragma: no cover
    _strip_rtf = None


class RtfAdapter(Adapter):
    name = "rtf"
    extensions = (".rtf",)

    def extract(self, source: Path) -> Extracted:
        raw = source.read_bytes()
        # RTF is typically ASCII or Latin-1; chardet would be overkill.
        text = raw.decode("latin-1", errors="replace")
        if _strip_rtf is None:
            # Tiny inline fallback: drop everything in {...} groups
            import re
            body = re.sub(r"\{\\?[^{}]*\}", " ", text)
            body = re.sub(r"\\'[0-9a-fA-F]{2}", " ", body)
            body = re.sub(r"\\[a-z]+\d* ?", " ", body)
            body = re.sub(r"[{}]", " ", body)
            body = re.sub(r"\s+", " ", body).strip()
        else:
            body = _strip_rtf(text).strip()
        return {
            "title": source.stem,
            "body_md": body,
            "metadata": {"format": "rtf", "char_count": len(body)},
        }