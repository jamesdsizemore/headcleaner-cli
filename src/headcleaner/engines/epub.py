"""EPUB adapter (Eng #7) — Electronic Publication books.

An EPUB is a zip of XHTML files. We use `ebooklib` to enumerate spine
items and concatenate their text content with `---` separators per
chapter.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

from .base import Adapter

try:
    import ebooklib
    from ebooklib import epub

    HAS_EBOOKLIB = True
except ImportError:  # pragma: no cover
    HAS_EBOOKLIB = False


def _html_to_text(html: str) -> str:
    """Tiny HTML-to-text fallback using BeautifulSoup."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    parts: list[str] = []
    for el in soup.find_all(["h1", "h2", "h3", "h4", "p", "li"]):
        text = el.get_text(" ", strip=True)
        if not text:
            continue
        tag = el.name
        if tag == "h1":
            parts.append(f"# {text}")
        elif tag == "h2":
            parts.append(f"## {text}")
        elif tag == "h3":
            parts.append(f"### {text}")
        elif tag == "h4":
            parts.append(f"#### {text}")
        elif tag == "li":
            parts.append(f"- {text}")
        else:
            parts.append(text)
    return "\n\n".join(parts)


class EpubAdapter(Adapter):
    name = "epub"
    extensions = (".epub",)

    def extract(self, source: Path) -> "Extracted":  # noqa: F821
        if not HAS_EBOOKLIB:
            return self._extract_fallback(source)

        book = epub.read_epub(str(source))
        title = ""
        try:
            md = book.get_metadata("DC", "title")
            if md and md[0]:
                title = str(md[0][1])
        except Exception:
            pass
        if not title:
            title = source.stem

        author = ""
        try:
            md = book.get_metadata("DC", "creator")
            if md and md[0]:
                author = str(md[0][1])
        except Exception:
            pass

        chapters: list[str] = []
        for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
            try:
                content = item.get_content().decode("utf-8", errors="replace")
            except Exception:
                continue
            chapter_md = _html_to_text(content)
            if chapter_md:
                chapters.append(f"## {item.get_name()}\n\n{chapter_md}")

        return {
            "title": title,
            "body_md": "\n\n---\n\n".join(chapters) if chapters else "(empty book)",
            "metadata": {
                "format": "epub",
                "author": author,
                "chapter_count": len(chapters),
            },
        }

    @staticmethod
    def _extract_fallback(source: Path) -> "Extracted":  # noqa: F821
        # No ebooklib: read first text-bearing HTML inside the zip.
        chapters: list[str] = []
        try:
            with zipfile.ZipFile(source) as zf:
                for name in sorted(zf.namelist()):
                    if not name.endswith((".xhtml", ".html", ".htm")):
                        continue
                    if "OEBPS" not in name and "content" not in name and "/" not in name:
                        continue
                    with zf.open(name) as f:
                        chapters.append(_html_to_text(f.read().decode("utf-8", errors="replace")))
        except Exception as e:
            return {
                "title": source.stem,
                "body_md": f"(could not parse epub: {e})",
                "metadata": {"format": "epub", "error": str(e)},
            }
        return {
            "title": source.stem,
            "body_md": "\n\n---\n\n".join(c for c in chapters if c),
            "metadata": {"format": "epub", "fallback": True},
        }
