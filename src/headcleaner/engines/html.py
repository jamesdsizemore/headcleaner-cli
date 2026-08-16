"""HTML adapter — .html and .htm files.

Strategy:
  1. Parse with BeautifulSoup (lxml backend for speed + robustness)
  2. Strip non-content tags (script, style, nav, header, footer, aside)
  3. Extract <title> as the document title
  4. markdownify the remaining tree with semantic ATX headings + GFM tables
"""
from __future__ import annotations

from pathlib import Path

from bs4 import BeautifulSoup
from markdownify import markdownify as md

from .base import Adapter, AdapterError


_STRIP_TAGS = {"script", "style", "nav", "header", "footer", "aside", "noscript", "iframe", "form"}


class HtmlAdapter(Adapter):
    name = "html"
    extensions = {".html", ".htm"}

    def __init__(self, encoding_hint: str = "utf-8") -> None:
        self.encoding_hint = encoding_hint

    def extract(self, source: Path, *, progress=None) -> dict:
        try:
            raw = source.read_text(encoding=self.encoding_hint, errors="replace")
        except OSError as e:
            raise AdapterError(f"cannot read {source}: {e}") from e

        soup = BeautifulSoup(raw, "lxml")

        # Title — prefer <h1> inside <main>/<article>, fall back to <title>
        title = self._extract_title(soup) or source.stem

        # Strip non-content tags
        for tag_name in _STRIP_TAGS:
            for tag in soup.find_all(tag_name):
                tag.decompose()

        body_md = md(str(soup), heading_style="ATX", bullets="-", tables=True)

        return {
            "title": title,
            "body_md": body_md.strip() + "\n",
            "metadata": {
                "engine": self.name,
                "source_format": source.suffix.lower(),
                "byte_size": source.stat().st_size,
            },
            "attachments": [],
        }

    @staticmethod
    def _extract_title(soup: BeautifulSoup) -> str | None:
        for sel in ("main h1", "article h1", "h1"):
            el = soup.select_one(sel)
            if el and el.get_text(strip=True):
                return el.get_text(strip=True)
        if soup.title and soup.title.string:
            return soup.title.string.strip()
        return None
