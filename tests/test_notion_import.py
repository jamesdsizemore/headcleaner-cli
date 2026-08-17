"""Tests for the full Notion import impl (Eng #31)."""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from headcleaner.notion import (
    NotionImportError,
    detect_export,
    parse_export,
    import_notion_export,
    _parse_page_md,
    _slugify,
)


@pytest.fixture
def notion_zip(tmp_path: Path) -> Path:
    """Build a fake Notion export zip with 2 pages, 1 database, 1 attachment."""
    p = tmp_path / "export.zip"
    with zipfile.ZipFile(p, "w", zipfile.ZIP_DEFLATED) as zf:
        # Page 1: title + properties
        page1 = (
            "# Meeting Notes\n\n"
            "Sprint planning review.\n\n"
            "## Properties\n\n"
            "**Owner:** Alice\n"
            "**Status:** active\n"
            "**Description:** Weekly notes\n\n"
            "## Action items\n\n"
            "- [ ] Fix bug\n"
        )
        zf.writestr("Meeting Notes abc123.md", page1)
        # Page 2: minimal
        page2 = "# Random Idea\n\nJust a thought.\n"
        zf.writestr("Random Idea def456.md", page2)
        # Database CSV
        db = "Name,Owner,Status\nProject X,Bob,active\nProject Y,Carol,pending\n"
        zf.writestr("Projects 789.csv", db)
        # Attachment
        zf.writestr("Meeting Notes abc123/sample.png", b"\x89PNG fake image bytes")
    return p


def test_slugify_basic() -> None:
    """_slugify turns titles into safe filenames."""
    assert _slugify("Meeting Notes") == "Meeting_Notes"
    assert _slugify("Q3: 2026 / Report") == "Q3_2026_Report"
    assert _slugify("") == "untitled"
    assert _slugify("hello world") == "hello_world"


def test_parse_page_md_extracts_title() -> None:
    """_parse_page_md extracts the title from the first H1."""
    text = "# Hello World\n\nbody\n"
    page = _parse_page_md("page-id.md", text)
    assert page.title == "Hello World"


def test_parse_page_md_extracts_properties() -> None:
    """_parse_page_md parses the Properties block when present."""
    text = "# Title\n\n## Properties\n\n**Owner:** Alice\n**Status:** active\n\n## Body\n\nstuff\n"
    page = _parse_page_md("id.md", text)
    assert page.properties == {"Owner": "Alice", "Status": "active"}


def test_parse_page_md_no_properties_block() -> None:
    """_parse_page_md returns empty properties when there is no Properties block."""
    text = "# Title\n\nbody only\n"
    page = _parse_page_md("id.md", text)
    assert page.properties == {}


def test_detect_export_counts(notion_zip: Path) -> None:
    """detect_export counts databases, pages, files."""
    counts = detect_export(notion_zip)
    assert counts["databases"] == 1
    assert counts["pages"] == 2
    assert counts["files"] == 1


def test_detect_export_missing_raises(tmp_path: Path) -> None:
    """detect_export raises NotionImportError when the path doesn't exist."""
    with pytest.raises(NotionImportError):
        detect_export(tmp_path / "no-such.zip")


def test_detect_export_not_a_zip(tmp_path: Path) -> None:
    """detect_export raises NotionImportError when the file isn't a zip."""
    f = tmp_path / "not.zip"
    f.write_text("not a zip")
    with pytest.raises(NotionImportError):
        detect_export(f)


def test_parse_export_returns_pages(notion_zip: Path) -> None:
    """parse_export returns a NotionExport with 2 pages."""
    export = parse_export(notion_zip)
    assert export.page_count == 2
    titles = {p.title for p in export.pages}
    assert "Meeting Notes" in titles
    assert "Random Idea" in titles


def test_parse_export_returns_databases(notion_zip: Path) -> None:
    """parse_export returns the database with rows."""
    export = parse_export(notion_zip)
    assert export.database_count == 1
    db = export.databases[0]
    assert db["name"] == "Projects 789"
    # Header + 2 data rows
    assert len(db["rows"]) == 3
    assert db["rows"][0] == ["Name", "Owner", "Status"]


def test_import_notion_export_writes_concepts(notion_zip: Path, tmp_path: Path) -> None:
    """import_notion_export writes one OKF concept per page."""
    out = tmp_path / "out"
    n = import_notion_export(notion_zip, out)
    assert n >= 2  # at least the 2 pages, possibly +1 for database summary
    md_files = sorted(out.glob("*.md"))
    assert any("Meeting_Notes" in f.name for f in md_files)
    # Notion properties were extracted
    meeting = next(f for f in md_files if "Meeting_Notes" in f.name)
    content = meeting.read_text(encoding="utf-8")
    assert "type: Document" in content
    assert "Owner: Alice" in content or "Alice" in content


def test_import_notion_export_extracts_attachments(notion_zip: Path, tmp_path: Path) -> None:
    """import_notion_export extracts attachments to _notion_attachments/."""
    out = tmp_path / "out"
    import_notion_export(notion_zip, out)
    attachments = list((out / "_notion_attachments").iterdir())
    assert len(attachments) == 1
    assert attachments[0].name.endswith(".png")


def test_import_notion_export_writes_database_summary(notion_zip: Path, tmp_path: Path) -> None:
    """import_notion_export writes a Notion databases summary file."""
    out = tmp_path / "out"
    import_notion_export(notion_zip, out)
    db_summary = out / "_notion_databases.md"
    assert db_summary.exists()
    content = db_summary.read_text(encoding="utf-8")
    assert "Projects" in content
    assert "Project X" in content
    assert "Bob" in content


def test_import_notion_export_missing_raises(tmp_path: Path) -> None:
    """import_notion_export raises NotionImportError when the export doesn't exist."""
    out = tmp_path / "out"
    with pytest.raises(NotionImportError):
        import_notion_export(tmp_path / "no-such.zip", out)


def test_import_notion_export_empty_zip(tmp_path: Path) -> None:
    """import_notion_export returns 0 for an empty zip."""
    p = tmp_path / "empty.zip"
    with zipfile.ZipFile(p, "w"):
        pass
    out = tmp_path / "out"
    n = import_notion_export(p, out)
    assert n == 0
