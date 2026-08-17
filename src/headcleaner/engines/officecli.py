"""Office adapter — DOCX, XLSX, PPTX (v0.8.0 office_oxide primary).

Backends, tried in order:

1. **`office_oxide`** (preferred) — pure-Python (PyO3) bindings over a Rust
   core. Sub-millisecond parse for typical files. ~100× faster than
   python-docx/openpyxl/python-pptx. 100% pass rate on valid Office files
   per the upstream corpus. Apache-2.0/MIT.

2. **`OfficeCLI` binary** (fallback) — npm-installed `@officecli/officecli`.
   Used if office_oxide is not installed (graceful degradation).

The (legacy) .doc/.xls/.ppt trio are explicitly NOT supported here; see
FORMAT_MATRIX.md for the legacy fallback path.

`from .base import Adapter, AdapterError` — the public adapter name remains
`officecli` for the router/router registry, so no other module needs to
change. We just prefer office_oxide internally.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path

from bs4 import BeautifulSoup
from markdownify import markdownify as md

from .base import Adapter, AdapterError

logger = logging.getLogger(__name__)


def office_oxide_available() -> bool:
    """True iff `office_oxide` Python bindings import successfully."""
    try:
        import office_oxide  # noqa: F401

        return True
    except ImportError:
        return False


class OfficeCLIAdapter(Adapter):
    name = "officecli"
    extensions = {".docx", ".xlsx", ".pptx"}

    def __init__(
        self, binary: str = "officecli", timeout: int = 60, prefer_oxide: bool = True
    ) -> None:
        self.binary = binary
        self.timeout = timeout
        # OfficeCLI binary resolution (kept for fallback path)
        self._officecli_resolved: str | None = None
        self._officecli_use_shell = False
        if shutil.which(binary):
            resolved = shutil.which(binary)  # type: ignore[assignment]
            self._officecli_resolved = resolved
            self._officecli_use_shell = (
                resolved.lower().endswith((".cmd", ".bat")) if resolved else False
            )
        # office_oxide preference
        self._prefer_oxide = prefer_oxide and office_oxide_available()
        if not self._prefer_oxide and not self._officecli_resolved:
            raise AdapterError(
                "No Office backend available. Install one of:\n"
                "  pip install office-oxide      (recommended, pure-Python, 100x faster)\n"
                "  npm install -g @officecli/officecli  (fallback binary)"
            )

    @property
    def backend(self) -> str:
        """Return the name of the backend that will be used for extraction."""
        return "office_oxide" if self._prefer_oxide else "officecli"

    def extract(self, source: Path, *, progress=None) -> dict:
        if self._prefer_oxide:
            try:
                return self._extract_with_oxide(source, progress=progress)
            except Exception as e:
                # Graceful degradation: if office_oxide fails, fall back to OfficeCLI.
                logger.warning(
                    "office_oxide failed on %s (%s); falling back to OfficeCLI", source, e
                )
                if self._officecli_resolved:
                    return self._extract_with_officecli(source)
                raise AdapterError(f"office_oxide failed on {source}: {e}") from e
        return self._extract_with_officecli(source)

    # ---- office_oxide backend (preferred) -----------------------------------

    def _extract_with_oxide(self, source: Path, *, progress=None) -> dict:
        import office_oxide

        # office_oxide returns format-appropriate markdown directly.
        # 0.8ms mean DOCX, 5.0ms mean XLSX, 0.7ms mean PPTX per upstream bench.
        body_md = office_oxide.to_markdown(str(source))
        # Also pull the title from the IR if available
        title = source.stem
        try:
            with office_oxide.Document.open(str(source)) as doc:
                # Use first heading-ish text as title; fallback to filename.
                plain = doc.plain_text() if hasattr(doc, "plain_text") else ""
                if plain:
                    first_line = plain.splitlines()[0].strip() if plain.strip() else ""
                    if first_line and len(first_line) < 200:
                        title = first_line
        except Exception:
            pass

        # Report progress as a single tick (office_oxide doesn't expose page-level progress)
        if progress is not None:
            progress(1, 1)

        return {
            "title": title,
            "body_md": body_md,
            "metadata": {
                "engine": self.name,
                "source_format": source.suffix.lower(),
                "backend": "office_oxide",
            },
            "attachments": [],
        }

    # ---- OfficeCLI binary backend (fallback) --------------------------------

    def _extract_with_officecli(self, source: Path) -> dict:
        try:
            html = self._run_officecli(source)
        except subprocess.TimeoutExpired as e:
            raise AdapterError(f"officecli timed out after {self.timeout}s on {source}") from e
        except subprocess.CalledProcessError as e:
            raise AdapterError(f"officecli failed on {source}: {e.stderr or e}") from e

        cleaned = self._clean_html(html)
        body_md = md(cleaned, heading_style="ATX", bullets="-")
        title = self._extract_title(cleaned) or source.stem

        lines = body_md.splitlines()
        while lines and lines[0].strip() == source.name:
            lines.pop(0)
        while lines and not lines[0].strip():
            lines.pop(0)
        body_md = "\n".join(lines) + "\n" if lines else ""

        return {
            "title": title,
            "body_md": body_md,
            "metadata": {
                "engine": self.name,
                "source_format": source.suffix.lower(),
                "backend": "officecli",
            },
            "attachments": [],
        }

    def _run_officecli(self, source: Path) -> str:
        assert self._officecli_resolved is not None
        proc = subprocess.run(
            [self._officecli_resolved, "view", str(source), "html"],
            capture_output=True,
            text=True,
            timeout=self.timeout,
            check=True,
            shell=self._officecli_use_shell,
        )
        return proc.stdout

    @staticmethod
    def _clean_html(html: str) -> str:
        import re

        soup = BeautifulSoup(html, "lxml")
        for tag in soup.find_all(["style", "script"]):
            tag.decompose()
        for span in soup.find_all("span", class_=re.compile(r"^(wb|we)$")):
            span.decompose()
        for cls in ("page-wrapper", "page", "page-body", "doc-header", "doc-footer"):
            for el in soup.find_all(class_=cls):
                el.unwrap()
        return str(soup)

    @staticmethod
    def _extract_title(soup_html: str) -> str | None:
        soup = BeautifulSoup(soup_html, "lxml")
        h1 = soup.find("h1")
        if h1 and h1.get_text(strip=True):
            return h1.get_text(strip=True)
        if soup.title and soup.title.string:
            return soup.title.string.strip()
        return None
