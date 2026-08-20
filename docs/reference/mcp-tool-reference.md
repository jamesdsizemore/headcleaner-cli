# MCP tool reference

This page documents every tool the headcleaner MCP server exposes. Each tool entry covers the same set of facts: what the tool does, its parameters, what it returns, the schema version, and the safety properties.

The MCP server speaks the standard Model Context Protocol over stdio. The client (your AI coding assistant) starts the server as a subprocess, sends JSON-RPC requests, and receives JSON-RPC responses. The server is read-only: no tool modifies the bundle, the index, or any other state.

## The tools

The server exposes the following tools. The names are stable and additive; new tools will be added without renaming or removing existing ones.

### `okf_search`

Purpose: search the local index for chunks matching a query.

Parameters:

- `query` (string, required) — the FTS5 query string. Quoted phrases and FTS5 operators are supported.
- `bundle` (string, required) — path to the OKF bundle.
- `tag` (string, optional) — restrict to chunks tagged with this tag.
- `type` (string, optional) — restrict to concepts of this type.
- `status` (string, optional) — restrict to chunks with this trust status.
- `path` (string, optional) — restrict to concepts whose path starts with this prefix.
- `source_sha` (string, optional) — restrict to chunks from a specific source file.
- `limit` (integer, optional, default 20) — maximum number of results.

Returns: a JSON object with `hits` (a list of cited search results) and `schema_version`. Each hit has `chunk_id`, `concept_path`, `ordinal`, `rank`, `excerpt`, `citation`, `trust_state`, and `index_schema_version`.

Safety: read-only.

### `okf_impact`

Purpose: explore the knowledge graph starting from a given node.

Parameters:

- `bundle` (string, required) — path to the OKF bundle.
- `node` (string, required) — the starting node ID.
- `depth` (integer, optional, default 1) — how many hops to traverse.
- `kind` (string, optional) — restrict returned edges to this kind.

Returns: a JSON object with `nodes` and `edges` for the subgraph reachable from the given node at the given depth. Each edge has `id`, `kind`, `from_id`, `to_id`, `evidence_chunk_ids`, `method`, and `status`.

Safety: read-only.

### `okf_diff`

Purpose: compare two Markdown files or two bundles element-by-element.

Parameters:

- `left` (string, required) — path to the left side.
- `right` (string, required) — path to the right side.
- `include_unchanged` (boolean, optional, default false) — include unchanged elements.

Returns: a JSON object with `left_ref`, `right_ref`, `summary`, `changes`, and `algorithm_version`. Each change has `kind`, `status`, `left_element_id`, `right_element_id`, `before`, `after`, and `citation`.

Safety: read-only.

### `okf_context`

Purpose: assemble a small cited context package around a topic or a chunk ID.

Parameters:

- `bundle` (string, required) — path to the OKF bundle.
- `query` (string, required) — the search query or topic.
- `max_bytes` (integer, optional, default 50000) — maximum total bytes.
- `format` (string, optional, default `md`) — `md` or `jsonl`.
- `include_ids` (array of strings, optional) — explicit chunk IDs to include.

Returns: a JSON object with `pack_id`, `query`, `included` (list of cited chunks), `omitted` (list of {chunk_id, reason}), `byte_budget`, `token_estimate`, and `manifest`. The `manifest` field contains the bundle, concept, source URI/hash, location, trust state, review state, and schema version for every included chunk.

Safety: read-only.

### `okf_chunks`

Purpose: list chunks for a bundle, with optional filters.

Parameters:

- `bundle` (string, required) — path to the OKF bundle.
- `concept_path` (string, optional) — restrict to chunks belonging to this concept.
- `source_sha` (string, optional) — restrict to chunks from this specific source file.
- `limit` (integer, optional, default 100) — maximum number of chunks to return.

Returns: a JSON object with `chunks` (a list of cited chunk objects) and `schema_version`. Each chunk has `id`, `concept_id`, `source_sha256`, `element_ids`, `ordinal`, `heading_path`, `text`, `citation`, `token_estimate`, `chunking_version`, and `oversize`.

Safety: read-only.

### `okf_concept`

Purpose: get the full content of a single concept.

Parameters:

- `bundle` (string, required) — path to the OKF bundle.
- `concept_id` (string, required) — the bundle-relative path of the concept (e.g. `notes.docx.md`).

Returns: a JSON object with the concept's body, frontmatter, source citation, and trust state.

Safety: read-only.

### `okf_manifest`

Purpose: get the run manifest for the bundle.

Parameters:

- `bundle` (string, required) — path to the OKF bundle.

Returns: a JSON object with the manifest contents.

Safety: read-only.

### `okf_report`

Purpose: get the run report for the bundle.

Parameters:

- `bundle` (string, required) — path to the OKF bundle.

Returns: the Markdown text of the run report.

Safety: read-only.

### `okf_diagnostics`

Purpose: get the diagnostics from the last run for a specific source file.

Parameters:

- `bundle` (string, required) — path to the OKF bundle.
- `relpath` (string, required) — the source file's relative path.

Returns: a JSON object with the diagnostics list and the per-file metrics.

Safety: read-only.

### `okf_claims`

Purpose: get the claim candidates and findings for the bundle.

Parameters:

- `bundle` (string, required) — path to the OKF bundle.
- `policy` (string, optional) — path to a policy file.

Returns: a JSON object with `claims` (a list of cited claim candidates) and `findings` (a list of cited findings, each with a rule_id and potential_conflict label where applicable).

Safety: read-only.

### `okf_dedupe`

Purpose: get the duplicate-family analysis for the bundle.

Parameters:

- `bundle` (string, required) — path to the OKF bundle.
- `threshold` (number, optional, default 0.8) — minimum combined similarity score.

Returns: a JSON object with `families` (a list of `DocumentFamily` records, each with `exact_members` and `candidate_members`) and `algorithm_version`.

Safety: read-only.

### `okf_graph`

Purpose: get the knowledge graph for the bundle.

Parameters:

- `bundle` (string, required) — path to the OKF bundle.
- `policy` (string, optional) — path to a policy file that may exclude edge kinds.

Returns: a JSON object with `nodes` and `edges`. Each node has `id`, `kind`, `label`, `source_refs`, and `attributes`. Each edge has `id`, `kind`, `from_id`, `to_id`, `evidence_chunk_ids`, `method`, and `status`.

Safety: read-only.

## Common response shape

Every tool that returns content returns it inside a JSON envelope:

```json
{
  "schema_version": "1",
  "tool": "okf_search",
  "ok": true,
  "data": { ... },
  "warnings": [],
  "errors": []
}
```

The `data` field carries the tool-specific payload. The `warnings` field carries non-fatal messages (such as "index not found, run index rebuild first"). The `errors` field carries structured error objects with `code`, `message`, and optional `details`.

When a tool call fails, the envelope's `ok` field is `false` and the `errors` field is non-empty. Clients should check `ok` before consuming `data`.

## What to read next

The [working with AI assistants](../user-guide/working-with-ai-agents.md) page introduces MCP without protocol jargon. The [MCP client setup](../integrations/mcp-client-setup.md) page has per-assistant configuration recipes. The [MCP development guide](../developer/mcp-development.md) covers how the server is implemented and how to add new tools.