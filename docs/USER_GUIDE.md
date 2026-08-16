# headcleaner User Guide

> A practical, example-driven walkthrough of every headcleaner feature.
> Read top-to-bottom on your first run; jump to a section when you need it later.

## 1. The 30-second tour

```bash
# 1. Install (once)
npm install -g @officecli/officecli     # Office engine
uv tool install headcleaner              # the CLI

# 2. Convert a folder of mixed documents
mkdir ~/inbox && cp *.docx *.pdf *.txt ~/inbox
headcleaner convert ~/inbox --format both --output ~/clean

# 3. Lint the output
headcleaner lint ~/clean

# 4. Auto-repair safe issues
headcleaner lint ~/clean --fix
```

That covers ~80% of daily use. The rest of this guide is the long tail.

## 2. The output shape

headcleaner writes to `<output>/`:

```
~/clean/
├── manifest.json                  # run summary
├── _md/                           # plain Markdown
│   ├── report.docx.md
│   ├── notes.pdf.md
│   └── config.json.md
└── okf/                           # OKF v0.2 bundle
    ├── index.md                   # auto-generated directory index
    ├── report.md                  # OKF concept (extension stripped)
    ├── notes.md
    └── config.md
```

Every OKF concept looks like:

```markdown
---
type: Document
title: Q3 Report
description: Document derived from report.docx via officecli.
resource: file:///home/you/inbox/report.docx
tags: [docx]
status: unverified
stale_after: 2027-02-15
sources:
  - uri: file:///home/you/inbox/report.docx
    kind: file
    sha256: 8c2f5d6e9a1b...
generated: human:you@yourhost
verified: human:pending
---

# Q3 Report

<Markdown body>
```

The `_md/` copy is the same body with lightweight frontmatter (title,
source URI, format, engine, sha256, generated_at).

## 3. Format support

| Format | Engine | Notes |
|---|---|---|
| `.docx`, `.xlsx`, `.pptx` | OfficeCLI binary | requires `npm i -g @officecli/officecli` |
| `.pdf` | pdfplumber | `--ocr` opt-in for scanned PDFs (pytesseract) |
| `.html`, `.htm` | BeautifulSoup + markdownify | strips scripts/nav/header/footer |
| `.txt` | chardet | encoding auto-detected |
| `.md`, `.markdown` | pass-through | strips frontmatter, uses H1 as title |
| `.csv`, `.tsv` | stdlib `csv` + Sniffer | dialect auto-detected |
| `.json` | stdlib `json` | pretty-printed fenced block + summary for flat objects |
| `.eml` | stdlib `email` | headers + text body + attachments list |
| `.epub` | ebooklib | one MD section per chapter, joined with `---` |
| `.rtf` | striprtf | control words stripped, plain text body |
| `.odt`, `.ods`, `.odp` | odfpy | text → paragraphs; spreadsheets → GFM tables; slides → per-slide text |
| `.msg` | extract-msg | Outlook headers + body + attachments |
| `.pst` (best-effort) | libpff-python | item count only; full extraction ships in v1.0 |
| `.doc`, `.xls`, `.ppt` | (clear-error path) | convert with LibreOffice first |

Run `headcleaner templates` to see the live list.

## 4. Human sign-off (`headcleaner review`)

Auto-conversion always sets `verified: human:pending`. The `review`
subcommand walks every pending concept in a bundle and lets you flip it:

```bash
headcleaner review ./out/okf
# Textual TUI keys:
#   a = approve (verified → human:reviewed, status → verified)
#   r = reject  (verified → human:rejected, status → rejected)
#   s = skip    (leaves the concept as pending)
#   n / p = next / previous concept
#   q = quit    (already-approved changes persist)
```

When Textual isn't available (e.g. headless CI), the same flow falls
back to a plain-mode REPL with the same key set.

The `headcleaner lint --strict` rule on `verified: human:pending` will
flag any concept you skipped when you ship the bundle.

## 5. Glob filters

Restrict the walker by filename glob:

```bash
# Only DOCX files
headcleaner inbox --include "*.docx" --output out

# Skip drafts anywhere in the tree
headcleaner inbox --exclude "*draft*" --output out

# Combine
headcleaner inbox -i "*.pdf" -i "*.docx" -e "*old*" --output out
```

Globs match against the **filename**, not the full path.

## 6. OCR for scanned PDFs

PDFs without a text layer (scans, image-only exports) need OCR:

```bash
# One-time install
brew install tesseract              # macOS
# or: choco install tesseract       # Windows
# or: sudo apt install tesseract-ocr # Debian/Ubuntu
uv tool install --with pytesseract --with Pillow headcleaner

# Then run
headcleaner scan.pdf --ocr --output out
```

OCR is slow (~1 sec/page). Pages without a text layer are flagged in
the body and listed in `metadata.image_only_pages`.

## 7. TUI vs plain mode

headcleaner ships two run modes:

| Mode | Trigger | Look |
|---|---|---|
| **TUI** | stdout is a TTY, `--tui` | animated omp-style panel with progress bar |
| **Plain** | non-TTY (pipe, redirect), `--no-tui` | line-by-line progress on stderr |

