"""Rebuildable SQLite FTS5 index for a local OKF bundle."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import tempfile
from contextlib import closing
from pathlib import Path
from typing import Any

import yaml

from .chunking import read_chunks, rebuild_chunks

INDEX_SCHEMA_VERSION = "1"


def index_path(bundle_root: Path) -> Path:
    return bundle_root / ".headcleaner" / "index.sqlite3"


def _concepts(bundle_root: Path) -> dict[str, dict[str, Any]]:
    concepts: dict[str, dict[str, Any]] = {}
    for path in sorted(bundle_root.rglob("*.md")):
        if path.name in {"index.md", "log.md", "REPORT.md"}:
            continue
        text = path.read_text(encoding="utf-8")
        if not text.startswith("---\n"):
            continue
        yaml_text, _separator, _body = text[4:].partition("\n---\n")
        if not _separator:
            continue
        try:
            meta = yaml.safe_load(yaml_text) or {}
        except yaml.YAMLError:
            continue
        if not isinstance(meta, dict) or "type" not in meta:
            continue
        concepts[path.relative_to(bundle_root).as_posix()] = meta
    return concepts


def _init(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        PRAGMA foreign_keys = ON;
        CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE concept (
            path TEXT PRIMARY KEY,
            type TEXT NOT NULL,
            status TEXT NOT NULL,
            source_sha256 TEXT NOT NULL,
            title TEXT NOT NULL
        );
        CREATE TABLE tag (name TEXT PRIMARY KEY);
        CREATE TABLE chunk_tag (
            chunk_id TEXT NOT NULL,
            tag TEXT NOT NULL,
            PRIMARY KEY(chunk_id, tag)
        );
        CREATE TABLE chunk (
            id TEXT PRIMARY KEY,
            concept_path TEXT NOT NULL,
            ordinal INTEGER NOT NULL,
            source_sha256 TEXT NOT NULL,
            citation TEXT NOT NULL,
            trust_state TEXT NOT NULL,
            text TEXT NOT NULL,
            chunk_hash TEXT NOT NULL
        );
        CREATE VIRTUAL TABLE chunk_fts USING fts5(text, content='chunk', content_rowid='rowid');
        CREATE TABLE build (
            id INTEGER PRIMARY KEY CHECK(id=1),
            chunk_count INTEGER NOT NULL,
            input_hash TEXT NOT NULL
        );
        """
    )


def rebuild_index(bundle_root: Path) -> Path:
    """Validate inputs, build a temp database, integrity check, atomically promote."""
    chunks = read_chunks(bundle_root)
    if not chunks:
        chunks = rebuild_chunks(bundle_root)
    concepts = _concepts(bundle_root)
    missing = sorted({chunk.concept_id for chunk in chunks if chunk.concept_id not in concepts})
    if missing:
        raise ValueError(
            f"INDEX_BUILD_FAILED: chunks reference missing concepts: {', '.join(missing)}"
        )
    target = index_path(bundle_root)
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False, dir=target.parent) as handle:
        temporary = Path(handle.name)
    try:
        connection = sqlite3.connect(temporary)
        try:
            _init(connection)
            with connection:
                connection.execute(
                    "INSERT INTO meta VALUES (?, ?)", ("schema_version", INDEX_SCHEMA_VERSION)
                )
                digest = hashlib.sha256()
                for path, meta in sorted(concepts.items()):
                    source = (meta.get("sources") or [{}])[0]
                    sha = str(source.get("sha256", "")) if isinstance(source, dict) else ""
                    connection.execute(
                        "INSERT INTO concept VALUES (?, ?, ?, ?, ?)",
                        (
                            path,
                            str(meta.get("type", "")),
                            str(meta.get("status", "unverified")),
                            sha,
                            str(meta.get("title", path)),
                        ),
                    )
                for chunk in chunks:
                    meta = concepts[chunk.concept_id]
                    rendered = str(chunk.to_dict())
                    chunk_hash = hashlib.sha256(rendered.encode()).hexdigest()
                    digest.update(rendered.encode())
                    connection.execute(
                        (
                            "INSERT INTO chunk("
                            "id, concept_path, ordinal, source_sha256, citation, trust_state, "
                            "text, chunk_hash"
                            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
                        ),
                        (
                            chunk.id,
                            chunk.concept_id,
                            chunk.ordinal,
                            chunk.source_sha256,
                            json.dumps(chunk.citation, sort_keys=True),
                            str(meta.get("status", "unverified")),
                            chunk.text,
                            chunk_hash,
                        ),
                    )
                    rowid = connection.execute(
                        "SELECT rowid FROM chunk WHERE id=?", (chunk.id,)
                    ).fetchone()[0]
                    connection.execute(
                        "INSERT INTO chunk_fts(rowid, text) VALUES (?, ?)", (rowid, chunk.text)
                    )
                    for tag in meta.get("tags") or []:
                        tag = str(tag)
                        connection.execute("INSERT OR IGNORE INTO tag VALUES (?)", (tag,))
                        connection.execute(
                            "INSERT OR IGNORE INTO chunk_tag VALUES (?, ?)", (chunk.id, tag)
                        )
                connection.execute(
                    "INSERT INTO build VALUES (1, ?, ?)", (len(chunks), digest.hexdigest())
                )
            if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise ValueError("INDEX_BUILD_FAILED: integrity check failed")
        finally:
            connection.close()
        os.replace(temporary, target)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return target


