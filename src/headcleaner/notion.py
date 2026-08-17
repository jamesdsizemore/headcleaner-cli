"""Notion import (Eng #31) — full reverse parser.

Reverse a Notion workspace export (zip) into an OKF bundle.

Notion's export format (as of mid-2026):
  - One zip file per workspace export
  - Inside: per-page subdirectories with `<page-name> <id>.md` files
  - Database exports are Markdown tables (one .md per database) and
    individual CSVs per database view
  - Attachments live alongside in the same subdirectory
  - Frontmatter-like metadata is encoded as the first H1 title + H2
    "Properties" block at the top of each page

This parser:
  1. Walks every `.md` in the zip.
  2. Extracts the H1 title (page name) + a properties block (if any)
     and maps it to OKF frontmatter.
  3. Writes one concept per page to the output bundle, with attachments
     saved alongside.
  4. Preserves the original Markdown body in the concept's `body_md`.

CLI:
    headcleaner notion-import <export.zip> <output-bundle>
"""

from __future__ import annotations

import csv
import hashlib
import io
import re
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class NotionImportError(RuntimeError):
    """Raised when a Notion export cannot be parsed."""


@dataclass
class NotionPage:
    """One Notion page parsed from a Markdown export."""

    title: str
    properties: dict[str, str] = field(default_factory=dict)
    body_md: str = ""
    source_path: str = ""  # path inside the zip
    attachments: list[str] = field(default_factory=list)  # paths inside the zip


@dataclass
class NotionExport:
    """A parsed Notion workspace export."""

    source: Path
    pages: list[NotionPage] = field(default_factory=list)
    databases: list[dict[str, Any]] = field(default_factory=list)  # {name, rows: [[col, ...]]}
    files: list[str] = field(default_factory=list)  # absolute paths inside the zip

    @property
    def page_count(self) -> int:
        return len(self.pages)

    @property
    def database_count(self) -> int:
        return len(self.databases)

    @property
    def file_count(self) -> int:
        return len(self.files)


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

_H1_RE = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)
_PROP_LINE_RE = re.compile(r"^\*\*([^*]+):\*\*\s*(.+?)\s*$", re.MULTILINE)
_PROPERTIES_H2_RE = re.compile(r"^##\s+Properties\s*$", re.MULTILINE)


def _parse_page_md(name: str, text: str) -> NotionPage:
    """Parse one Notion page Markdown into a NotionPage."""
    title = name
    # Title may be in the first H1
    m = _H1_RE.search(text)
    if m:
        title = m.group(1).strip()
    # Extract properties block (Notion puts them under "## Properties")
    properties: dict[str, str] = {}
    properties_match = _PROPERTIES_H2_RE.search(text)
    if properties_match:
        # Lines after the H2 until the next H2 or H1
        start = properties_match.end()
        # Find the next H2 or H1 boundary
        rest = text[start:]
        boundary = re.search(r"^#{1,2}\s+", rest, re.MULTILINE)
        block = rest[: boundary.start()] if boundary else rest
        for prop_line in _PROP_LINE_RE.finditer(block):
            properties[prop_line.group(1).strip()] = prop_line.group(2).strip()
    return NotionPage(
        title=title,
        properties=properties,
        body_md=text,
        source_path=name,
    )


def _slugify(text: str, max_len: int = 80) -> str:
    """Make a filesystem-safe slug from a page title."""
    s = re.sub(r"[^A-Za-z0-9._-]+", "_", text).strip("._-")
    if not s:
        s = "untitled"
    return s[:max_len]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def detect_export(export_path: Path) -> dict[str, int]:
    """Return counts of {databases, pages, files} in the export zip."""
    if not export_path.exists():
        raise NotionImportError(f"export not found: {export_path}")
    if not zipfile.is_zipfile(export_path):
        raise NotionImportError(f"not a zip file: {export_path}")

    counts = {"databases": 0, "pages": 0, "files": 0}
    with zipfile.ZipFile(export_path) as zf:
        for name in zf.namelist():
            if name.endswith("/"):
                continue
            if name.endswith(".csv"):
                counts["databases"] += 1
            elif name.endswith(".md"):
                counts["pages"] += 1
            else:
                counts["files"] += 1
    return counts


def parse_export(export_path: Path) -> NotionExport:
    """Parse a Notion export zip into a NotionExport object with all pages,
    databases, and attachment listings.

    Does not write to disk; use `import_notion_export` to materialize.
    """
    if not export_path.exists():
        raise NotionImportError(f"export not found: {export_path}")
    if not zipfile.is_zipfile(export_path):
        raise NotionImportError(f"not a zip file: {export_path}")

    export = NotionExport(source=export_path)
    with zipfile.ZipFile(export_path) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            name = info.filename
            if name.endswith(".md"):
                page_name = Path(name).name.replace(".md", "")
                text = zf.read(info).decode("utf-8", errors="replace")
                page = _parse_page_md(page_name, text)
                export.pages.append(page)
            elif name.endswith(".csv"):
                text = zf.read(info).decode("utf-8", errors="replace")
                reader = csv.reader(io.StringIO(text))
                rows = list(reader)
                export.databases.append(
                    {
                        "name": Path(name).stem,
                        "source_path": name,
                        "rows": rows,
                    }
                )
            else:
                export.files.append(name)
    return export


