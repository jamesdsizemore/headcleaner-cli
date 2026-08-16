"""OfficeCLI adapter — DOCX, XLSX, PPTX (and the legacy .doc/.xls/.ppt trio are
explicitly NOT supported here; see FORMAT_MATRIX.md row 4 for legacy fallback).

Strategy:
  1. shell out to `officecli view <file> html` (or text/outline for tables/structure)
  2. strip OfficeCLI's render scaffolding (page wrappers, hidden span markers)
  3. convert the cleaned HTML to Markdown via markdownify
  4. return the normalized dict
"""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

from bs4 import BeautifulSoup
from markdownify import markdownify as md

from .base import Adapter, AdapterError


class OfficeCLIAdapter(Adapter):
    name = "officecli"
    extensions = {".docx", ".xlsx", ".pptx"}

    def __init__(self, binary: str = "officecli", timeout: int = 60) -> None:
        self.binary = binary
        self.timeout = timeout
        # On Windows, npm-installed CLIs ship as `name.cmd` wrappers. Resolve via
        # shutil.which so subprocess.run can find them; pass shell=True if it's
        # a .cmd so cmd.exe can interpret it.
        resolved = shutil.which(binary)
        if not resolved:
            raise AdapterError(
                f"`{binary}` not found on PATH. Install with: npm install -g @officecli/officecli"
            )
        self._resolved = resolved
        self._use_shell = resolved.lower().endswith((".cmd", ".bat"))

    def extract(self, source: Path) -> dict:
        try:
            html = self._run(source)
        except subprocess.TimeoutExpired as e:
            raise AdapterError(f"officecli timed out after {self.timeout}s on {source}") from e
        except subprocess.CalledProcessError as e:
            raise AdapterError(f"officecli failed on {source}: {e.stderr or e}") from e

        cleaned = self._clean_html(html)
        body_md = md(cleaned, heading_style="ATX", bullets="-")
        title = self._extract_title(cleaned) or source.stem

        # Drop a leading line that is just the original filename (OfficeCLI puts
        # `<title>filename.docx</title>` in the rendered HTML; markdownify lifts
        # it to a top-level paragraph). Keeps the body clean.
        lines = body_md.splitlines()
        while lines and lines[0].strip() == source.name:
            lines.pop(0)
        # Also drop any immediately following blank lines
        while lines and not lines[0].strip():
            lines.pop(0)
        body_md = "\n".join(lines) + "\n" if lines else ""

        return {
            "title": title,
            "body_md": body_md,
            "metadata": {"engine": self.name, "source_format": source.suffix.lower()},
            "attachments": [],
        }

    def _run(self, source: Path) -> str:
        # Use shell=True when the resolved binary is a .cmd wrapper so cmd.exe
        # can interpret it; otherwise subprocess.run can't find the executable.
        proc = subprocess.run(
            [self._resolved, "view", str(source), "html"],
            capture_output=True,
            text=True,
            timeout=self.timeout,
            check=True,
            shell=self._use_shell,
        )
        return proc.stdout

    @staticmethod
    def _clean_html(html: str) -> str:
        """Strip OfficeCLI's render scaffolding so markdownify sees clean content."""
        soup = BeautifulSoup(html, "lxml")

        # Remove style/script blocks (render CSS, not content)
        for tag in soup.find_all(["style", "script"]):
            tag.decompose()

        # Remove hidden block-marker spans (OfficeCLI uses wb/we for edit boundaries)
        for span in soup.find_all("span", class_=re.compile(r"^(wb|we)$")):
            span.decompose()

        # Unwrap page wrappers so headings/body are direct children of the doc
        for cls in ("page-wrapper", "page", "page-body", "doc-header", "doc-footer"):
            for el in soup.find_all(class_=cls):
                el.unwrap()

        return str(soup)

    @staticmethod
    def _extract_title(soup_html: str) -> str | None:
        soup = BeautifulSoup(soup_html, "lxml")
        # Prefer the first h1; fall back to <title>
        h1 = soup.find("h1")
        if h1 and h1.get_text(strip=True):
            return h1.get_text(strip=True)
        if soup.title and soup.title.string:
            return soup.title.string.strip()
        return None
