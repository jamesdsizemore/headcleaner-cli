# Using headcleaner

A practical guide to the `headcleaner convert` command, with worked examples.

## Table of contents

1. [The basics](#1-the-basics)
2. [Format selection (`--format`)](#2-format-selection---format)
3. [Glob filters (`--include` / `--exclude`)](#3-glob-filters---include---exclude)
4. [OCR profiles and languages](#4-ocr-profiles-and-languages)
5. [Engine selection and fallbacks](#5-engine-selection-and-fallbacks)
6. [Contained attachments and archives](#6-contained-attachments-and-archives)
7. [Output layout and structured sidecars](#7-output-layout-and-structured-sidecars)
8. [Quality and render verification](#8-quality-and-render-verification)
9. [TUI vs plain mode](#9-tui-vs-plain-mode)
10. [Linting the output](#10-linting-the-output)
11. [Common recipes](#11-common-recipes)

---

## 1. The basics

```bash
headcleaner convert <INPUT_DIR> -o <OUTPUT_DIR>
```

`INPUT_DIR` is walked recursively. Every file whose extension has a
registered adapter is converted. The rest are silently skipped.

```bash
headcleaner ~/Documents/inbox --format both --output ~/Documents/inbox.clean
```

This produces `_md/` (plain Markdown), `okf/` (OKF v0.2 bundle), and
`manifest.json` at the root of the output dir.

---

## 2. Format selection (`--format`)

```bash
# Default — both Markdown and OKF
headcleaner inbox --output out

# Just Markdown
headcleaner inbox --format md --output out

# Just OKF
headcleaner inbox --format okf --output out
```

`--format both` is the default because most users want both: the OKF bundle
for indexing/search, and the plain Markdown for editing.

---

## 3. Glob filters (`--include` / `--exclude`)

Restrict the walker to a subset of files via shell-style globs. Both flags
are repeatable.

```bash
# Only convert .docx files
headcleaner inbox --include "*.docx" --output out

# Skip everything that lives in a "drafts" folder
headcleaner inbox --exclude "*drafts*" --output out

# Both: only .docx and .pdf, but skip any with "old" in the name
headcleaner inbox -i "*.docx" -i "*.pdf" -e "*old*" --output out
```

Globs match against the **filename** (not the full path). Use quotes to
protect `*` from your shell.

---

## 4. OCR profiles and languages

PDFs without a text layer (scans, image-only files) need OCR. Enable
with `--ocr`:

```bash
headcleaner inbox --include "*.pdf" --ocr --ocr-profile archival --ocr-lang eng --output out
```

Requires:
- `pytesseract` Python package (install via `uv tool install --with pytesseract headcleaner`)
- Tesseract OCR binary on PATH (`brew install tesseract` / `choco install tesseract`)

Profiles are `fast`, `balanced`, `archival`, and `handwriting_experimental`.
`--ocr-lang` accepts comma-separated Tesseract pack codes and is checked before
documents are processed. Run `headcleaner doctor` to see installed language
packs. OCR is opt-in and does not change the output's `unverified` trust state.

---

## 5. Engine selection and fallbacks

Use `--engine NAME` when a workflow requires a particular local extractor.
The named engine is the only attempted engine unless `--allow-fallback` is also
supplied. `--no-fallback` explicitly disables alternates. Engines that declare
a network requirement are never selected without `--allow-network`.

```bash
# Require the PDF adapter and retain its declared fallback policy only if needed
headcleaner inbox --include "*.pdf" --engine pdf --allow-fallback --output out
```

The manifest records each attempted, unavailable, or skipped engine in
diagnostics. An unavailable required tool is reported; it is never invoked.

---

## 6. Contained attachments and archives

Supported email and declared ZIP attachments become logical child results when
their extracted type has an adapter. Their source URI starts with `attachment:`
and their emitted child path is hash/ordinal based, never derived from an
untrusted filename. The defaults bound nesting depth, member count, individual
member bytes, and total extracted bytes.

```bash
headcleaner inbox --attachment-max-depth 2 --attachment-max-members 100 --output out
```

Traversal names, symlinks, encrypted ZIP members, duplicate members, unsafe
XML, and limit breaches become `ATTACHMENT_QUARANTINED` manifest diagnostics.
Safe siblings continue. Password-protected content remains metadata-only;
HeadCleaner does not request or log passwords.

---

## 7. Output layout and structured sidecars

```
out/
├── manifest.json                  # run summary: per-file status, engine, sha256
├── _md/                           # plain Markdown (one file per source)
│   ├── notes.docx.md
│   ├── q3.pdf.md
│   └── ...
└── okf/                           # OKF v0.2 bundle (one concept per source)
    ├── index.md                   # auto-generated directory index
    ├── notes.docx.md              # NOTE: extension stripped in OKF
    ├── q3.pdf.md
    └── ...
```

OKF strips the source extension because OKF concepts are just `.md` files;
the original extension is preserved in the frontmatter `tags`.

Use `--no-okf-index` to skip the directory index generation.

---

For supported CSV, Office worksheet, and PDF table extraction, OKF output may
also include deterministic CSV/JSON table sidecars. These preserve available
headers, formulas, merged-range metadata, provenance, and PDF inference
warnings; Markdown remains the readable projection.

---

## 8. Quality and render verification

Run the benchmark against attributed fixtures to measure required text,
heading, and table anchors. It fails on fixture metadata, source-hash, or
baseline metric regressions and never rewrites the baseline without an explicit
`--update-baseline` path.

```bash
headcleaner benchmark tests/quality/fixtures --json
```

Compare already-created source/output artifacts without converting them again:

```bash
headcleaner verify-render original.txt out/_md/original.txt.md --output-dir out --json
```

Reports are written under `_verification/<source-sha256>/report.json`. A
mismatch is an advisory review finding by default; unavailable renderers are
reported without mutating canonical Markdown or OKF output.

---

## 9. TUI vs plain mode

`headcleaner` ships two run modes:

| Mode | Trigger | Output |
|---|---|---|
| **TUI** (animated, omp-style) | stdout is a TTY, `--tui` | animated panel with progress bar, per-file status, neon palette |
| **Plain** | non-TTY (pipe, redirect), `--no-tui` | line-by-line progress on stderr, exit code on completion |

Force a mode:

```bash
headcleaner inbox --tui                # force TUI
headcleaner inbox --no-tui             # force plain
```

In CI / scripts, `--no-tui` is what you want.

---

## 10. Linting the output

After conversion, run the linter to catch structural issues before you
commit the bundle:

```bash
headcleaner lint out/
```

The linter walks every `.md` file under the output dir, applies OKF and
Markdown rules, and prints findings with severity (`error`, `warning`, `info`).

Exit codes:
- `0` — clean (no errors; warnings ignored unless `--strict`)
- `1` — at least one error (or a warning under `--strict`)

Useful flags:

```bash
headcleaner lint out/ --strict      # warnings count as errors
headcleaner lint out/ --no-color    # plain text (for CI logs)
```

Run it before every commit:

```bash
# .git/hooks/pre-commit
#!/bin/sh
headcleaner lint okf/ || exit 1
```

---

## 11. Common recipes

### Inbox zero — convert everything in Downloads

```bash
mkdir -p ~/Downloads.clean
headcleaner ~/Downloads --format both --output ~/Downloads.clean
headcleaner lint ~/Downloads.clean --strict
```

### OCR a stack of scanned contracts

```bash
headcleaner ~/Documents/contracts --include "*.pdf" --ocr \
    --format okf --output ~/contracts.okf
```

### Migrate a project from Notion export to an OKF bundle

```bash
headcleaner ~/Downloads/notion-export \
    --include "*.md" --include "*.csv" \
    --format okf --output ./knowledge
```

### Watch a folder, auto-convert new files

```bash
ls ~/inbox | while read f; do
    headcleaner "$f" --format md --output out/ || true
done
```

(For real watch-mode, see ENHANCEMENTS.md #4.)
