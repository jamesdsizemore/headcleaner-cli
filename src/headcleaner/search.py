"""Shared deterministic local search over a Phase 2 SQLite FTS5 index."""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .index import INDEX_SCHEMA_VERSION, index_path


class SearchQueryError(ValueError):
    pass


@dataclass(frozen=True)
class SearchHit:
    rank: float
    chunk_id: str
    concept_path: str
    ordinal: int
    excerpt: str
    citation: dict[str, Any]
    trust_state: str
    index_schema_version: str = INDEX_SCHEMA_VERSION


def search(
    bundle_root: Path,
    query: str,
    *,
    tag: str | None = None,
    type: str | None = None,
    status: str | None = None,
    path: str | None = None,
    source_sha: str | None = None,
    limit: int = 20,
) -> list[SearchHit]:
    if not query.strip():
        return []
    if limit <= 0:
        raise ValueError("limit must be positive")
    database = index_path(bundle_root)
    if not database.exists():
        raise ValueError("index does not exist; run `headcleaner index rebuild BUNDLE`")
    where = ["chunk_fts MATCH ?"]
    params: list[Any] = [query]
    if tag:
        where.append("EXISTS (SELECT 1 FROM chunk_tag ct WHERE ct.chunk_id=c.id AND ct.tag=?)")
        params.append(tag)
    if type:
        where.append("p.type=?")
        params.append(type)
    if status:
        where.append("p.status=?")
        params.append(status)
    if path:
        where.append("c.concept_path LIKE ?")
        params.append(f"{path}%")
    if source_sha:
        where.append("c.source_sha256=?")
        params.append(source_sha)
    params.append(limit)
    sql = f"""
        SELECT bm25(chunk_fts), c.id, c.concept_path, c.ordinal,
               snippet(chunk_fts, 0, '[', ']', '…', 16), c.citation, c.trust_state
        FROM chunk_fts JOIN chunk c ON c.rowid=chunk_fts.rowid
        JOIN concept p ON p.path=c.concept_path
        WHERE {" AND ".join(where)}
        ORDER BY bm25(chunk_fts), c.concept_path, c.ordinal
        LIMIT ?
    """
    try:
        with closing(sqlite3.connect(database)) as connection:
            rows = connection.execute(sql, params).fetchall()
    except sqlite3.OperationalError as exc:
        if (
            "fts5" in str(exc).lower()
            or "syntax" in str(exc).lower()
            or "unterminated" in str(exc).lower()
        ):
            raise SearchQueryError(f"invalid search query: {exc}") from exc
        raise
    return [
        SearchHit(float(row[0]), row[1], row[2], int(row[3]), row[4], json.loads(row[5]), row[6])
        for row in rows
    ]