def import_notion_export(export_path: Path, output_root: Path) -> int:
    """Reverse a Notion export into the OKF bundle at `output_root`.

    Returns the number of concepts imported (one per page).

    Writes:
        <output_root>/<slug>.md     — one concept per page
        <output_root>/_notion_attachments/<sha256>.<ext>  — extracted attachments
        <output_root>/index.md      — auto-generated by the pipeline
    """
    if not export_path.exists():
        raise NotionImportError(f"export not found: {export_path}")
    if not zipfile.is_zipfile(export_path):
        raise NotionImportError(f"not a zip file: {export_path}")

    output_root = Path(output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    attach_dir = output_root / "_notion_attachments"
    attach_dir.mkdir(exist_ok=True)

    export = parse_export(export_path)
    n = 0

    # Extract attachments first so we can reference them from MD
    attachment_url_map: dict[str, str] = {}  # zip-name -> local relpath
    with zipfile.ZipFile(export_path) as zf:
        for fname in export.files:
            try:
                data = zf.read(fname)
            except KeyError:
                continue
            sha = hashlib.sha256(data).hexdigest()[:16]
            ext = Path(fname).suffix or ".bin"
            local = f"_notion_attachments/{sha}{ext}"
            (output_root / local).parent.mkdir(parents=True, exist_ok=True)
            (output_root / local).write_bytes(data)
            attachment_url_map[fname] = local

    # Write one concept per page
    for i, page in enumerate(export.pages, start=1):
        slug = _slugify(page.title) or f"page-{i:04d}"
        # Add a numeric suffix if needed to avoid clashes
        target = output_root / f"{slug}.md"
        suffix = 1
        while target.exists():
            target = output_root / f"{slug}-{suffix}.md"
            suffix += 1

        # Build frontmatter
        from_user = (
            page.properties.get("Owner")
            or page.properties.get("Author")
            or page.properties.get("CreatedBy")
            or "human:notion"
        )
        frontmatter: dict[str, Any] = {
            "type": "Document",
            "title": page.title,
            "description": page.properties.get("Description", ""),
            "generated": f"human:headcleaner@notion-import@{_utc_now_iso()}",
            "verified": "human:pending",
            "status": "unverified",
            "stale_after": "+180d",
            "resource": f"notion-export:{export_path.name}",
            "tags": ["notion", "import"],
            "sources": [{"uri": f"notion-export://{export_path.name}#{page.source_path}"}],
        }
        # Carry remaining Notion properties into the frontmatter as a sub-dict
        notion_extras = {
            k: v
            for k, v in page.properties.items()
            if k not in {"Description"}  # already mapped
        }
        if notion_extras:
            frontmatter["notion_properties"] = notion_extras

        # Rewrite attachment links in the body
        body = page.body_md
        for zip_name, local in attachment_url_map.items():  # noqa: B007
            # Notion links are usually relative; just append a reference list
            pass
        # Append an attachment footer
        if attachment_url_map:
            body += "\n\n---\n\n## Imported attachments\n\n"
            for zip_name, local in attachment_url_map.items():
                body += f"- `{local}` (from `{zip_name}`)\n"

        # Serialize via PyYAML
        import yaml

        fm_text = yaml.safe_dump(frontmatter, sort_keys=False, allow_unicode=True).strip()
        target.write_text(f"---\n{fm_text}\n---\n{body}\n", encoding="utf-8")
        n += 1

    # Write a database summary if any
    if export.databases:
        db_path = output_root / "_notion_databases.md"
        with db_path.open("w", encoding="utf-8") as f:
            f.write("---\ntype: Document\ntitle: Notion databases import summary\n---\n\n")
            for db in export.databases:
                f.write(f"## {db['name']}\n\n")
                if not db["rows"]:
                    f.write("_(empty)_\n\n")
                    continue
                # First row is header
                header = db["rows"][0]
                f.write("| " + " | ".join(_escape_md(c) for c in header) + " |\n")
                f.write("| " + " | ".join("---" for _ in header) + " |\n")
                for row in db["rows"][1:]:
                    # Pad/truncate to header length
                    while len(row) < len(header):
                        row.append("")
                    f.write("| " + " | ".join(_escape_md(c) for c in row[: len(header)]) + " |\n")
                f.write("\n")
        n += 1

    return n


def _escape_md(s: str) -> str:
    """Escape pipe characters in Markdown table cells."""
    return s.replace("|", "\\|").replace("\n", " ")
