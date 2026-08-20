from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

from headcleaner.chunking import Chunk, write_chunks


def _bundle(tmp_path: Path) -> Path:
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    (bundle / "alpha.md").write_text(
        "---\ntype: Document\ntitle: Alpha\ntags: [guide, api]\nstatus: unverified\n"
        "sources: [{uri: file:///alpha.txt, sha256: '" + "a" * 64 + "'}]\n---\nAlpha body",
        encoding="utf-8",
    )
    (bundle / "beta.md").write_text(
        "---\ntype: Note\ntitle: Beta\ntags: [guide]\nstatus: unverified\n"
        "sources: [{uri: file:///beta.txt, sha256: '" + "b" * 64 + "'}]\n---\nBeta body",
        encoding="utf-8",
    )
    write_chunks(
        bundle,
        [
            Chunk(
                "1" * 64,
                "alpha.md",
                "a" * 64,
                ("element-a",),
                0,
                (),
                "alpha retrieval phrase",
                {
                    "source_uri": "file:///alpha.txt",
                    "source_sha256": "a" * 64,
                    "page": 1,
                    "start": 0,
                    "end": 21,
                },
                5,
            ),
            Chunk(
                "2" * 64,
                "beta.md",
                "b" * 64,
                ("element-b",),
                0,
                (),
                "beta retrieval phrase",
                {
                    "source_uri": "file:///beta.txt",
                    "source_sha256": "b" * 64,
                    "page": 1,
                    "start": 0,
                    "end": 20,
                },
                5,
            ),
        ],
    )
    return bundle


def test_rebuild_index_is_idempotent_and_bundle_relative(tmp_path: Path) -> None:
    from headcleaner.index import index_path, rebuild_index

    bundle = _bundle(tmp_path)
    first = rebuild_index(bundle)
    second = rebuild_index(bundle)

    assert first == second == index_path(bundle)
    assert first.exists()
    assert str(tmp_path.resolve()) not in first.read_bytes().decode("latin1", errors="ignore")


def test_update_index_rebuilds_atomically_after_chunk_change(tmp_path: Path) -> None:
    from headcleaner.chunking import Chunk, write_chunks
    from headcleaner.index import rebuild_index, update_index

    bundle = _bundle(tmp_path)
    rebuild_index(bundle)
    write_chunks(
        bundle,
        [
            Chunk(
                "2" * 64,
                "alpha.md",
                "a" * 64,
                ("element-b",),
                1,
                (),
                "replacement retrieval phrase",
                {
                    "source_uri": "file:///alpha.txt",
                    "source_sha256": "a" * 64,
                    "page": 1,
                    "start": 0,
                    "end": 26,
                },
                4,
            )
        ],
    )

    path = update_index(bundle)

    assert path.exists()


def test_update_index_reconciles_only_changed_and_deleted_chunks(tmp_path: Path) -> None:
    """An update retains untouched SQLite rows while reconciling changed chunks."""
    from headcleaner.chunking import Chunk, write_chunks
    from headcleaner.index import rebuild_index, update_index
    from headcleaner.search import search

    bundle = _bundle(tmp_path)
    database = rebuild_index(bundle)
    with closing(sqlite3.connect(database)) as connection:
        untouched_rowid = connection.execute(
            "SELECT rowid FROM chunk WHERE id=?", ("1" * 64,)
        ).fetchone()[0]

    write_chunks(
        bundle,
        [
            Chunk(
                "1" * 64,
                "alpha.md",
                "a" * 64,
                ("element-a",),
                0,
                (),
                "alpha retrieval phrase",
                {
                    "source_uri": "file:///alpha.txt",
                    "source_sha256": "a" * 64,
                    "page": 1,
                    "start": 0,
                    "end": 21,
                },
                5,
            ),
            Chunk(
                "3" * 64,
                "beta.md",
                "b" * 64,
                ("element-c",),
                1,
                (),
                "replacement retrieval phrase",
                {
                    "source_uri": "file:///beta.txt",
                    "source_sha256": "b" * 64,
                    "page": 1,
                    "start": 0,
                    "end": 28,
                },
                4,
            ),
        ],
    )

    with closing(sqlite3.connect(database)) as reader:
        assert reader.execute("SELECT COUNT(*) FROM chunk").fetchone()[0] == 2
        update_index(bundle)

    with closing(sqlite3.connect(database)) as connection:
        assert (
            connection.execute("SELECT rowid FROM chunk WHERE id=?", ("1" * 64,)).fetchone()[0]
            == untouched_rowid
        )
        assert connection.execute("SELECT 1 FROM chunk WHERE id=?", ("2" * 64,)).fetchone() is None
        assert (
            connection.execute("SELECT 1 FROM chunk WHERE id=?", ("3" * 64,)).fetchone() is not None
        )

    assert [result.chunk_id for result in search(bundle, "replacement")] == ["3" * 64]


def test_update_index_refreshes_unchanged_chunk_trust_state_in_place(tmp_path: Path) -> None:
    """Concept-status updates preserve the FTS row while refreshing indexed trust metadata."""
    from headcleaner.index import rebuild_index, update_index

    bundle = _bundle(tmp_path)
    database = rebuild_index(bundle)
    with closing(sqlite3.connect(database)) as connection:
        original_rowid = connection.execute(
            "SELECT rowid FROM chunk WHERE id=?", ("1" * 64,)
        ).fetchone()[0]

    alpha = bundle / "alpha.md"
    alpha.write_text(
        alpha.read_text(encoding="utf-8").replace("status: unverified", "status: reviewed"),
        encoding="utf-8",
    )

    update_index(bundle)

    with closing(sqlite3.connect(database)) as connection:
        rowid, trust_state = connection.execute(
            "SELECT rowid, trust_state FROM chunk WHERE id=?", ("1" * 64,)
        ).fetchone()
    assert rowid == original_rowid
    assert trust_state == "reviewed"
