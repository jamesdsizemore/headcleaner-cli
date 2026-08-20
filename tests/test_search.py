from __future__ import annotations

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


def test_search_filters_and_returns_citations(tmp_path: Path) -> None:
    from headcleaner.index import rebuild_index
    from headcleaner.search import search

    bundle = _bundle(tmp_path)
    rebuild_index(bundle)
    hits = search(bundle, "retrieval", tag="api", type="Document", source_sha="a" * 64)

    assert len(hits) == 1
    assert hits[0].concept_path == "alpha.md"
    assert hits[0].citation["source_sha256"] == "a" * 64


def test_search_rejects_malformed_fts_without_sql_interpolation(tmp_path: Path) -> None:
    from headcleaner.index import rebuild_index
    from headcleaner.search import SearchQueryError, search

    bundle = _bundle(tmp_path)
    rebuild_index(bundle)
    try:
        search(bundle, '"unterminated')
    except SearchQueryError as exc:
        assert "invalid search query" in str(exc)
    else:
        raise AssertionError("malformed FTS query was accepted")


def test_rebuild_after_index_deletion_preserves_deterministic_search_results(
    tmp_path: Path,
) -> None:
    from headcleaner.index import index_path, rebuild_index
    from headcleaner.search import search

    bundle = _bundle(tmp_path)
    rebuild_index(bundle)
    before = search(bundle, "retrieval")
    index_path(bundle).unlink()
    rebuild_index(bundle)
    after = search(bundle, "retrieval")

    assert after == before
