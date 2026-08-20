# CLI reference

This page documents every command headcleaner ships. It is organized by what each command does for you, not by which source module implements it. Each command entry covers the same set of facts: purpose, when to use it, basic command form, useful options, what it checks, possible results, mutability, optional tools, and related commands.

The page starts with a decision tree that points you to the right command, then documents each command in alphabetical order.

## Which command should I run?

The decision tree below is the fastest way to find the right command for what you want to do.

```text
Do you want to convert a folder of documents into Markdown or OKF?
├── Yes -> headcleaner convert
└── No, I want to work with an already-converted bundle
    ├── Build the search index -> headcleaner index rebuild
    ├── Update the index incrementally -> headcleaner index update
    ├── Search the index -> headcleaner search
    ├── Embed chunks for semantic search -> headcleaner index embed
    ├── Build the knowledge graph -> headcleaner graph
    ├── Find duplicate documents -> headcleaner dedupe
    ├── Find claim candidates and stale findings -> headcleaner claims
    ├── Compare two bundles or files -> headcleaner diff
    └── Preview rename/deletion-safe sync -> headcleaner sync

Do you want to run headcleaner as a service for an AI assistant or HTTP client?
├── Yes, MCP server -> headcleaner mcp
└── Yes, local HTTP server -> headcleaner serve

Do you want to validate or test something?
├── Validate a policy file -> headcleaner policy test
├── Check your environment -> headcleaner doctor
└── Measure conversion quality on fixtures -> headcleaner benchmark
```

## convert

Purpose: convert a folder of source documents into Markdown and/or OKF bundle output.

When to use it: every time you want headcleaner to read a folder and produce clean output. This is the command you will run most often.

Basic command:

```bash
uv run --no-sync --python 3.13 headcleaner convert INPUT OUTPUT
```

`INPUT` is the folder of source documents. `OUTPUT` is the folder where the converted bundle, manifest, and report will be written.

Useful options:

- `--format md|okf|both` — what to emit. Default is `both`, which produces both the `_md/` tree and the `okf/` bundle.
- `--include GLOB` / `--exclude GLOB` — restrict which files are converted. Glob patterns are matched against relative paths.
- `--ocr` — enable OCR for scanned PDFs.
- `--ocr-lang en,deu,fra` — Tesseract language codes for OCR. Default is `eng`.
- `--ocr-profile fast|balanced|archival` — which OCR profile to use. Default is `balanced`.
- `--no-cache` — force re-extraction of every file even if the source hash matches the cache.
- `--no-fallback` — refuse to fall back to a different engine if the first one fails.
- `--engine NAME` — pin the engine for files whose extension matches. Useful for testing.
- `--allow-network` — permit network calls for engines or features that need them. Required for remote embedding and remote vector databases.
- `--jobs N` — number of files to process in parallel. Default is 1.
- `--quiet` — suppress per-file progress lines.
- `--json` — emit structured events on stdout instead of human-readable lines.

What it checks: every file under `INPUT` that matches an `--include` pattern and does not match an `--exclude` pattern. Files are routed to the appropriate adapter based on extension.

Possible results: `ok`, `warn`, `skipped`, `failed`, `error` per file. The complete semantics are in the [Understanding results](../user-guide/understanding-results.md) page. The run exits with code 0 if no `failed` or `error` results occurred, 1 if any `failed`, and 2 if any `error`.

Mutability: writes only to `OUTPUT`. Never modifies `INPUT`.

Optional tools: depends on the input formats. OfficeCLI for Office files, LibreOffice for legacy Office, Tesseract for scanned PDFs, readpst for `.pst` archives, and so on. See the [engine directory](engine-directory.md).

Related commands: `lint` (review the converted output), `index rebuild` (build the search index over the result), `benchmark` (measure conversion quality on fixtures).

## index

Purpose: subcommand group for managing the local SQLite search index.

Subcommands:

- `index rebuild BUNDLE` — atomically rebuild the search index from the chunks in `okf/chunks.jsonl`.
- `index update BUNDLE` — transactionally reconcile the index: remove deleted chunk rows, replace changed chunk rows, and refresh concept metadata while preserving unchanged FTS rows.
- `index embed BUNDLE` — compute embeddings for every chunk using a configured embedding provider, cache the result, optionally upload to a remote vector database.

### index rebuild

Basic command:

```bash
uv run --no-sync --python 3.13 headcleaner index rebuild BUNDLE
```

