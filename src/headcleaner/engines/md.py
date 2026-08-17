"""Markdown adapter — .md and .markdown files.

Pass-through with frontmatter injection: if the file has frontmatter,
preserve it and add any missing OKF trust family keys. If it doesn't,
generate a complete OKF frontmatter block from the file's first heading
(or the filename stem as fallback).
"""

from __future__ import annotations

import re
from pathlib import Path

from .base import Adapter


class MdAdapter(Adapter):
    name = "md"
    extensions = {".md", ".markdown"}

    def extract(self, source: Path, *, progress=None) -> dict:
        text = source.read_text(encoding="utf-8", errors="replace")
        title = self._extract_title(text) or source.stem
        body_md = self._clean_body(text)

        return {
            "title": title,
            "body_md": body_md,
            "metadata": {
                "engine": self.name,
                "source_format": source.suffix.lower(),
                "byte_size": source.stat().st_size,
            },
            "attachments": [],
        }

    @staticmethod
    def _extract_title(text: str) -> str | None:
        """Return the first H1's text, or the first ATX heading."""
        # Skip frontmatter
        body = text
        m = re.match(r"\A---\s*\n(.*?)\n---\s*\n", body, re.DOTALL)
        if m:
            body = body[m.end() :]
        for line in body.splitlines():
            m = re.match(r"^#\s+(.+?)\s*$", line)
            if m:
                return m.group(1).strip()
        return None

    @staticmethod
    def _clean_body(text: str) -> str:
        """Strip a leading frontmatter block (normalize will re-emit OKF)."""
        m = re.match(r"\A---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
        if m:
            return text[m.end() :].lstrip("\n")
        return text
