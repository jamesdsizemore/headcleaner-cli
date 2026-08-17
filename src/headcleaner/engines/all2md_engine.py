"""all2md fallback adapter (v0.8.0).

``all2md`` (thomas-villani/all2md, MIT) is the broadest Python doc-to-MD
library: 50+ parsers including sourcecode, ipynb, latex, enex, chm, mhtml,
webarchive, and many more. We use it as a fallback adapter that handles
formats our 14 native adapters don't cover.

The adapter owns a single ``extensions`` set; users opt in via the router
by calling ``register_all2md_fallback()`` at startup.
"""

from __future__ import annotations

import logging
from pathlib import Path

from .base import Adapter, AdapterError

logger = logging.getLogger(__name__)


def all2md_available() -> bool:
    """True iff all2md is importable."""
    try:
        import all2md  # noqa: F401

        return True
    except ImportError:
        return False


# Format extensions that all2md handles which headcleaner does NOT have
# a native adapter for. (DOCX/XLSX/PPTX/EPUB/RTF/ODF/EML/MSG/PST are
# already handled natively — we don't double-cover them here.)
ALL2MD_EXTRA_EXTENSIONS: set[str] = {
    ".ipynb",  # Jupyter notebook
    ".latex",  # LaTeX
    ".tex",
    ".rst",  # reStructuredText
    ".asciidoc",
    ".adoc",
    ".textile",
    ".mediawiki",
    ".wiki",
    ".org",  # Emacs org-mode
    ".dokuwiki",
    ".bbcode",
    ".fb2",  # FictionBook
    ".chm",  # Compiled HTML Help
    ".mhtml",
    ".mht",  # MIME HTML
    ".webarchive",
    ".web",
    ".openapi",
    ".yaml",
    ".yml",  # all2md has YAML-as-content support
    ".toml",
    ".ini",
    ".enex",  # Evernote export
    ".json",
    ".xml",
    ".csv",  # all2md has CSV — our native csv.py is fine too; keep here for choice
    ".tsv",
    ".zip",  # all2md's archive mode (lists contents)
    ".py",  # source code
    ".js",
    ".ts",
    ".java",
    ".c",
    ".cpp",
    ".h",
    ".go",
    ".rs",
}


class All2mdAdapter(Adapter):
    """Adapter that wraps ``all2md.to_markdown()`` for extra formats.

    Used as a fallback for formats headcleaner does not have a native
    adapter for (Jupyter notebooks, LaTeX, reStructuredText, source code,
    Evernote exports, etc.).
    """

    name = "all2md"
    extensions = ALL2MD_EXTRA_EXTENSIONS

    def __init__(self) -> None:
        if not all2md_available():
            raise AdapterError("all2md is not installed. Install with: pip install all2md")

    def extract(self, source: Path, *, progress=None) -> dict:
        try:
            import all2md

            body_md = all2md.to_markdown(str(source))
        except Exception as e:
            raise AdapterError(f"all2md failed on {source}: {e}") from e

        # Report progress as a single tick (all2md doesn't expose page-level progress)
        if progress is not None:
            progress(1, 1)

        return {
            "title": source.stem,
            "body_md": body_md,
            "metadata": {
                "engine": self.name,
                "source_format": source.suffix.lower(),
                "backend": "all2md",
            },
            "attachments": [],
        }
