# Set up a Python-friendly document conversion

This tutorial walks through converting a folder of mixed Office documents and PDFs into a clean, searchable archive. It assumes the kind of corpus a small team might accumulate: quarterly reports in PDF, planning spreadsheets, meeting notes in Word, archived web pages, and the occasional scanned PDF.

## Outcome

You will have a converted OKF bundle, a search index, a knowledge graph, a duplicate-family report, and a claims review — the full set of derivatives the everyday workflow expects.

## Prerequisites

- headcleaner installed per the [installation guide](../getting-started/installation.md).
- OfficeCLI installed (`npm install -g @officecli/officecli`) so that `.docx`, `.xlsx`, and `.pptx` files can be extracted.
- A folder containing at least one Word document, one Excel spreadsheet, one PDF, and one HTML file. A quarterly-report archive is ideal; a personal notes folder is fine.

## Step 1 — Confirm your environment

Before converting anything, run the diagnostic:

```bash
uv run --no-sync --python 3.13 headcleaner doctor
```

The doctor command prints a checklist of the tools headcleaner can see on your machine. A healthy environment for this tutorial shows Python, `uv`, and OfficeCLI as available. If OfficeCLI is missing, the report will tell you so; install it and re-run before continuing.

## Step 2 — Convert the folder

The conversion command reads your input folder and writes the canonical output to the directory you specify. Use the recommended pair of commands:

```bash
uv run --no-sync --python 3.13 headcleaner convert ./quarterly-archive ./quarterly-archive.clean --format both
```

The `--format both` flag is the default; it produces both the `_md/` tree and the `okf/` bundle. If you only want the OKF bundle, use `--format okf`. If you only want the plain Markdown, use `--format md`. For a real archive you almost always want both, because downstream tools vary in which they prefer.

While the command runs, pay attention to the per-file lines. Each line shows the status, the source file, the engine that handled it, the elapsed time, and any warning. A healthy run shows mostly `ok`, occasional `warn` (usually about an image that could not be extracted or a table that needs review), and no `failed`.

## Step 3 — Read the report

Open `./quarterly-archive.clean/REPORT.md` and read the per-engine breakdown. The table near the top of the report shows, for each engine, how many files it handled and how long on average. For a Python-friendly archive you should see OfficeCLI as the busiest engine, pdfplumber next, and BeautifulSoup (for HTML) at the bottom.

If any files are in `failed` status, read the `error` field on each. The most common cause on a first run is a corrupted source file; the next most common is an OfficeCLI version mismatch. The [troubleshooting guide](../user-guide/troubleshooting.md) walks through the symptom-first diagnosis.

## Step 4 — Build the search index

The conversion produced cited chunks in `okf/chunks.jsonl`. Build the searchable database over them:

```bash
uv run --no-sync --python 3.13 headcleaner index rebuild ./quarterly-archive.clean/okf
```

The rebuild reads the chunks, builds a new SQLite database in a temporary file, runs an integrity check, and atomically replaces the previous index. If anything goes wrong during the rebuild, the previous index is preserved and the command exits with a non-zero status and an `INDEX_BUILD_FAILED` message.

## Step 5 — Run a search you can verify

Pick a phrase you know appears in one of your source documents — a project name, a customer name, a date, a specific term. Run a search and confirm the result:

```bash
uv run --no-sync --python 3.13 headcleaner search "Project Atlas" --bundle ./quarterly-archive.clean --json
```

The JSON output includes the citation block. Open the source file referenced in the citation and confirm the phrase appears where the citation says it does. If the citation does not match the source, something went wrong; please open an issue with the smallest possible reproduction.

## Step 6 — Build the knowledge graph

The conversion produced concepts and chunks; now build the knowledge graph that connects them:

```bash
uv run --no-sync --python 3.13 headcleaner graph ./quarterly-archive.clean/okf --json > graph.json
```

The graph command reads the chunks, builds containment edges (concept-to-chunk), citation edges (chunk-to-source), mention edges (chunk-to-entity, chunk-to-topic), and any explicit cross-references found in the documents. The output is written to `okf/graph.jsonl`; piping to `graph.json` is optional and just gives you a copy outside the bundle.

The graph is a derivative. You can delete it any time and rebuild it with the same command; nothing else in the bundle depends on its existence.

## Step 7 — Run the duplicate-family analysis

For a real archive, finding near-duplicates early is useful. Headcleaner's dedupe analysis is non-destructive; it reports candidates but never deletes or merges anything.

```bash
uv run --no-sync --python 3.13 headcleaner dedupe ./quarterly-archive.clean/okf --threshold 0.85 --json > dedupe.json
```

The threshold is the minimum similarity score for a pair to be reported as a candidate. The default of 0.8 is conservative; 0.85 is a tighter setting that produces fewer false positives. The `--json` flag emits the structured result; without it, the command prints a one-line summary.

Open `dedupe.json`. Each candidate pair has `left_id`, `right_id`, a combined similarity score, and individual scores for title, content, and path similarity. The candidates are not asserted to be duplicates; you decide what to do with them.

## Step 8 — Run the claims review

The claims review finds dated facts, named owners, and other structured claim candidates in your chunks, then pairs them to surface potential conflicts. Like the dedupe analysis, it is non-destructive and report-only.

```bash
uv run --no-sync --python 3.13 headcleaner claims ./quarterly-archive.clean/okf --json > claims.json
```

Open `claims.json`. The `claims` array lists every claim candidate found, with its source citation. The `findings` array lists potential conflict pairs, with `rule_id` values that identify the comparison rule used. Findings are labeled `potential_conflict`; headcleaner does not assert that any pair is actually a contradiction.

## What you have learned

You know how to convert a realistic Office-and-PDF corpus, build the full derivative stack (search index, knowledge graph, dedupe report, claims report), and read each derivative without confusing it for an assertion of fact. The next thing most teams want is to wire this into a recurring workflow — the [CI integration tutorial](ci-integration.md) is the natural next lesson.

## Where to go next

- [Everyday workflow](../user-guide/everyday-workflow.md) — the four moments when headcleaner pays off.
- [CI integration tutorial](ci-integration.md) — running this conversion on every pull request.
- [Local search tutorial](local-search.md) — going deeper on the search index.
- [PDF and OCR tutorial](pdf-and-ocr.md) — when your corpus includes scanned documents.