The TUI:
- Lightning-bolt jar (⚡) brand mark in header
- Rounded-corner box-drawing panels (╭╮╰╯)
- Powerline separators (▕) between segments
- Neon palette: cyan (#22D3EE), pink (#EC4899), purple (#A855F7)
- Live progress bar with ETA
- Per-file status with engine attribution

Force a mode:
```bash
headcleaner inbox --tui        # TUI
headcleaner inbox --no-tui     # plain
```

## 8. The linter

`headcleaner lint <DIR>` reviews every `.md` file under the OKF bundle
and emits findings:

```
$ headcleaner lint ./clean
  warning notes.md:4  [okf/status-missing]  `status` not set; OKF v0.2 §5.2...
  warning notes.md:4  [okf/verified-missing]  `verified` not set; OKF v0.2 §5.3...

  scanned: 12   errors: 0   warnings: 2   info: 0
```

**Severity levels:**
- `error` — concept is structurally broken (missing `type`, invalid SHA-256, …)
- `warning` — concept is OK but could be better (missing trust fields, …)
- `info` — style hint (long lines, …)

**Exit codes:**
- `0` — clean
- `1` — at least one error
- `1` (with `--strict`) — also counts warnings as errors

**Rules applied:**
- OKF structural: `type` required, valid `resource` URI, valid SHA-256, sources[] shape, trust family
- Markdown body: orphan code fences, heading hierarchy, line length

See `docs/OKF_NOTES.md` for the full rule list.

## 8. Auto-repair (`--fix`)

For safe structural issues, the linter can compute a fix:

```bash
# Default: writes to <DIR>.fixed/
headcleaner lint ./clean --fix

# Custom output directory
headcleaner lint ./clean --fix --fix-out /tmp/fixed/

# What gets fixed:
#   + status: unverified       (when missing)
#   + verified: human:pending  (when missing)
#   + stale_after: +180d       (when missing)
#   + resource: <from sources> (when both exist)

# What NEVER gets touched:
#   - body content
#   - the 'type' key (must be human-set)
#   - index.md (auto-generated)
#   - any file without frontmatter
#   - the 'verified' status upgrade (that's a human decision)
```

The source directory is **never modified**. Diff before applying.

## 10. Trust stance (read this before shipping)

Every auto-converted concept gets:

- `status: unverified`
- `verified: human:pending`
- `generated: human:<user>@<host>`
- `stale_after: <today + 180d>`
- `sources: [{uri, kind: file, sha256}]`

We never auto-claim review. To mark a concept as human-reviewed,
**you must edit the file** and change `verified: human:pending` to
`verified: human:<your-id>`.

Find concepts needing review:
```bash
grep -l "verified: human:pending" okf/**/*.md
```

(`headcleaner review` — a TUI for clearing the placeholder — is
tracked in ENHANCEMENTS.md #3.)

## 11. Common recipes

### Migrate a Notion export

```bash
# Notion exports come as a .zip with .md + .csv files
unzip notion-export.zip -d inbox/
headcleaner inbox --include "*.md" --include "*.csv" --output knowledge/
```

### Convert a single file

```bash
headcleaner convert file.pdf --format md --output out/
ls out/_md/
```

### OCR a stack of contracts

```bash
headcleaner ~/Documents/contracts --include "*.pdf" --ocr \
    --format okf --output contracts.okf
```

### Lint in CI

```yaml
# .github/workflows/example.yml
- run: headcleaner convert ./inbox --format both --output ./out --no-tui
- run: headcleaner lint ./out --strict
```

### Watch a folder

```bash
# Not yet implemented (ENHANCEMENTS.md #21)
# Workaround: loop with a sleep
while true; do
    headcleaner convert ./inbox --format both --output ./out --no-tui
    sleep 30
done
```

## 12. Troubleshooting

| Problem | Fix |
|---|---|
| `officecli: command not found` | `npm install -g @officecli/officecli` |
| PDF has no text | `--ocr` flag (needs pytesseract + Tesseract) |
| Hidden files skipped | rename (dotfiles are dropped intentionally) |
| `ModuleNotFoundError: headcleaner` | use `uv run headcleaner` or `uv tool install headcleaner` |
| Linter says `okf/type-required` | add `type: Document` (or a more specific value) to the concept's frontmatter |
| Want to bulk-fix trust fields | `headcleaner lint <DIR> --fix` |

Full troubleshooting guide: `docs/TROUBLESHOOTING.md`.

## 13. Where to go next

- **`docs/INSTALL.md`** — every install path
- **`docs/USAGE.md`** — short usage guide (this file is the long version)
- **`docs/ARCHITECTURE.md`** — how the pipeline fits together
- **`docs/FORMAT_MATRIX.md`** — every format × engine × library
- **`docs/OKF_NOTES.md`** — OKF v0.2 contract + trust policy
- **`docs/CONTRIBUTING.md`** — adding a new format / engine / emitter
- **`docs/ENHANCEMENTS.md`** — 44-item roadmap
- **`docs/FAQ.md`** — common questions
- **`docs/TROUBLESHOOTING.md`** — common errors
- **`docs/CHANGELOG.md`** — release history
- **`docs/PUBLISHING.md`** — how to release / publish to PyPI
