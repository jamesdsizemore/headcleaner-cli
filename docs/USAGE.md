# Using headcleaner

A practical guide to the `headcleaner convert` command, with worked examples.

## Table of contents

1. [The basics](#1-the-basics)
2. [Format selection (`--format`)](#2-format-selection---format)
3. [Glob filters (`--include` / `--exclude`)](#3-glob-filters---include---exclude)
4. [OCR for scanned PDFs (`--ocr`)](#4-ocr-for-scanned-pdfs---ocr)
5. [Output layout](#5-output-layout)
6. [TUI vs plain mode](#6-tui-vs-plain-mode)
7. [Linting the output](#7-linting-the-output)
8. [Common recipes](#8-common-recipes)

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

## 4. OCR for scanned PDFs (`--ocr`)

PDFs without a text layer (scans, image-only files) need OCR. Enable
with `--ocr`:

```bash
headcleaner inbox --include "*.pdf" --ocr --output out
```

Requires:
- `pytesseract` Python package (install via `uv tool install --with pytesseract headcleaner`)
- Tesseract OCR binary on PATH (`brew install tesseract` / `choco install tesseract`)

OCR is slow (~1 sec/page on commodity hardware) — keep it off by default.

---

## 5. Output layout

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

## 6. TUI vs plain mode

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

## 7. Linting the output

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

## 8. Common recipes

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
