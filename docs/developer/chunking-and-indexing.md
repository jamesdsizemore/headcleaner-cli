# Chunking and indexing

This page documents the chunking algorithm, the local SQLite search index, and the shared search API. It is the developer reference for the Phase 2 contracts that make headcleaner output searchable.

## The chunking algorithm

The chunker lives in `src/headcleaner/chunking.py`. The entry point is `chunk_elements`, which takes an ordered iterable of typed elements plus the concept identity and returns a list of `Chunk` objects.

### The rule

The algorithm walks the elements in ordinal order. It maintains a current buffer and a heading path. It closes the current chunk at:

- A heading boundary (heading elements trigger a flush).
- A size boundary (when the current buffer plus the next element would exceed `max_chars`, default 2000).
- After a complete table or code element (these are indivisible).

If a single element exceeds the size boundary, it is emitted whole with `oversize: true`. Source evidence is never truncated.

The heading path is carried forward across chunks. Each chunk's `heading_path` records the sequence of headings from the document root to the chunk's position.

### Stable IDs

The chunk ID is a SHA-256 digest of `source_sha256 + element_ids + ordinal + chunking_version`. The chunking version is `"1"` in the current implementation. Changing the algorithm increments the version, which makes downstream tools able to detect that the same source produces different chunks.

### Citations

Every chunk carries a `citation` dict with `source_uri`, `source_sha256`, `page`, `start`, and `end`. The validator is in `Chunk.__post_init__` rejects any chunk whose citation is missing keys or whose `source_sha256` does not match the chunk's `source_sha256`.

### Emission

`write_chunks` atomically writes `chunks.jsonl` to the bundle root. The write goes through a temporary file plus `os.replace` so a crash mid-write does not corrupt the previous file. `read_chunks` reads the file back into `Chunk` objects with full validation.

### Rebuild from canonical output

`rebuild_chunks` walks the OKF bundle, parses each concept's Markdown body, derives typed elements, and produces the same chunks `chunk_elements` would produce. The output is byte-stable across reruns. The implementation reads concepts only; it never reads source files, so the rebuild is safe to run on a bundle that has been moved.

## The search index

The search index lives in `src/headcleaner/index.py`. It is a SQLite database at `<bundle>/.headcleaner/index.sqlite3`.

### Schema

The schema is stored in `meta` with version `"1"`. The tables are:

- `concept` — one row per concept, with `path`, `type`, `status`, `source_sha256`, `title`.
- `chunk` — one row per chunk, with `id`, `concept_path`, `ordinal`, `source_sha256`, `citation`, `trust_state`, `text`, `chunk_hash`.
- `chunk_fts` — FTS5 virtual table over `chunk.text`, with `content='chunk'` and `content_rowid='rowid'`.
- `tag` — one row per unique tag.
- `chunk_tag` — many-to-many between chunks and tags.
- `build` — single-row metadata: chunk count and input digest.

### Build semantics

`rebuild_index` reads the chunks and concepts, validates them, writes a new SQLite database in a temporary file, runs `PRAGMA integrity_check`, and atomically replaces the previous database. The previous database is preserved on failure.

`update_index` reconciles an existing compatible database in one SQLite transaction. It hashes the current serialized chunks, removes rows for deleted chunks, and deletes/reinserts only rows whose chunk hash changed. Unchanged chunks keep their SQLite/FTS row identity. Concept metadata is upserted, tag mappings are refreshed, and a trust-state-only change updates the existing chunk row in place without replacing its FTS row. The command updates the build digest and runs `PRAGMA integrity_check` before commit. If the index is missing or its schema version is incompatible, `update_index` safely falls back to `rebuild_index`.

### Failure modes

A failed rebuild preserves the previous database and reports `INDEX_BUILD_FAILED`. The most common failure is a chunk whose concept does not exist in the bundle; the error message names the missing concept. Other failures include integrity check failures and unwritable output directories.

## The shared search API

The search API lives in `src/headcleaner/search.py`. It is the single function the CLI, the HTTP server, and the MCP server all call.

```python
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
) -> list[SearchHit]: ...
```

### Ranking

Ranking is `bm25(chunk_fts)` with a deterministic tie-break on `(concept_path, ordinal)`. Two equivalent queries always return hits in identical order. The deterministic tie-break is what makes the results reproducible across surfaces.

### Filters

The five filters (`tag`, `type`, `status`, `path`, `source_sha`) all intersect with each other and with the FTS5 query. Filters are passed as parameterized SQL; the query string itself is passed through FTS5 MATCH syntax, not interpolated.

### Error handling

Invalid FTS5 syntax (unterminated phrases, malformed operators) raises `SearchQueryError`. The CLI, HTTP server, and MCP server all catch this and return a user-facing error. Empty queries return an empty result list.

### Connection lifecycle

The read connection is wrapped in `contextlib.closing` so it is closed on Windows where the SQLite context manager commits but does not close.

## What to read next

The [canonical model developer guide](canonical-model.md) documents the `Chunk` and `SearchHit` data shapes. The [embeddings and vectors developer guide](embeddings-and-vectors.md) covers the embedding layer that can be added on top of the search index. The [architecture developer guide](architecture.md) explains how the chunking and indexing modules fit into the larger pipeline.