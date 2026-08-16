"""Adapter abstract base class.

Every engine (OfficeCLI, PDF, HTML, etc.) implements `Adapter`. The contract is
deliberately small: convert a file to a normalized intermediate dict that
`normalize.py` turns into a `CanonicalDoc`.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import ClassVar


class AdapterError(Exception):
    """Raised when an engine cannot convert the given file."""


class Adapter(ABC):
    """Base class for all engines."""

    #: Human-readable name shown in the manifest and logs.
    name: ClassVar[str] = ""

    #: File extensions this adapter handles, lowercased and including the dot.
    #: e.g. {".docx", ".doc"} or {".html", ".htm"}.
    extensions: ClassVar[set[str]] = set()

    @abstractmethod
    def extract(self, source: Path) -> dict:
        """Return a normalized dict representing the document content.

        The dict shape is:

            {
                "title": str | None,
                "body_md": str,            # canonical Markdown body
                "metadata": dict,          # engine-specific extras (optional)
                "attachments": list[dict], # e.g. images: [{"kind": "image", ...}]
            }

        `body_md` MUST be valid Markdown. `title` is best-effort; the
        emitter falls back to the filename stem if None.
        """
        raise NotImplementedError

    def supports(self, path: Path) -> bool:
        """True if this adapter handles the given file path."""
        return path.suffix.lower() in self.extensions
