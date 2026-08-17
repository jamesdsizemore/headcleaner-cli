"""Shared test fixtures: tiny valid DOCX, PDF, HTML, TXT."""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest


_DOCX_CT = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>"""

_DOCX_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""

_DOCX_BODY = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:body>
<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>Test Heading</w:t></w:r></w:p>
<w:p><w:r><w:t>First test paragraph.</w:t></w:r></w:p>
</w:body>
</w:document>"""

_PDF = b"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/Parent 2 0 R/Resources<</Font<</F1 4 0 R>>>>/MediaBox[0 0 612 792]/Contents 5 0 R>>endobj
4 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj
5 0 obj<</Length 50>>stream
BT /F1 12 Tf 100 700 Td (Fixture PDF text) Tj ET
endstream
endobj
xref
0 6
0000000000 65535 f
0000000009 00000 n
0000000056 00000 n
0000000103 00000 n
0000000198 00000 n
0000000252 00000 n
trailer<</Size 6/Root 1 0 R>>
startxref
326
%%EOF
"""


@pytest.fixture
def docx_path(tmp_path: Path) -> Path:
    p = tmp_path / "test.docx"
    with zipfile.ZipFile(p, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", _DOCX_CT)
        z.writestr("_rels/.rels", _DOCX_RELS)
        z.writestr("word/document.xml", _DOCX_BODY)
    return p


@pytest.fixture
def pdf_path(tmp_path: Path) -> Path:
    p = tmp_path / "test.pdf"
    p.write_bytes(_PDF)
    return p


@pytest.fixture
def html_path(tmp_path: Path) -> Path:
    p = tmp_path / "test.html"
    p.write_text(
        "<!doctype html><html><head><title>Fixture</title></head>"
        "<body><h1>Fixture</h1><p>Test paragraph.</p>"
        "<script>stripped</script></body></html>",
        encoding="utf-8",
    )
    return p


@pytest.fixture
def txt_path(tmp_path: Path) -> Path:
    p = tmp_path / "test.txt"
    p.write_text("Hello fixture\nsecond line\n", encoding="utf-8")
    return p


@pytest.fixture
def xlsx_path() -> Path:
    """Hand-rolled valid XLSX shipped at tests/fixtures/sample.xlsx."""
    return Path(__file__).parent / "fixtures" / "sample.xlsx"


@pytest.fixture
def mixed_dir(tmp_path: Path, docx_path, pdf_path, html_path, txt_path) -> Path:
    """A folder containing one of each supported format."""
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "nested.pdf").write_bytes(_PDF)
    (tmp_path / ".hidden.txt").write_text("skipped\n", encoding="utf-8")
    return tmp_path
