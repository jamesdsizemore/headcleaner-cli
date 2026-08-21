# Troubleshooting

This page is a symptom-first guide to the things that go wrong with headcleaner. If your run is failing or behaving unexpectedly, find the symptom that matches what you see and follow the steps under it. The page covers skipped checks, missing tools, missing configuration, wrong Python, coding-assistant connection problems, and permission-required errors.

The page is not a complete reference; for that, see the [result reference](../reference/result-reference.md) and the [configuration reference](../reference/configuration-reference.md). This page is the "I have a problem right now and I want to fix it" guide.

## Symptom: A file is in `skipped` status

If a file you expected to be converted is in `skipped` status, the most common reason is that headcleaner recognized the format but the required tool is not installed. The skipped entry in `REPORT.md` or `manifest.json` will tell you which tool is missing.

For PDF files in particular, "skipped" usually means the PDF is image-only and Tesseract is not installed. Headcleaner can extract text from text-native PDFs without any external tool, but scanned PDFs need OCR. The fix is to install Tesseract per the [installation guide](../getting-started/installation.md#tesseract-for-scanned-pdfs-and-image-only-documents) and re-run the conversion with the `--ocr` flag.

For Office files (`.doc`, `.xls`, `.ppt`, the legacy non-XML formats), skipped usually means LibreOffice is not installed. Headcleaner uses LibreOffice to upgrade legacy Office files into the XML-based formats that the modern adapters can read. Install LibreOffice per the [installation guide](../getting-started/installation.md#libreoffice-for-legacy-office-formats) and re-run.

For any file type, if the skipped message says "unsupported format" rather than naming a tool, headcleaner does not have an adapter for that format. The list of supported formats is in the [engine directory](../reference/engine-directory.md). If you need support for a format that is not listed, you can add a custom adapter; see the [tool and engine development guide](../developer/tool-and-engine-development.md).

## Symptom: A file is in `failed` status

A `failed` file is one headcleaner tried to convert but could not. The `error` field in `REPORT.md` or `manifest.json` describes what went wrong.

The most common causes, by frequency:

- The source file is corrupted. Open it in the application that produced it and confirm it opens cleanly. Headcleaner cannot recover from a corrupted source; you need to fix or remove the file.
- The required tool is installed but failing on this specific file. Run `headcleaner doctor` and confirm the tool shows up as installed. If it does, try running the tool directly on the source file to see what error it produces.
- A permission error reading the source or writing the output. Confirm that your user account has read access to the source and write access to the output directory.

If the error message says "engine attempted but failed" and the engine name is unfamiliar, check the [engine directory](../reference/engine-directory.md) to understand what that engine does and what input shape it expects.

## Symptom: `uv sync` fails with a Python version error

The error message will tell you which Python version was requested versus what was available. Headcleaner requires Python 3.12 or 3.13 and the lockfile is built against 3.13.

The fix is to either install Python 3.13 or to pass `--python 3.13` explicitly to `uv sync` so it downloads and manages Python 3.13 for you. The latter is the recommended path because it isolates headcleaner's Python from your system Python.

If `uv sync --locked` fails saying the lockfile is out of date, do not pass `--no-lock` or regenerate the lockfile without authorization. The lockfile is part of the project's reproducibility contract; out-of-date lockfile means the project's dependencies changed. Pull the latest changes from the project's main branch and re-run.

## Symptom: `headcleaner` is not found after installation

If `uv sync` succeeded but invoking `headcleaner` directly fails with "command not found," your shell's `PATH` is not picking up the `uv`-managed virtual environment's `bin/` directory.

The reliable fix is to always invoke headcleaner through `uv run`:

```bash
uv run --no-sync --python 3.13 headcleaner …
```

This works regardless of `PATH` because `uv run` activates the virtual environment before invoking the command. If you prefer to call `headcleaner` directly, you need to either activate the virtual environment first (`.venv/bin/activate` on macOS/Linux, `.venv\Scripts\activate` on Windows) or add the virtual environment's `bin/` directory to your `PATH`.

## Symptom: A coding assistant cannot connect to headcleaner

If you have configured the MCP integration but the assistant reports it cannot reach the MCP server, the most common reasons are:

- The client configuration is using a different `command` than `uv` with the exact arguments shown in the [MCP client setup](../integrations/mcp-client-setup.md) page. MCP clients require very specific argument shapes; a small difference can prevent the server from starting.
- The MCP server is failing immediately because of an environment problem. Run `uv run --no-sync --python 3.13 headcleaner mcp` from the same shell the assistant would use, and confirm the command starts cleanly. It will print a JSON-RPC handshake prompt on stdin and wait; that is the expected behavior.
- The assistant expects the server to bind a TCP socket, but headcleaner's MCP server speaks stdio. Check the assistant's documentation; if it requires TCP, headcleaner does not currently support that mode.

## Symptom: A permission-required error appears

Headcleaner refuses to perform certain operations without explicit configuration. The most common are:

- Sending chunks to a remote embedding model. The fix is to pass `--allow-network` on the `index embed` command. Headcleaner will not connect to any network service without that flag, even if you have configured a provider that supports remote inference.
- Connecting to a remote vector database. The fix is the same `--allow-network` flag plus the `--qdrant-endpoint` and `--qdrant-collection` flags. The combination ensures you have explicitly chosen both the provider and the destination.
- Writing a derivative that overrides canonical content. Headcleaner never overwrites canonical output; derivatives go to their own locations. If you are seeing a permission error about writing to a path you expect to be writable, confirm the path is not under your canonical output directory.
- Running an OCR pass that might modify your source. OCR is read-only by default and never modifies the source; the error would be about something else. Run `headcleaner doctor` to confirm Tesseract is installed correctly.

## Symptom: A run is unexpectedly slow

If a run is taking much longer than you expect, the most common reasons are:

- OCR is enabled and your input contains scanned PDFs. OCR is slow by nature. Consider running OCR only on the files that need it, by passing file globs to `--include` or `--exclude`.
- The first run on a large bundle. The first run extracts everything; subsequent runs use the cache and are much faster. Confirm caching is enabled (it is by default; pass `--no-cache` only when you want to force re-extraction).
- The search index is being rebuilt on every run. Index rebuilding is a separate command; the `convert` command does not rebuild the index. Run `index rebuild` only when you want to refresh the index.

If the slowness persists and you cannot explain it, capture the run with `--json` and inspect the per-file `duration_seconds` field. A small number of files will dominate the wall clock; focusing on them usually reveals the cause.

## Symptom: I do not know where to look next

If none of the above match your situation, the next best places to look are:

- The [FAQ](faq.md) for practical questions that come up often.
- The [result reference](../reference/result-reference.md) for what every field in the manifest means.
- The run report at `<bundle>/REPORT.md` for a structured summary of what happened.

If you have found a bug — for example, an `error` status that suggests headcleaner encountered something the maintainers did not anticipate — please open an issue with the smallest possible reproduction, the output of `headcleaner --version`, and the relevant portion of the report.

## Symptom: I want to know why a concept is gated

Run `headcleaner readiness BUNDLE --json` and look at the `deductions` array for the concept. Every deduction cites a `rule_id`, a `value`, a `threshold`, a `contribution`, and a `citation` (the frontmatter field that triggered the deduction). The grade is computed by subtracting documented deductions from `MAX_SCORE = 1.0` against the named profile's thresholds (`default`, `rag`, or `publication`).

## Symptom: My attestation `--verify` fails after I edit one concept

That is the expected behavior. `headcleaner attest --verify` re-hashes the bundle and compares against `attestation.json`; any concept edit breaks the Merkle root. Re-run `headcleaner attest BUNDLE [--key PATH] [--in-toto PATH]` to record a fresh attestation. The `--verify` exit code is non-zero on mismatch — a named error is printed to stderr.

## Symptom: My queue claim was rejected

`headcleaner review-claim` consults the per-bundle audit sidecar at `<bundle>/.headcleaner/queue-audit.json` before claiming. If another reviewer has already claimed that concept_ref, the CLI rejects the claim with exit 1 and a `duplicate claim rejected` message. Use the same `--reviewer` to retry (idempotent for the same reviewer), or pick a different concept.