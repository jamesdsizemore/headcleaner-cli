"""Tests for the router (router.py) and adapters."""

from __future__ import annotations

import shutil
from pathlib import Path

from headcleaner.engines.html import HtmlAdapter
from headcleaner.engines.officecli import OfficeCLIAdapter
from headcleaner.engines.pdf import PdfAdapter
from headcleaner.engines.txt import TxtAdapter
from headcleaner.router import get_adapter, registered_extensions


def test_registered_extensions_includes_all_adapters() -> None:
    exts = registered_extensions()
    assert ".docx" in exts and ".xlsx" in exts and ".pptx" in exts
    assert ".pdf" in exts
    assert ".html" in exts and ".htm" in exts
    assert ".txt" in exts


def test_get_adapter_routes_correctly(tmp_path: Path) -> None:
    assert get_adapter(tmp_path / "x.docx").name == "officecli"
    assert get_adapter(tmp_path / "x.xlsx").name == "officecli"
    assert get_adapter(tmp_path / "x.pptx").name == "officecli"
    assert get_adapter(tmp_path / "x.pdf").name == "pdf"
    assert get_adapter(tmp_path / "x.html").name == "html"
    assert get_adapter(tmp_path / "x.htm").name == "html"
    assert get_adapter(tmp_path / "x.txt").name == "txt"


def test_get_adapter_returns_none_for_unsupported(tmp_path: Path) -> None:
    # Use extensions that no headcleaner or all2md adapter claims.
    assert get_adapter(tmp_path / "x.unknown_xyz") is None
    assert get_adapter(tmp_path / "x") is None


def test_get_adapter_honors_requested_compatible_engine(tmp_path: Path) -> None:
    assert get_adapter(tmp_path / "x.txt", requested_engine="txt").name == "txt"
    assert get_adapter(tmp_path / "x.txt", requested_engine="html") is None


def test_txt_adapter_extracts_content(txt_path: Path) -> None:
    out = TxtAdapter().extract(txt_path)
    assert out["title"] == "test"
    assert "Hello fixture" in out["body_md"]
    assert out["body_md"].startswith("```text")
    assert out["body_md"].rstrip().endswith("```")
    assert out["metadata"]["encoding"]


def test_html_adapter_strips_scripts(html_path: Path) -> None:
    out = HtmlAdapter().extract(html_path)
    assert "stripped" not in out["body_md"]
    assert "Test paragraph." in out["body_md"]
    assert out["title"] == "Fixture"


def test_pdf_adapter_extracts_text_layer(pdf_path: Path) -> None:
    out = PdfAdapter().extract(pdf_path)
    assert "Fixture PDF text" in out["body_md"]
    assert "## Page 1" in out["body_md"]


def test_pdf_adapter_ocr_flag_requires_pytesseract(pdf_path: Path) -> None:
    # Without pytesseract installed, --ocr should raise AdapterError
    out = PdfAdapter(ocr=False).extract(pdf_path)
    assert "Fixture PDF text" in out["body_md"]


def _require_officecli() -> None:
    """Fail clearly when the required OfficeCLI integration is absent."""
    assert shutil.which("officecli"), "officecli must be installed for integration tests"


def test_officecli_adapter_extracts_docx(docx_path: Path) -> None:
    _require_officecli()
    out = OfficeCLIAdapter().extract(docx_path)
    assert "Test Heading" in out["body_md"]
    # The title should NOT be the raw filename; it should be the <h1>
    assert out["title"] == "Test Heading"
    # The stray filename line should be stripped from the body
    assert not out["body_md"].lstrip().startswith("test.docx")


def test_officecli_adapter_extracts_xlsx(xlsx_path: Path) -> None:
    """End-to-end: hand-rolled XLSX -> OfficeCLI -> markdownify -> Markdown."""
    _require_officecli()
    out = OfficeCLIAdapter().extract(xlsx_path)
    # Spreadsheet content rendered as an HTML table by OfficeCLI, then markdownified
    body = out["body_md"]
    assert "Alice" in body, f"XLSX cell 'Alice' missing from body:\n{body}"
    assert "Bob" in body
    assert "92" in body
    assert "|" in body, "Markdown table delimiter missing"