`BUNDLE` is the OKF bundle directory, typically `<output>/okf`.

What it checks: validates every chunk in `chunks.jsonl`, builds a new SQLite database in a temporary file, runs an integrity check, and atomically replaces the previous database.

Possible results: exits 0 on success, 1 if chunk validation fails (`INDEX_BUILD_FAILED`), 2 if the database file is unwritable.

Mutability: writes only to `<bundle>/.headcleaner/index.sqlite3`. The previous index is preserved if the rebuild fails.

Related commands: `index update` (incremental), `search` (query the rebuilt index).

### index update

Use this when a bundle already has an index and only part of its chunk or concept state has changed. The command reconciles the compatible SQLite index in one transaction: removed chunks are deleted, changed chunks are replaced, concept tags are refreshed, and trust-state-only changes are updated in place. Unchanged chunk and FTS rows remain in place. If the index is absent or has an incompatible schema, the command safely performs the same atomic build used by `index rebuild`.

### index embed

Basic command:

```bash
uv run --no-sync --python 3.13 headcleaner index embed BUNDLE --provider NAME --model MODEL
```

Required flags: `--provider` selects the embedding provider; `--model` selects the model identifier within that provider.

Useful options:

- `--allow-network` — required for the HTTP embedding provider.
- `--timeout SECONDS` — HTTP request timeout. Default 30.
- `--qdrant-endpoint URL` — also upload embeddings to a Qdrant collection at this endpoint.
- `--qdrant-collection NAME` — collection name to use. Default is `headcleaner`.
- `--recreate-qdrant-collection` — recreate the remote collection if its dimension or model_id differs from the current provider.

What it checks: for every chunk, computes an embedding if not cached, caches it locally, optionally uploads to Qdrant, then prunes orphan vectors (cached vectors whose chunk is no longer in the index).

Possible results: exits 0 on success. Exits 1 if the provider is unknown, the model is unavailable, the Qdrant endpoint is unreachable, or the chunk count is zero. Exits 2 if `--qdrant-endpoint` was passed without `--allow-network`.

Mutability: writes to the local cache and optionally to the remote vector database. Never modifies the bundle.

Related commands: `search` (use the embeddings implicitly when ranking is enabled).

## search

Purpose: query the local search index with deterministic FTS5 ranking and optional filters.

Basic command:

```bash
uv run --no-sync --python 3.13 headcleaner search QUERY --bundle BUNDLE
```

Useful options:

- `--tag TAG` — restrict to chunks tagged with this tag.
- `--type TYPE` — restrict to concepts of this type.
- `--status STATUS` — restrict to chunks with this trust status.
- `--path PREFIX` — restrict to concepts whose path starts with this prefix.
- `--source-sha SHA` — restrict to chunks from this specific source file.
- `--limit N` — maximum number of results. Default 20.
- `--json` — emit structured JSON instead of human-readable lines.

What it checks: queries the `chunk_fts` FTS5 virtual table, joined against `chunk` and `concept` for the filter fields. Ranking is `bm25(chunk_fts)` with a deterministic tie-break on `concept_path` then `ordinal`.

Possible results: exits 0 if the query succeeds (including when there are no matches). Exits 1 if the query syntax is invalid (e.g. unterminated phrase), 2 if the index does not exist.

Mutability: none. The index is read-only.

Related commands: `index rebuild` (build the index), `index embed` (add semantic ranking).

## graph

Purpose: build or query the knowledge graph for a bundle.

Basic command:

```bash
uv run --no-sync --python 3.13 headcleaner graph BUNDLE [--node NODE] [--depth N] [--kind KIND] [--policy POLICY]
```

Useful options:

- `--node NODE` — query the graph starting from this node. Without `--node`, the command prints the full graph summary.
- `--depth N` — traversal depth for `--node` queries. Default 1.
- `--kind KIND` — restrict returned edges to this kind. Allowed values: `contains`, `cites`, `mentions`, `related_to`, `duplicate_candidate`, `conflicts_candidate`.
- `--policy POLICY` — apply an edge-kind exclusion policy from this TOML file.
- `--json` — emit structured JSON instead of a one-line summary.

What it checks: reads the chunks and concepts from the bundle, builds the graph deterministically, and (when `--node` is given) walks the graph from the given node to the given depth.

Possible results: exits 0 if the build and query succeed. Exits 1 if the bundle is malformed or the policy file is invalid.

