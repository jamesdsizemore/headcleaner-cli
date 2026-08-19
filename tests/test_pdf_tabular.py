from __future__ import annotations

from headcleaner.engines.pdf import _table_to_asset


def test_pdf_table_asset_marks_inferred_cells_and_page_provenance() -> None:
    asset = _table_to_asset(
        [["name", "score"], ["Ada", "10"]],
        page_number=2,
        ordinal=0,
    )

    assert asset == {
        "kind": "pdf_table",
        "ordinal": 0,
        "columns": ["name", "score"],
        "rows": [["Ada", "10"]],
        "source_location": {"page": 2, "start": None, "end": None},
        "provenance": {"engine": "pdf", "inferred": True, "confidence": "advisory"},
    }
