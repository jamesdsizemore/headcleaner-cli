from __future__ import annotations

import json
from pathlib import Path

import pytest

from headcleaner.model import Element
from headcleaner.normalize import CanonicalDoc


def _doc(tmp_path: Path, elements: list[Element]) -> CanonicalDoc:
    source = tmp_path / "source.txt"
    source.write_text("source", encoding="utf-8")
    return CanonicalDoc(
        title="Source",
        body_md="",
        source_path=source,
        source_relpath=Path("source.txt"),
        source_uri=source.resolve().as_uri(),
        source_sha256="a" * 64,
        source_size_bytes=6,
        source_format=".txt",
        engine="txt",
        elements=elements,
    )


def test_chunks_are_deterministic_and_keep_heading_context(tmp_path: Path) -> None:
    from headcleaner.chunking import chunk_document

    elements = [
        Element.create("a" * 64, "heading", 0, "Overview", source_location={"page": 1}),
        Element.create(
            "a" * 64, "paragraph", 1, "A short explanation.", source_location={"page": 1}
        ),
        Element.create("a" * 64, "heading", 2, "Details", source_location={"page": 2}),
        Element.create("a" * 64, "paragraph", 3, "Further details.", source_location={"page": 2}),
    ]
    doc = _doc(tmp_path, elements)

    first = chunk_document(doc, concept_id="source.md", max_chars=1000)
    second = chunk_document(doc, concept_id="source.md", max_chars=1000)

    assert [chunk.to_dict() for chunk in first] == [chunk.to_dict() for chunk in second]
    assert [chunk.heading_path for chunk in first] == [("Overview",), ("Details",)]
    assert all(chunk.citation["source_sha256"] == "a" * 64 for chunk in first)
    assert all(chunk.element_ids for chunk in first)


def test_table_is_indivisible_and_oversize_is_marked(tmp_path: Path) -> None:
    from headcleaner.chunking import chunk_document

    table_text = "| one | two |\n| --- | --- |\n| alpha | beta |"
    elements = [Element.create("a" * 64, "table", 0, table_text, source_location={"page": 4})]
    chunks = chunk_document(_doc(tmp_path, elements), concept_id="source.md", max_chars=10)

    assert len(chunks) == 1
    assert chunks[0].text == table_text
    assert chunks[0].oversize is True


def test_chunk_jsonl_round_trip_and_rejects_missing_citation(tmp_path: Path) -> None:
    from headcleaner.chunking import Chunk, chunk_document, read_chunks, write_chunks

    element = Element.create(
        "a" * 64, "paragraph", 0, "Indexed text.", source_location={"start": 1, "end": 13}
    )
    chunks = chunk_document(_doc(tmp_path, [element]), concept_id="source.md")
    out = write_chunks(tmp_path, chunks)

    assert out == tmp_path / "chunks.jsonl"
    assert read_chunks(tmp_path) == chunks
    payload = json.loads(out.read_text(encoding="utf-8").splitlines()[0])
    payload["citation"] = {}
    with pytest.raises(ValueError, match="citation"):
        Chunk.from_dict(payload)
