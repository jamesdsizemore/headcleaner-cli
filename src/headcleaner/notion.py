"""Notion import (Eng #31) — reverse import from a Notion workspace export.

SKELETON / STUB. The full implementation tracks the OKF v0.2 bundle shape
and Notion's `.zip` export format (database dumps, page properties,
rich text blocks).

Usage (planned):
    headcleaner notion-import <export.zip> <output-bundle-dir>

The export zip contains:
    - Notion Database export (CSV-ish)
    - Per-page Markdown + sub-pages
    - Inline files (images, attachments)

This stub exposes the planned public API and raises NotImplementedError
with a clear migration path.
"""
from __future__ import annotations

import zipfile
from pathlib import Path


class NotionImportError(RuntimeError):
    """Raised when a Notion export cannot be parsed."""


def detect_export(export_path: Path) -> dict[str, int]:
    """Return counts of {databases, pages, files} in the export zip.

    Pure read; no files extracted.
    """
    if not export_path.exists():
        raise NotionImportError(f"export not found: {export_path}")
    if not zipfile.is_zipfile(export_path):
        raise NotionImportError(f"not a zip file: {export_path}")

    counts = {"databases": 0, "pages": 0, "files": 0}
    with zipfile.ZipFile(export_path) as zf:
        for name in zf.namelist():
            if name.endswith(".csv"):
                counts["databases"] += 1
            elif name.endswith(".md"):
                counts["pages"] += 1
            elif "/" not in name.split("/")[-1]:
                counts["files"] += 1
    return counts


def import_notion_export(export_path: Path, output_root: Path) -> int:
    """Reverse a Notion export into the OKF bundle at `output_root`.

    Returns the number of concepts imported.

    SKELETON: the implementation walks the zip, maps Notion page
    properties to OKF frontmatter, downloads any attached files, and
    writes one concept per page. This is left as a v0.6+ task because
    Notion's export format changes frequently and a clean implementation
    deserves a dedicated sprint.
    """
    counts = detect_export(export_path)
    raise NotionImportError(
        f"Notion import is a v0.6+ feature. Detected "
        f"{counts['databases']} databases, {counts['pages']} pages, "
        f"{counts['files']} files in {export_path.name}. "
        f"Until the full parser ships, you can extract the zip manually and "
        f"point `headcleaner convert` at the extracted Markdown directory."
    )