def update_index(bundle_root: Path) -> Path:
    """Transactionally reconcile changed cited chunks into an existing index."""
    chunks = read_chunks(bundle_root)
    if not chunks:
        chunks = rebuild_chunks(bundle_root)
    concepts = _concepts(bundle_root)
    missing = sorted({chunk.concept_id for chunk in chunks if chunk.concept_id not in concepts})
    if missing:
        raise ValueError(
            f"INDEX_BUILD_FAILED: chunks reference missing concepts: {', '.join(missing)}"
        )

    target = index_path(bundle_root)
    if not target.exists():
        return rebuild_index(bundle_root)

    rendered_chunks = {chunk.id: (chunk, str(chunk.to_dict())) for chunk in chunks}
    digest = hashlib.sha256()
    for _chunk, rendered in rendered_chunks.values():
        digest.update(rendered.encode())

    with closing(sqlite3.connect(target)) as connection:
        schema = connection.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
        if schema != (INDEX_SCHEMA_VERSION,):
            return rebuild_index(bundle_root)

        connection.row_factory = sqlite3.Row
        existing = {
            row["id"]: row
            for row in connection.execute(
                "SELECT id, chunk_hash, rowid, text, trust_state FROM chunk"
            ).fetchall()
        }
        changed = {
            chunk_id
            for chunk_id, (_chunk, rendered) in rendered_chunks.items()
            if chunk_id not in existing
            or existing[chunk_id]["chunk_hash"] != hashlib.sha256(rendered.encode()).hexdigest()
        }
        removed = set(existing) - set(rendered_chunks)
        trust_state_changed = {
            chunk_id
            for chunk_id, (chunk, _rendered) in rendered_chunks.items()
            if chunk_id not in changed
            and existing[chunk_id]["trust_state"]
            != str(concepts[chunk.concept_id].get("status", "unverified"))
        }

        with connection:
            for path, meta in sorted(concepts.items()):
                source = (meta.get("sources") or [{}])[0]
                sha = str(source.get("sha256", "")) if isinstance(source, dict) else ""
                connection.execute(
                    """
                    INSERT INTO concept(path, type, status, source_sha256, title)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(path) DO UPDATE SET
                        type=excluded.type,
                        status=excluded.status,
                        source_sha256=excluded.source_sha256,
                        title=excluded.title
                    """,
                    (
                        path,
                        str(meta.get("type", "")),
                        str(meta.get("status", "unverified")),
                        sha,
                        str(meta.get("title", path)),
                    ),
                )
            for (path,) in connection.execute("SELECT path FROM concept").fetchall():
                if path not in concepts:
                    connection.execute("DELETE FROM concept WHERE path=?", (path,))

            for chunk_id in sorted(trust_state_changed):
                chunk, _rendered = rendered_chunks[chunk_id]
                connection.execute(
                    "UPDATE chunk SET trust_state=? WHERE id=?",
                    (str(concepts[chunk.concept_id].get("status", "unverified")), chunk_id),
                )

            for chunk_id in sorted(changed | removed):
                current = existing.get(chunk_id)
                if current is None:
                    continue
                connection.execute(
                    "INSERT INTO chunk_fts(chunk_fts, rowid, text) VALUES ('delete', ?, ?)",
                    (current["rowid"], current["text"]),
                )
                connection.execute("DELETE FROM chunk_tag WHERE chunk_id=?", (chunk_id,))
                connection.execute("DELETE FROM chunk WHERE id=?", (chunk_id,))

            for chunk_id in sorted(changed):
                chunk, rendered = rendered_chunks[chunk_id]
                meta = concepts[chunk.concept_id]
                connection.execute(
                    """
                    INSERT INTO chunk(
                        id, concept_path, ordinal, source_sha256, citation, trust_state,
                        text, chunk_hash
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        chunk.id,
                        chunk.concept_id,
                        chunk.ordinal,
                        chunk.source_sha256,
                        json.dumps(chunk.citation, sort_keys=True),
                        str(meta.get("status", "unverified")),
                        chunk.text,
                        hashlib.sha256(rendered.encode()).hexdigest(),
                    ),
                )
                rowid = connection.execute(
                    "SELECT rowid FROM chunk WHERE id=?", (chunk.id,)
                ).fetchone()[0]
                connection.execute(
                    "INSERT INTO chunk_fts(rowid, text) VALUES (?, ?)", (rowid, chunk.text)
                )

            for chunk_id, (chunk, _rendered) in rendered_chunks.items():
                connection.execute("DELETE FROM chunk_tag WHERE chunk_id=?", (chunk_id,))
                for tag in concepts[chunk.concept_id].get("tags") or []:
                    tag = str(tag)
                    connection.execute("INSERT OR IGNORE INTO tag VALUES (?)", (tag,))
                    connection.execute("INSERT INTO chunk_tag VALUES (?, ?)", (chunk_id, tag))
            connection.execute(
                "DELETE FROM tag WHERE name NOT IN (SELECT DISTINCT tag FROM chunk_tag)"
            )
            connection.execute(
                """
                INSERT INTO build VALUES (1, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    chunk_count=excluded.chunk_count,
                    input_hash=excluded.input_hash
                """,
                (len(chunks), digest.hexdigest()),
            )
            if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise ValueError("INDEX_BUILD_FAILED: integrity check failed")
    return target
