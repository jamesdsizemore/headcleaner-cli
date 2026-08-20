"""Deterministic, cited chunk derivatives for canonical documents and OKF bundles."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .model import Element
from .normalize import CanonicalDoc

CHUNKING_VERSION = "1"
_REQUIRED_CITATION_KEYS = frozenset({"source_uri", "source_sha256", "page", "start", "end"})
_RESERVED_CONCEPTS = frozenset({"index.md", "log.md", "REPORT.md"})


@dataclass(frozen=True)
class Chunk:
    id: str
    concept_id: str
    source_sha256: str
    element_ids: tuple[str, ...]
    ordinal: int
    heading_path: tuple[str, ...]
    text: str
    citation: dict[str, Any]
    token_estimate: int
    chunking_version: str = CHUNKING_VERSION
    oversize: bool = False

    def __post_init__(self) -> None:
        if not self.element_ids:
            raise ValueError("chunk element_ids must be non-empty")
        if self.ordinal < 0:
            raise ValueError("chunk ordinal must be non-negative")
        if set(self.citation) != _REQUIRED_CITATION_KEYS:
            raise ValueError(
                "chunk citation must contain source_uri, source_sha256, page, start, and end"
            )
        if self.citation["source_sha256"] != self.source_sha256:
            raise ValueError("chunk citation source_sha256 must match chunk source_sha256")
        if not self.citation["source_uri"]:
            raise ValueError("chunk citation source_uri is required")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "concept_id": self.concept_id,
            "source_sha256": self.source_sha256,
            "element_ids": list(self.element_ids),
            "ordinal": self.ordinal,
            "heading_path": list(self.heading_path),
            "text": self.text,
            "citation": self.citation,
            "token_estimate": self.token_estimate,
            "chunking_version": self.chunking_version,
            "oversize": self.oversize,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> Chunk:
        citation = value.get("citation")
        if not isinstance(citation, dict):
            raise ValueError("chunk citation is required")
        return cls(
            id=str(value["id"]),
            concept_id=str(value["concept_id"]),
            source_sha256=str(value["source_sha256"]),
            element_ids=tuple(str(item) for item in value["element_ids"]),
            ordinal=int(value["ordinal"]),
            heading_path=tuple(str(item) for item in value.get("heading_path", [])),
            text=str(value["text"]),
            citation=dict(citation),
            token_estimate=int(value["token_estimate"]),
            chunking_version=str(value.get("chunking_version", CHUNKING_VERSION)),
            oversize=bool(value.get("oversize", False)),
        )


def _chunk_id(source_sha256: str, element_ids: Iterable[str], ordinal: int) -> str:
    payload = "\0".join((source_sha256, *element_ids, str(ordinal), CHUNKING_VERSION))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _citation(source_uri: str, source_sha256: str, elements: list[Element]) -> dict[str, Any]:
    locations = [element.source_location or {} for element in elements]
    pages = [location.get("page") for location in locations if location.get("page") is not None]
    starts = [location.get("start") for location in locations if location.get("start") is not None]
    ends = [location.get("end") for location in locations if location.get("end") is not None]
    return {
        "source_uri": source_uri,
        "source_sha256": source_sha256,
        "page": min(pages) if pages else None,
        "start": min(starts) if starts else None,
        "end": max(ends) if ends else None,
    }


def _make_chunk(
    *,
    concept_id: str,
    source_uri: str,
    source_sha256: str,
    elements: list[Element],
    ordinal: int,
    heading_path: tuple[str, ...],
    max_chars: int,
) -> Chunk:
    text = "\n\n".join(element.text for element in elements).strip()
    element_ids = tuple(element.id for element in elements)
    return Chunk(
        id=_chunk_id(source_sha256, element_ids, ordinal),
        concept_id=concept_id,
        source_sha256=source_sha256,
        element_ids=element_ids,
        ordinal=ordinal,
        heading_path=heading_path,
        text=text,
        citation=_citation(source_uri, source_sha256, elements),
        token_estimate=max(1, (len(text.split()) + 3) // 4),
        oversize=len(text) > max_chars,
    )


def chunk_elements(
    elements: Iterable[Element],
    *,
    concept_id: str,
    source_uri: str,
    source_sha256: str,
    max_chars: int = 2000,
) -> list[Chunk]:
    """Chunk an ordered element stream without splitting table/code evidence."""
    if max_chars <= 0:
        raise ValueError("max_chars must be positive")
    chunks: list[Chunk] = []
    current: list[Element] = []
    heading_path: tuple[str, ...] = ()
    current_heading_path: tuple[str, ...] = ()

    def flush() -> None:
        if current:
            chunks.append(
                _make_chunk(
                    concept_id=concept_id,
                    source_uri=source_uri,
                    source_sha256=source_sha256,
                    elements=current.copy(),
                    ordinal=len(chunks),
                    heading_path=current_heading_path,
                    max_chars=max_chars,
                )
            )
            current.clear()

    for element in sorted(elements, key=lambda item: item.ordinal):
        if element.kind == "heading":
            flush()
            heading_path = (element.text.strip(),) if element.text.strip() else heading_path
            current_heading_path = heading_path
        projected = sum(len(item.text) for item in current) + len(element.text)
        if current and projected > max_chars:
            flush()
            current_heading_path = heading_path
        if not current:
            current_heading_path = heading_path
        current.append(element)
        if element.kind in {"table", "code"}:
            flush()
    flush()
    return chunks


def chunk_document(doc: CanonicalDoc, *, concept_id: str, max_chars: int = 2000) -> list[Chunk]:
    return chunk_elements(
        doc.elements,
        concept_id=concept_id,
        source_uri=doc.source_uri,
        source_sha256=doc.source_sha256,
        max_chars=max_chars,
    )


def write_chunks(bundle_root: Path, chunks: Iterable[Chunk]) -> Path:
    """Atomically replace the sole chunk cache at ``<bundle>/chunks.jsonl``."""
    bundle_root.mkdir(parents=True, exist_ok=True)
    path = bundle_root / "chunks.jsonl"
    rows = [json.dumps(chunk.to_dict(), ensure_ascii=False, sort_keys=True) for chunk in chunks]
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", delete=False, dir=bundle_root, newline="\n"
    ) as handle:
        handle.write("\n".join(rows) + ("\n" if rows else ""))
        temporary = Path(handle.name)
    os.replace(temporary, path)
    return path


def read_chunks(bundle_root: Path) -> list[Chunk]:
    path = bundle_root / "chunks.jsonl"
    if not path.exists():
        return []
    chunks: list[Chunk] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid chunks.jsonl line {line_no}") from exc
        chunks.append(Chunk.from_dict(value))
    return chunks


def _elements_from_markdown(source_sha256: str, body: str) -> list[Element]:
    elements: list[Element] = []
    for ordinal, block in enumerate(
        part for part in re.split(r"\n\s*\n", body.strip()) if part.strip()
    ):
        heading = re.match(r"^#{1,6}\s+(.+)$", block)
        kind = "heading" if heading else "table" if block.lstrip().startswith("|") else "paragraph"
        text = heading.group(1).strip() if heading else block.strip()
        elements.append(Element.create(source_sha256, kind, ordinal, text))
    return elements


def rebuild_chunks(bundle_root: Path, *, max_chars: int = 2000) -> list[Chunk]:
    """Regenerate byte-stable chunks from canonical OKF concepts only."""
    chunks: list[Chunk] = []
    for path in sorted(bundle_root.rglob("*.md")):
        if path.name in _RESERVED_CONCEPTS:
            continue
        text = path.read_text(encoding="utf-8")
        match = re.match(r"\A---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
        if not match:
            continue
        frontmatter = yaml.safe_load(match.group(1)) or {}
        if not isinstance(frontmatter, dict) or "type" not in frontmatter:
            continue
        sources = frontmatter.get("sources") or []
        source = sources[0] if isinstance(sources, list) and sources else {}
        if not isinstance(source, dict) or not source.get("sha256") or not source.get("uri"):
            raise ValueError(f"concept lacks source citation: {path}")
        source_sha256 = str(source["sha256"])
        concept_id = path.relative_to(bundle_root).as_posix()
        chunks.extend(
            chunk_elements(
                _elements_from_markdown(source_sha256, text[match.end() :]),
                concept_id=concept_id,
                source_uri=str(source["uri"]),
                source_sha256=source_sha256,
                max_chars=max_chars,
            )
        )
    # A chunk ordinal is source-local; retain deterministic concept order for the file.
    write_chunks(bundle_root, chunks)
    return chunks
