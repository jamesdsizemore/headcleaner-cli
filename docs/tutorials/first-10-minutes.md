# Your first ten minutes

This tutorial is the on-ramp lesson. By the end of it you will have converted a small folder of mixed documents into a clean, searchable output. You will read the report, build a search index, and decide where to go next.

## Outcome

You will have a converted output folder, a search index over that output, and a clear next step in your headcleaner journey.

## Prerequisites

You need headcleaner installed. The [installation guide](../getting-started/installation.md) walks through that step by step on Windows, macOS, and Linux. You also need a folder containing three to ten mixed documents: at least one Word, Excel, or PowerPoint file; at least one PDF; and ideally one HTML or plain-text file. If you do not have a folder that fits, create one and drop a few representative files in.

You do not need OfficeCLI, LibreOffice, or Tesseract installed for this tutorial. The folder you pick may exercise only the built-in adapters; that is fine.

## Step 1 — Look at what you have

Before you run headcleaner, look at the folder you have chosen. Confirm:

- The folder exists and you have read access to it.
- The folder contains at least three documents in supported formats.
- You have a place to write the output. For this tutorial, a sibling directory called `my-folder.clean` is enough.

## Step 2 — Run the conversion

From the parent directory that contains your input folder, run:

```bash
uv run --no-sync --python 3.13 headcleaner convert ./my-folder ./my-folder.clean
```

Headcleaner walks the folder, picks an adapter for each file, normalizes the output, and writes the result to `./my-folder.clean`. The output includes both plain Markdown (`_md/`) and an OKF bundle (`okf/`), a `manifest.json`, and a `REPORT.md`.

While the command runs, you will see one line per file. Each line looks like:

```text
[ok]     notes.docx       (officecli, 0.4s)
[ok]     q3-report.pdf    (pdfplumber, 1.2s)
[warn]   archived.eml     (eml, 0.8s) — 1 attachment quarantined
[skipped] photo.jpg          (unsupported format)
[ok]     budget.xlsx      (officecli, 0.3s)
```

When the command finishes, look at the final summary line. A healthy run ends with a count of `ok`, `skipped`, and `failed` files where `failed` is zero.

## Step 3 — Look at the output

Open `./my-folder.clean` in your file browser. You should see:

- `manifest.json` — the structured summary of the run.
- `REPORT.md` — the human-readable summary.
- `_md/` — one Markdown file per source.
- `okf/` — the OKF v0.2 bundle, including `index.md`.

Open `REPORT.md` first. The summary table at the top tells you whether the run was healthy in three numbers. The [Understanding results](../user-guide/understanding-results.md) page explains what each status means and what to do about each one.

Open one of the `_md/` files, for example `_md/notes.docx.md`. You should see a YAML frontmatter block at the top with the source URI, source SHA-256 hash, generation date, and trust state. The body after the frontmatter is the readable Markdown rendering of your document. The [Citations and trust](../user-guide/citations-and-trust.md) page explains what each frontmatter field means.

## Step 4 — Build the search index

Now that you have a converted output, build the local search index so you can query it:

```bash
uv run --no-sync --python 3.13 headcleaner index rebuild ./my-folder.clean/okf
```

Headcleaner reads the cited chunks from `okf/chunks.jsonl`, builds a new SQLite database, runs an integrity check, and atomically replaces the previous database. The command prints the path to the rebuilt index and the count of chunks indexed.

If the chunk count is non-zero, your conversion produced body content that was chunked — exactly what you want. If the count is zero, either your input folder had no body content (for example, only image-only PDFs without OCR) or the chunking thresholds excluded everything. The [chunking and indexing developer guide](../developer/chunking-and-indexing.md) explains the chunking parameters.

## Step 5 — Run a search

Try a search using a phrase you know appears in one of your source files:

```bash
uv run --no-sync --python 3.13 headcleaner search "the phrase you remember" --bundle ./my-folder.clean
```

The command prints one line per result with the source concept path and a short excerpt. The excerpt is the chunk that matched your query. If you add `--json`, the output becomes a structured list with full citation information; the [result reference](../reference/result-reference.md) documents every field.

## Step 6 — Decide where to go next

You have a working headcleaner setup. From here the documentation branches based on what you want to do next.

- If you want to use headcleaner regularly, the [everyday workflow guide](../user-guide/everyday-workflow.md) shows the four moments when headcleaner pays off the most.
- If you want to convert a more challenging corpus (PDFs with OCR, email with attachments, scanned documents), the relevant tutorial in [the tutorials collection](index.md) is the next lesson.
- If you want to connect headcleaner to an AI coding assistant, the [MCP client setup guide](../integrations/mcp-client-setup.md) and the [AI assistant tutorial](ai-coding-assistant.md) cover that.
- If you want to add headcleaner to CI, the [CI integration tutorial](ci-integration.md) walks through that.

## What you have learned

You know how to convert a folder, read the output, build the search index, run a search, and use citations to trace any result back to its source. You also know where to look for the next thing you want to do with headcleaner. That is the foundation every later tutorial builds on.