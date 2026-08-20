# Serve API reference

This page documents every endpoint of the local HTTP server headcleaner ships. The server is intended for local use and binds to `127.0.0.1` by default. Do not bind it to a non-loopback interface without explicit authentication and authorization; the server is read-only and unauthenticated.

The server uses the same underlying search implementation as the CLI and the MCP server. The endpoint shapes are designed to be friendly to HTTP clients, including JSON consumers and curl-based scripts.

## Starting the server

The basic command is:

```bash
uv run --no-sync --python 3.13 headcleaner serve --bundle BUNDLE --host HOST --port PORT
```

The server runs until interrupted. There is no graceful shutdown flag; send SIGINT and it will close the listening socket and exit.

## Endpoints

The server exposes the following endpoints. All endpoints are GET unless otherwise noted. All endpoints return JSON unless otherwise noted.

### `GET /api/health`

Purpose: confirm the server is alive and the bundle is reachable.

Returns:

```json
{
  "status": "ok",
  "tool": "headcleaner",
  "version": "0.x.y",
  "bundle": "/abs/path/to/bundle",
  "schema_version": "1"
}
```

### `GET /api/search`

Purpose: search the local index with the same parameters as the CLI `search` command.

Query parameters:

- `q` (required) — the FTS5 query string.
- `tag` — restrict to chunks tagged with this tag.
- `type` — restrict to concepts of this type.
- `status` — restrict to chunks with this trust status.
- `path` — restrict to concepts whose path starts with this prefix.
- `source_sha` — restrict to chunks from a specific source file.
- `limit` — maximum number of results. Default 20.

Returns:

```json
{
  "query": "the phrase you searched for",
  "hits": [
    {
      "chunk_id": "...",
      "concept_path": "notes.docx.md",
      "ordinal": 0,
      "rank": -3.14,
      "excerpt": "...the phrase you searched for...",
      "citation": {
        "source_uri": "file:///path/to/notes.docx",
        "source_sha256": "aaa...",
        "page": null,
        "start": null,
        "end": null
      },
      "trust_state": "unverified",
      "index_schema_version": "1"
    }
  ],
  "schema_version": "1"
}
```

Errors: 400 if the query syntax is invalid; 404 if the index does not exist (with a `code: INDEX_NOT_FOUND` body); 500 on internal error.

### `GET /api/chunks`

Purpose: list chunks for the bundle, with optional filters.

Query parameters:

- `concept_path` — restrict to chunks belonging to this concept.
- `source_sha` — restrict to chunks from this specific source file.
- `limit` — maximum number of chunks. Default 100.

Returns:

```json
{
  "chunks": [
    {
      "id": "...",
      "concept_id": "notes.docx.md",
      "source_sha256": "aaa...",
      "element_ids": ["e1", "e2"],
      "ordinal": 0,
      "heading_path": ["Introduction"],
      "text": "...",
      "citation": { ... },
      "token_estimate": 12,
      "chunking_version": "1",
      "oversize": false
    }
  ],
  "schema_version": "1"
}
```

### `GET /api/concept/{concept_id}`

Purpose: get the full content of a single concept.

Path parameters:

- `concept_id` — the bundle-relative path of the concept (e.g. `notes.docx.md`).

Returns: a JSON object with the concept's body, frontmatter, source citation, and trust state.

Errors: 404 if the concept does not exist.

### `GET /api/graph`

Purpose: get the knowledge graph for the bundle.

Query parameters:

- `policy` (optional) — path to a policy file that may exclude edge kinds.

Returns: a JSON object with `nodes` and `edges`. Each node has `id`, `kind`, `label`, `source_refs`, and `attributes`. Each edge has `id`, `kind`, `from_id`, `to_id`, `evidence_chunk_ids`, `method`, and `status`.

### `GET /api/manifest`

Purpose: get the run manifest for the bundle.

Returns: a JSON object with the manifest contents.

### `GET /api/report`

Purpose: get the run report for the bundle.

Returns: a Markdown response (`text/markdown; charset=utf-8`) with the report text.

### `GET /api/claims`

Purpose: get the claim candidates and findings for the bundle.

Query parameters:

- `policy` (optional) — path to a policy file.

Returns: a JSON object with `claims` and `findings`.

### `GET /api/dedupe`

Purpose: get the duplicate-family analysis for the bundle.

Query parameters:

- `threshold` (optional, default 0.8) — minimum combined similarity score.

Returns: a JSON object with `families` and `algorithm_version`.

## Error envelope

When an endpoint returns an error, the response body is:

```json
{
  "code": "INDEX_NOT_FOUND",
  "message": "index does not exist; run headcleaner index rebuild",
  "details": {}
}
```

The HTTP status code is appropriate to the error (400 for malformed input, 404 for missing resource, 500 for internal error). The `code` field is stable across versions and is the right thing to switch on programmatically.

## Where to read next

The [CLI reference](cli-reference.md) shows the same functionality exposed through the CLI. The [chunking and indexing developer guide](../developer/chunking-and-indexing.md) explains the underlying search implementation.