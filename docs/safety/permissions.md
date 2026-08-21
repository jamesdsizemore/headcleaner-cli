# Permissions

Every flag that affects headcleaner's safety guarantees lives on the command line and in policy files. This page is the single reference for every permission-related flag: what it does, what it permits, and what the default is.

The flags fall into four groups: network, write, slow operations, and override. Each group has its own default behavior and its own explicit opt-in.

## Network

Network-capable features never fire by default. They require `--allow-network` plus explicit destination configuration.

### `--allow-network`

What it permits: any network call. This is the master switch; without it, headcleaner refuses every request that would result in a network connection.

When you need it:

- Running `headcleaner index embed --provider openai_compatible_http --endpoint URL`. The HTTP provider uses the configured endpoint to compute embeddings; without `--allow-network`, the command fails before any request.
- Running `headcleaner index embed --qdrant-endpoint URL`. The Qdrant adapter connects to the configured endpoint to upsert vectors; without `--allow-network`, the command fails before any request.

When you do not need it:

- Local Sentence Transformers embedding. The model runs in-process; no network call is made.
- Local FTS5 search. SQLite is local.
- Local knowledge graph queries. No network.
- Local MCP server. The server speaks stdio; no network.

The flag is per-command. Passing `--allow-network` on `index embed` does not affect any other command.

## Write

Headcleaner writes only to the directories you explicitly name. There are three write paths: the conversion output directory, the search index file, and the sync state file.

### Conversion output

What it permits: writing to the directory you pass as the second argument to `headcleaner convert`. The directory is created if it does not exist; if it exists, files inside it may be overwritten.

Default: every `convert` run writes to the named directory. There is no flag to disable this; if you do not want to write output, do not run `convert`.

### Search index

What it permits: writing to `<bundle>/.headcleaner/index.sqlite3`. The index is rebuilt atomically in a temporary file and replaced.

Default: writing is opt-in via `headcleaner index rebuild`. Running the rebuild overwrites the previous index.

### Sync state

What it permits: writing to `<bundle>/.headcleaner/sync.json`. Sync state is updated by successful conversion runs and by `headcleaner sync --apply`.

Default: dry-run is the default for the `sync` command. Writing to the sync state requires `--apply`. Without `--apply`, `sync` reports what would change but does not modify anything.

### `redact --write-derivative`

What it permits: writing a separate `<bundle>/_redacted/` derivative plus a
redaction report. Without this flag, `headcleaner redact BUNDLE` only emits
proposals and writes nothing. The canonical bundle, source files, manifest, and
review records are never overwritten by redaction.

Default: disabled. The initial detector reports deterministic secret candidates
using source coordinates and a value digest; it does not persist matched secret
text. A redaction proposal or derivative does not approve, verify, or otherwise
change the trust status of a concept.

## Automatic hostile-input quarantine

Every `convert` run inspects each top-level input before adapter selection,
attachment processing, OCR, or extraction. The inspection inventories ZIP
containers without extracting members and quarantines traversal paths,
malformed/encrypted archives, macro indicators, and declared-type/signature
mismatches. A quarantined input is recorded as `INSPECTION_QUARANTINED` and is
not sent to a conversion engine; this is identical for sequential and parallel
(`--jobs N`) conversion.

There is deliberately no bypass flag. Use `headcleaner inspect INPUT --json`
to examine the structured findings without converting or writing any output.

## Slow operations

A few operations are slow enough that they warrant an explicit opt-in, not because they are unsafe, but because they take long enough that you should be aware of them.

### `--ocr`

What it permits: running Tesseract on image-only pages. Each page takes seconds; a large scanned PDF can take hours.

Default: disabled. Without `--ocr`, image-only PDFs are skipped with a message pointing at the flag.

### `--jobs N`

What it permits: processing up to N files in parallel. Each parallel worker holds resources proportional to the file it is processing.

Default: 1. Pass `--jobs N` to process N files in parallel; headcleaner will refuse values it considers unsafe.

## Override

A few flags override defaults in ways that are safe but warrant attention.

### `--no-cache`

What it permits: re-extracting every file even if the source hash matches the cache.

Default: caching is enabled. Headcleaner skips files whose source hash matches the cached result. Pass `--no-cache` to force re-extraction.

### `--no-fallback`

What it permits: refusing to fall back to an alternative engine if the first one fails.

Default: fallback is enabled when the adapter pool indicates it. Pass `--no-fallback` to fail on the first error rather than trying the next available engine.

### `--engine NAME`

What it permits: pinning a specific engine for files whose extension matches. Useful for testing.

Default: routing is based on file extension and adapter priority. Pass `--engine NAME` to force a specific engine.

## Flags that do not exist

For clarity, the following flags are sometimes assumed but do not exist:

- `--yes` or `--no-prompt` — headcleaner does not prompt for input. There is nothing to confirm.
- `--force` — there is no global force flag. Each risky operation has its own opt-in (e.g. `--apply` for sync, `--prune-generated` for prune).
- `--insecure` — there is no insecure flag. The safety guarantees are not configurable.

## Where to read next

The [safety overview](safety-overview.md) is the single-page summary of the guarantees. The [privacy and data handling page](privacy-and-data-handling.md) explains what headcleaner does with the data you give it. The [CLI reference](../reference/cli-reference.md) is the complete flag reference.