Mutability: writes `graph.jsonl` to the bundle. Does not modify canonical output.

Related commands: `dedupe` (uses the graph's duplicate-candidate edges), `claims` (links its claim candidates into the graph).

## dedupe

Purpose: find exact and near-duplicate document candidates within a bundle.

Basic command:

```bash
uv run --no-sync --python 3.13 headcleaner dedupe BUNDLE [--threshold FLOAT] [--json]
```

Useful options:

- `--threshold FLOAT` — minimum combined similarity score for a pair to be reported. Default 0.8. Must be in `[0, 1]`.
- `--json` — emit structured JSON instead of a one-line summary.

What it checks: groups documents by source SHA for exact duplicates, then computes title/content/path similarity for every distinct pair. Pairs whose combined score exceeds the threshold are reported as candidates.

Possible results: exits 0 always. The result is a list of `DocumentFamily` records. Exact duplicates have non-empty `exact_members`; near-duplicates have entries in `candidate_members`.

Mutability: none. The command is read-only.

Related commands: `graph` (uses the dedupe result for duplicate-candidate edges), `diff` (compares two specific documents).

## claims

Purpose: extract claim candidates from chunks and emit stale/conflict findings.

Basic command:

```bash
uv run --no-sync --python 3.13 headcleaner claims BUNDLE [--policy POLICY] [--json]
```

Useful options:

- `--policy POLICY` — apply this policy file's `[claims]` section (suppressions and scope).
- `--json` — emit structured JSON instead of a one-line summary.

What it checks: extracts dated, monetary, ownership, and status-label claims from the chunks, pairs them by kind and scope, and emits `potential_conflict` findings for pairs with unequal values. Stale findings are derived from per-source `stale_after` dates when the policy provides them, falling back to a single legacy global date.

Possible results: exits 0 always. The result is a list of claim candidates and findings, each with its citation and rule_id.

Mutability: none. The command is read-only.

Related commands: `graph` (links claim candidates as `related_to` topic nodes), `dedupe` (uses the same chunk corpus).

## diff

Purpose: compare two Markdown files or two bundles element by element.

Basic command:

```bash
uv run --no-sync --python 3.13 headcleaner diff LEFT RIGHT [--format text|json|md] [--include-unchanged]
```

Useful options:

- `--format text|json|md` — output format. `text` is the default and is a short summary. `json` is the full structured diff. `md` is a Markdown report.
- `--include-unchanged` — include unchanged elements in the diff. Default is to omit them.

What it checks: parses each side as Markdown with frontmatter, normalizes them, aligns element IDs, and classifies each element as `added`, `removed`, `modified`, `moved`, or `unchanged`. Frontmatter and trust-family changes are surfaced as separate `frontmatter` kind changes.

Possible results: exits 0 always. The diff result is reported regardless of whether anything changed.

Mutability: none. The command is read-only.

Related commands: `graph` (compare graphs), `sync` (compare source directories).

## sync

Purpose: rename/deletion-safe source-to-output synchronization.

Basic command:

```bash
uv run --no-sync --python 3.13 headcleaner sync INPUT OUTPUT [--dry-run] [--apply] [--prune-generated] [--json]
```

Useful options:

- `--dry-run` — default. Report what would change without modifying anything.
- `--apply` — apply the plan. Mandatory for any write or delete.
- `--prune-generated` — with `--apply`, remove generated files that no longer correspond to a known source.
- `--json` — emit structured JSON instead of human-readable lines.

What it checks: matches each source file by SHA against the durable sync state, classifies the result as `unchanged`, `renamed`, or `deleted_candidate`, and (with `--prune-generated`) verifies that every file marked for deletion is a known generated file whose hash matches the recorded output hash.

Possible results: exits 0 if the plan is well-formed and the dry-run completes. Exits 1 if any file marked for deletion has been modified since the last sync (a `SYNC_CONFLICT`), if the sync state is corrupt (`SYNC_STATE_CORRUPT`), or if `--apply` is passed without an explicit decision.

Mutability: with `--apply`, writes to the durable sync state file at `<output>/.headcleaner/sync.json`. With `--prune-generated`, deletes generated files that match the recorded hash. Without `--apply`, the command is read-only.

Related commands: `watch` (the watcher invokes sync in dry-run planning mode).

## mcp

Purpose: start the MCP server over stdio for a compatible AI coding assistant.

Basic command:

```bash
uv run --no-sync --python 3.13 headcleaner mcp
```

The command does not take arguments because all configuration is done by the MCP client. The client decides when to start and stop the server.

What it checks: each tool call validates its arguments against the tool's schema and runs the underlying implementation (search, graph, diff, context, etc.).

Possible results: the server responds to each tool call with a JSON-RPC response. Tool errors are reported with structured error codes; the server itself does not exit on tool errors.

Mutability: read-only. The MCP server exposes no tool that writes to the bundle, the index, or any other state.

Related commands: `serve` (the HTTP server exposes a different subset of the same functionality).

## serve

Purpose: start the local HTTP server that exposes the search API.

Basic command:

```bash
uv run --no-sync --python 3.13 headcleaner serve --bundle BUNDLE --host HOST --port PORT
```

Useful options:

- `--host HOST` — bind host. Default `127.0.0.1` (loopback only).
- `--port PORT` — bind port. Default `8765`.
- `--reload` — auto-reload on source changes (development only).

What it checks: each HTTP request validates its query parameters and runs the underlying search implementation.

Possible results: the server runs until interrupted. Each request returns a JSON response or a structured error.

Mutability: read-only. The HTTP server exposes no endpoint that writes to the bundle.

Related commands: `mcp` (the MCP server exposes a different subset of the same functionality), `search` (the CLI counterpart).

## lint

Purpose: review converted Markdown and OKF for formatting issues.

Basic command:

```bash
uv run --no-sync --python 3.13 headcleaner lint BUNDLE [--strict] [--no-color]
```

Useful options:

- `--strict` — treat warnings as errors.
- `--no-color` — disable ANSI color output.

What it checks: frontmatter shape, citation completeness, link integrity, body formatting, and the lint rules defined in your policy file.

Possible results: exits 0 if no findings, 1 if any error findings, 2 if warnings exist and `--strict` is set.

Mutability: none. The command is read-only.

Related commands: `policy test` (broader policy evaluation), `convert` (the source of the output being linted).

## policy

Purpose: evaluate a policy file against a bundle.

Subcommands:

- `policy test BUNDLE --pack PACK` — evaluate the given pack's rules against the bundle.
- `policy explain --pack PACK --rule RULE` — explain a specific rule's condition and effect.

### policy test

Basic command:

```bash
uv run --no-sync --python 3.13 headcleaner policy test BUNDLE --pack PACK
```

What it checks: every rule in the pack, against every concept in the bundle. Findings are reported with severity `info`, `warning`, or `error`.

Possible results: exits 0 if no error findings, 1 if any error finding, 2 if the pack itself is invalid (missing required fields, unknown rule kinds, etc.).

Mutability: none. The command is read-only.

Related commands: `lint` (per-file linting), `claims` (policy-aware claim extraction).

## doctor

Purpose: print a diagnostic report of the headcleaner environment.

Basic command:

```bash
uv run --no-sync --python 3.13 headcleaner doctor
```

What it checks: Python version, `uv` presence, headcleaner version, OfficeCLI presence and version, LibreOffice presence and version, Tesseract presence and version, `readpst` presence, output directory writability.

Possible results: exits 0 if all required tools are present and reachable, 1 if any required tool is missing, 2 if a tool is present but reports an error.

Mutability: none. The command is read-only.

Related commands: `convert` (which calls doctor-like checks internally), `benchmark` (which validates its own fixtures).

## benchmark

Purpose: measure conversion quality against attributed fixtures.

Basic command:

```bash
uv run --no-sync --python 3.13 headcleaner benchmark FIXTURES [--baseline PATH] [--json] [--update-baseline]
```

Useful options:

- `--baseline PATH` — compare against a baseline file. Default compares against the checked-in baseline.
- `--json` — emit structured JSON.
- `--update-baseline` — update the baseline after an explicit review. Requires `--baseline PATH`.

What it checks: per-fixture text anchor recall, heading order preservation, table anchor recall, output file existence. Each fixture has an `expectations.json` that declares the required anchors and warnings.

Possible results: exits 0 if all fixtures pass, 1 if any fixture fails. With `--update-baseline`, exits 0 after writing the updated baseline.

Mutability: none against the fixtures. With `--update-baseline`, writes to the baseline file.

Related commands: `convert` (the operation being benchmarked), `doctor` (which validates the environment the benchmark depends on).