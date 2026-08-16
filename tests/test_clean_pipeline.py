"""End-to-end tests for the --clean heuristic pipeline wiring (v0.8.0)."""
from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from headcleaner.run import RunOptions, run_pipeline


def _make_docx(path: Path, body_paragraphs: list[str]) -> None:
    """Build a minimal but valid .docx with the given paragraphs."""
    paragraphs_xml = "".join(
        f'<w:p><w:r><w:t>{p}</w:t></w:r></w:p>' for p in body_paragraphs
    )
    document_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f'<w:body>{paragraphs_xml}</w:body></w:document>'
    )
    rels_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="document.xml"/>'
        '</Relationships>'
    )
    pkg_rels_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
        '</Relationships>'
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        '</Types>'
    )
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types)
        zf.writestr("_rels/.rels", pkg_rels_xml)
        zf.writestr("word/document.xml", document_xml)
        zf.writestr("word/_rels/document.xml.rels", rels_xml)


def _strip_frontmatter(text: str) -> str:
    """Remove YAML frontmatter from the head of a markdown file."""
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            return parts[2]
    return text


def test_clean_md_off_by_default(tmp_path: Path) -> None:
    """Without --clean, the heuristics pipeline is NOT applied."""
    docx = tmp_path / "inbox" / "messy.docx"
    docx.parent.mkdir()
    _make_docx(docx, ["hello\u00ADworld  with   multiple   spaces"])

    out = tmp_path / "out"
    record = run_pipeline(RunOptions(input_root=tmp_path / "inbox", output_root=out, fmt="md", clean_md=False))

    md_files = list((out / "_md").glob("*.md"))
    assert len(md_files) == 1


def test_clean_md_on_applies_pipeline(tmp_path: Path) -> None:
    """With --clean=True, the heuristics pipeline runs."""
    docx = tmp_path / "inbox" / "ok.docx"
    docx.parent.mkdir()
    _make_docx(docx, ["hello\u00ADworld  with   multiple   spaces"])

    out = tmp_path / "out"
    record = run_pipeline(RunOptions(input_root=tmp_path / "inbox", output_root=out, fmt="md", clean_md=True))

    md_files = list((out / "_md").glob("*.md"))
    assert len(md_files) == 1
    full = md_files[0].read_text(encoding="utf-8")
    body = _strip_frontmatter(full)
    # Whitespace collapsed
    assert "multiple   spaces" not in body
    assert "multiple spaces" in body
    # Soft hyphen stripped from body (may survive in title frontmatter)
    assert "\u00AD" not in body


def test_clean_md_with_parallel_workers(tmp_path: Path) -> None:
    """The --clean flag also works under parallel mode (--jobs 2)."""
    docx = tmp_path / "inbox" / "parallel.docx"
    docx.parent.mkdir()
    _make_docx(docx, ["soft\u00ADhyphen test  with   spaces"])

    out = tmp_path / "out"
    record = run_pipeline(
        RunOptions(
            input_root=tmp_path / "inbox",
            output_root=out,
            fmt="md",
            clean_md=True,
            jobs=2,
        )
    )

    statuses = [r.status for r in record.results]
    assert "failed" not in statuses
    md_files = list((out / "_md").glob("*.md"))
    assert len(md_files) == 1
    full = md_files[0].read_text(encoding="utf-8")
    body = _strip_frontmatter(full)
    # Whitespace collapses; soft hyphen removed from body
    assert "\u00AD" not in body
    assert "  with   " not in body


def test_clean_md_idempotent(tmp_path: Path) -> None:
    """Running --clean twice produces the same output as running it once."""
    from headcleaner.heuristics import clean_text

    text = "exam-\nple\u00AD with\r\nweird   spacing"
    once = clean_text(text)
    twice = clean_text(once)
    assert once == twice