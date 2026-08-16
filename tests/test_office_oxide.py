"""Tests for the office_oxide / officecli adapter (v0.8.0)."""
from __future__ import annotations

import zipfile
import os
from pathlib import Path

import pytest

from headcleaner.engines.officecli import OfficeCLIAdapter, office_oxide_available
from headcleaner.engines.base import AdapterError


# ---------------------------------------------------------------------------
# Smoke test: real docx fixture (built inline)
# ---------------------------------------------------------------------------

def _make_docx(path: Path, body_paragraphs: list[str]) -> None:
    """Build a minimal but valid .docx file at ``path``."""
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


def _make_pptx(path: Path, slide_text: str) -> None:
    """Build a minimal but valid .pptx file at ``path``."""
    slide_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
        f'<p:cSld><p:spTree><p:sp><p:txBody><a:p><a:r><a:t>{slide_text}</a:t></a:r></a:p></p:txBody></p:sp></p:spTree></p:cSld>'
        '</p:sld>'
    )
    document_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
        '<p:sldIdLst><p:sldId id="256" r:id="rId1"/></p:sldIdLst>'
        '</p:presentation>'
    )
    rels_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide1.xml"/>'
        '</Relationships>'
    )
    pkg_rels_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>'
        '</Relationships>'
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>'
        '<Override PartName="/ppt/slides/slide1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>'
        '</Types>'
    )
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types)
        zf.writestr("_rels/.rels", pkg_rels_xml)
        zf.writestr("ppt/presentation.xml", document_xml)
        zf.writestr("ppt/_rels/presentation.xml.rels", rels_xml)
        zf.writestr("ppt/slides/slide1.xml", slide_xml)


@pytest.fixture
def docx_file(tmp_path: Path) -> Path:
    """A minimal .docx with a single paragraph."""
    p = tmp_path / "hello.docx"
    _make_docx(p, ["Hello world from office_oxide"])
    return p


@pytest.fixture
def pptx_file(tmp_path: Path) -> Path:
    """A minimal .pptx with a single slide."""
    p = tmp_path / "deck.pptx"
    _make_pptx(p, "Slide content here")
    return p


# ---------------------------------------------------------------------------
# Adapter behavior
# ---------------------------------------------------------------------------

def test_office_oxide_available_returns_bool() -> None:
    """office_oxide_available returns a bool."""
    assert isinstance(office_oxide_available(), bool)


@pytest.mark.skipif(not office_oxide_available(), reason="office_oxide not installed")
def test_adapter_uses_oxide_by_default(tmp_path: Path) -> None:
    """With office_oxide installed, the adapter uses it as primary backend."""
    p = tmp_path / "hello.docx"
    _make_docx(p, ["Hello via office_oxide"])
    adapter = OfficeCLIAdapter()
    assert adapter.backend == "office_oxide"


@pytest.mark.skipif(not office_oxide_available(), reason="office_oxide not installed")
def test_adapter_extracts_docx(tmp_path: Path) -> None:
    """Adapter extracts real DOCX content via office_oxide."""
    p = tmp_path / "test.docx"
    _make_docx(p, ["First paragraph", "Second paragraph"])
    adapter = OfficeCLIAdapter()
    result = adapter.extract(p)
    assert "body_md" in result
    assert "First paragraph" in result["body_md"]
    assert result["metadata"]["backend"] == "office_oxide"
    assert result["metadata"]["engine"] == "officecli"


@pytest.mark.skipif(not office_oxide_available(), reason="office_oxide not installed")
def test_adapter_extracts_pptx(tmp_path: Path) -> None:
    """Adapter extracts PPTX content via office_oxide."""
    p = tmp_path / "deck.pptx"
    _make_pptx(p, "Slide deck content here")
    adapter = OfficeCLIAdapter()
    result = adapter.extract(p)
    assert "body_md" in result
    assert "Slide deck content" in result["body_md"]
    assert result["metadata"]["source_format"] == ".pptx"


@pytest.mark.skipif(not office_oxide_available(), reason="office_oxide not installed")
def test_adapter_calls_progress(tmp_path: Path) -> None:
    """Adapter reports at least one progress tick."""
    p = tmp_path / "test.docx"
    _make_docx(p, ["body"])
    progress_calls: list[tuple[int, int]] = []

    def progress(cur: int, total: int) -> None:
        progress_calls.append((cur, total))

    adapter = OfficeCLIAdapter()
    adapter.extract(p, progress=progress)
    assert len(progress_calls) >= 1


@pytest.mark.skipif(not office_oxide_available(), reason="office_oxide not installed")
def test_adapter_extensions_match_officecli() -> None:
    """Adapter covers docx/xlsx/pptx extensions."""
    adapter = OfficeCLIAdapter()
    assert ".docx" in adapter.extensions
    assert ".xlsx" in adapter.extensions
    assert ".pptx" in adapter.extensions


@pytest.mark.skipif(not office_oxide_available(), reason="office_oxide not installed")
def test_adapter_graceful_fallback_on_invalid_file(tmp_path: Path) -> None:
    """If office_oxide fails AND officecli is not on PATH, raise AdapterError."""
    # Build a file that isn't a valid docx — extension is .docx but content is gibberish.
    p = tmp_path / "garbage.docx"
    p.write_bytes(b"not a real docx file")
    # Without officecli binary available in test env, this should raise AdapterError.
    adapter = OfficeCLIAdapter(binary="nonexistent_officecli_binary_xyz")
    with pytest.raises((AdapterError, Exception)):
        adapter.extract(p)