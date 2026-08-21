# Result reference

This page documents every field that headcleaner emits in its result artifacts: `manifest.json`, `REPORT.md`, the per-file result records, the run event stream, and the exit codes. The page is a lookup; if you are not yet familiar with what these artifacts are, read the [checking converted output](../user-guide/checking-converted-output.md) page first.

## The manifest

`manifest.json` is the structured record of a run. It is the source of truth that every other artifact is derived from. The top-level shape is:

```json
{
  "schema_version": "1",
  "tool_version": "0.x.y",
  "started_at": "2026-08-20T14:32:01Z",
  "finished_at": "2026-08-20T14:32:04Z",
  "input_root": "/abs/path/to/input",
  "output_root": "/abs/path/to/output",
  "options": { ... },
  "results": [ ... ],
  "engines": { ... },
  "totals": { ... }
}
```

The fields:

- `schema_version` is the manifest schema version. The current value is `"1"`. Downstream tools should check this before consuming the manifest.
- `tool_version` is the headcleaner version that produced the manifest. The combination of `schema_version` and `tool_version` uniquely identifies the producer.
- `started_at` and `finished_at` are ISO 8601 timestamps in UTC.
- `input_root` and `output_root` are the absolute paths to the input and output directories. They are recorded for reproducibility and debugging; downstream tools that move the bundle should update them or omit them.
- `options` is a record of the run settings: format, OCR settings, dedupe threshold, claim suppressions, claim scope, and any other flags that affect output. The full list is in the [configuration reference](configuration-reference.md).
- `results` is the per-file result array. See below.
- `engines` is a summary of which engines were attempted and how often. Useful for understanding the shape of a run.
- `totals` is a per-status count: how many files were `ok`, `warn`, `failed`, `error`, or `skipped`.

## Per-file result records

Each entry in `results` describes one source file. The fields:

- `relpath` — the file path relative to `input_root`. Always uses POSIX separators (`/`) regardless of host OS.
- `engine` — the name of the engine that handled the file (e.g. `officecli`, `pdfplumber`, `beautifulsoup`). Empty if the file was skipped before engine selection.
- `status` — one of `ok`, `warn`, `failed`, `error`, `skipped`. The semantics are in the [understanding results](../user-guide/understanding-results.md) page.
- `sha256` — the source file's SHA-256 hash. Empty if the file was not read.
- `md_path` — the path to the generated Markdown output relative to `output_root`, if any.
- `okf_path` — the path to the generated OKF output relative to `output_root`, if any.
- `duration_seconds` — how long the file took to process, in seconds.
- `error` — a human-readable error message if `status` is `failed`, `error`, or `skipped`. Empty for `ok` and `warn`.
- `attachments` — for email messages, the list of child attachments. Each entry has `id`, `sha256`, and `media_type`.
- `diagnostics` — a list of structured diagnostic objects. Each has `code`, `severity`, `message`, and `evidence`. The codes are stable uppercase identifiers; the [configuration reference](configuration-reference.md) lists them.
- `metrics` — extraction metrics: `page_count`, `character_count`, `element_counts`, `engine_attempts`, `ocr_used`, `detected_languages`, `confidence_inputs`. Consume these values as structured evidence rather than positional text; different engines can provide different subsets.

## The run report

`REPORT.md` is the human-readable version of the manifest. It is structured as:

- A header section with bundle, started, finished, and wall-clock.
- A summary table with files processed, files skipped, files failed, total, and success rate.
- A per-engine breakdown table with each engine's total, ok, failed, error rate, and average time.
- An extraction diagnostics section listing diagnostic codes and average confidence (if available).
- A claim review candidates section (if claim review was run).
- A duplicate and version candidates section (if dedupe was run).
- An evidence graph section (if graph was run).
- A top errors section listing up to ten error messages from failed files.

The fields in the report are computed from the manifest, not from independent sources. The manifest is authoritative.

## The run event stream

When you pass `--json` to `convert`, headcleaner emits one JSON event per file plus a `start` event at the beginning and a `finish` event at the end. Each event has a flat shape:

```json
{"event": "start", "tool": "headcleaner", "version": "0.x.y", "format": "both", "dry_run": false, "files": 12}
{"event": "file", "relpath": "notes.docx", "engine": "officecli", "status": "ok", "sha256": "...", "duration_seconds": 0.4}
{"event": "finish", "ok": 9, "skipped": 2, "failed": 1}
```

The `events validate` subcommand checks the stream against the schema. The stream is the easiest artifact to consume in CI: pipe it to a downstream tool, parse one JSON object per line, and react to `finish` to drive the CI exit code.

## Exit codes

Headcleaner uses a small set of exit codes that are stable across commands:

- `0` — success. No error-level findings or failures occurred.
- `1` — recoverable failure. A file was in `failed` status, a policy rule matched an error finding, a search query had no results, or a command-specific failure occurred. The output is still usable; the error is in the result artifact.
- `2` — fatal error. An argument was malformed, the lockfile is out of date, the environment is missing a required tool, or an internal error occurred. The command did not produce useful output.

CI pipelines should treat `1` as "fix the underlying issue" and `2` as "fix the pipeline." The two are usually distinct different in nature and require different responses.

## Status values in detail

The five status values carry the same meaning across all the artifacts. The semantics, repeated here for convenience:

- `ok` — the file was converted successfully.
- `warn` — the file was converted but a recoverable condition was noted. The output is usable.
- `failed` — the file could not be converted. The output is missing or partial. The `error` field has details.
- `error` — an unexpected internal error occurred. This typically warrants a bug report.
- `skipped` — the file was deliberately not converted, either because it is not a supported format or because a required tool was missing.

The status colors in `REPORT.md` and the terminal output use cyan for `ok`, pink for `warn`/`failed`/`error`, and purple for information. Skipped is shown in muted grey.

## Phase 3 result artifacts

These artifacts are produced by post-conversion commands and follow the same JSON shape discipline as the manifest.

- `<bundle>/attestation.json` (Contract 3.5) — produced by `headcleaner attest`. Carries `tool`, `version`, `bundle_root`, `concept_count`, `concepts` (per-bundle-relative SHA-256 set), `source_provenance` (OKF sources[] bundle-relative paths and SHA-256), `merkle_root`, `engines` (capability/version records), `schema_version`, `timestamp`, and optionally `public_key`/`signature`/`proof`. Conforms to `docs/schemas/attestation.schema.json`.
- `<bundle>/.headcleaner/queue-audit.json` (Contract 3.6) — produced by `headcleaner review-claim`. Append-only list of `{concept_ref, reviewer, state, claimed_at}` entries.
- `<bundle>/_redacted/` (Contract 3.3, opt-in) — produced by `headcleaner redact --write-derivative`. A parallel derivative that links back to canonical concepts; never overwrites canonical output.

## What to read next

The [CLI reference](cli-reference.md) documents every command and its flags. The [configuration reference](configuration-reference.md) documents every field you can set in a policy file. The [engine directory](engine-directory.md) is the per-engine reference.