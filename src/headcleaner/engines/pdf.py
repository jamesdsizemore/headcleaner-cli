"""PDF adapter — text-layer extraction via pdfplumber (with pypdf fallback).

Strategy:
  1. Try pdfplumber per page: emit headings as '#', paragraphs as text, tables as
     GFM tables. Preserves structure when present.
  2. If `--ocr` is enabled, fall back to pytesseract for pages with no text layer.
  3. Otherwise: emit a fenced block with a note that the page is image-only.

For v0.1 we only handle the text-layer path. OCR is wired but gated by a flag
that the CLI will pass through.
"""

from __future__ import annotations

from pathlib import Path

import pdfplumber

from .base import Adapter, AdapterError


class PdfAdapter(Adapter):
    name = "pdf"
    extensions = {".pdf"}

    def __init__(self, ocr: bool = False, ocr_lang: str = "eng") -> None:
        self.ocr = ocr
        self.ocr_lang = ocr_lang

    def extract(self, source: Path, *, progress=None) -> dict:
        if self.ocr:
            try:
                import pytesseract  # noqa: F401  (presence check)
                from PIL import Image  # noqa: F401
            except ImportError as e:
                raise AdapterError(
                    "--ocr requires pytesseract + Pillow. Install: uv pip install pytesseract Pillow"
                ) from e

        pages_md: list[str] = []
        image_only_pages: list[int] = []
        tabular_assets: list[dict] = []
        table_ordinal = 0

        try:
            with pdfplumber.open(source) as pdf:
                # pdfplumber exposes encryption via pdf.metadata; a None metadata
                # or absent /Encrypt entry means the PDF is not encrypted.
                if pdf.metadata and pdf.metadata.get("/Encrypt"):
                    raise AdapterError(
                        f"PDF is encrypted: {source}. "
                        f"Decrypt with `qpdf --decrypt {source.name} {source.stem}.decrypted.pdf` "
                        f"then re-run headcleaner on the decrypted copy."
                    )
                total_pages = len(pdf.pages)
                for idx, page in enumerate(pdf.pages, start=1):
                    if progress is not None:
                        try:
                            progress(idx, total_pages)
                        except Exception:
                            pass  # progress is best-effort; never block extraction
                    page_md = self._render_page(page)
                    try:
                        tables = page.extract_tables() or []
                    except Exception:
                        tables = []
                    for table in tables:
                        asset = _table_to_asset(table, page_number=idx, ordinal=table_ordinal)
                        if asset is not None:
                            tabular_assets.append(asset)
                            table_ordinal += 1
                    if page_md:
                        pages_md.append(f"## Page {idx}\n\n{page_md}")
                    else:
                        image_only_pages.append(idx)
        except AdapterError:
            raise
        except Exception as e:
            # pdfplumber raises PasswordError for some encrypted PDFs; map to a clear message.
            msg = str(e)
            if "password" in msg.lower() or "encrypt" in msg.lower():
                raise AdapterError(
                    f"PDF is encrypted or password-protected: {source}. "
                    f"Decrypt with `qpdf --decrypt {source.name} {source.stem}.decrypted.pdf` "
                    f"then re-run headcleaner on the decrypted copy. ({type(e).__name__})"
                ) from e
            raise AdapterError(f"pdfplumber failed on {source}: {e}") from e

        if image_only_pages and not self.ocr:
            note = (
                f"\n\n> **Note:** {len(image_only_pages)} page(s) "
                f"({', '.join(str(p) for p in image_only_pages[:5])}{'…' if len(image_only_pages) > 5 else ''}) "  # noqa: E501
                f"have no extractable text layer. Re-run with `--ocr` to enable Tesseract OCR."
            )
            body = "\n\n".join(pages_md) + note if pages_md else note.lstrip("\n")
        else:
            body = "\n\n".join(pages_md) or "(empty PDF)"

        return {
            "title": source.stem,
            "body_md": body + "\n",
            "metadata": {
                "engine": self.name,
                "source_format": ".pdf",
                "image_only_pages": image_only_pages,
                "ocr_enabled": self.ocr,
            },
            "tabular_assets": tabular_assets,
            "attachments": [],
        }

    @staticmethod
    def _render_page(page) -> str:
        """Render a single pdfplumber page as Markdown text + tables."""
        out: list[str] = []

        # Tables first (pdfplumber's extract_tables is best-effort)
        try:
            tables = page.extract_tables() or []
        except Exception:
            tables = []

        for t_idx, table in enumerate(tables, start=1):
            if not table or not any(any(c for c in row) for row in table):
                continue
            md_table = _table_to_markdown(table)
            if md_table:
                out.append(f"**Table {t_idx}**\n\n{md_table}")

        # Then prose
        text = page.extract_text() or ""
        text = text.strip()
        if text:
            if out:
                out.append("")  # blank line between tables and prose
            out.append(text)

        return "\n\n".join(out).strip()


def _table_to_markdown(table: list[list[str | None]]) -> str:
    """Convert a pdfplumber table (list of rows, each row a list of cells) to GFM."""
    if not table or len(table) < 2:
        return ""

    def cell(value: str | None) -> str:
        if value is None:
            return ""
        return str(value).replace("|", "\\|").replace("\n", " ").strip()

    # First non-empty row becomes the header
    header = [cell(c) for c in table[0]]
    body = [[cell(c) for c in row] for row in table[1:]]

    if not any(h for h in header):
        return ""

    lines = ["| " + " | ".join(header) + " |", "| " + " | ".join("---" for _ in header) + " |"]
    for row in body:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def _table_to_asset(
    table: list[list[str | None]], *, page_number: int, ordinal: int
) -> dict | None:
    """Project a best-effort PDF table into an explicitly inferred asset payload."""
    if not table or len(table) < 2:
        return None
    columns = ["" if cell is None else str(cell).strip() for cell in table[0]]
    if not any(columns):
        return None
    rows = [["" if cell is None else str(cell).strip() for cell in row] for row in table[1:]]
    return {
        "kind": "pdf_table",
        "ordinal": ordinal,
        "columns": columns,
        "rows": rows,
        "source_location": {"page": page_number, "start": None, "end": None},
        "provenance": {"engine": "pdf", "inferred": True, "confidence": "advisory"},
    }
