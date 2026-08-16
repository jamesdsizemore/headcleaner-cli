# headcleaner

> Walk a folder, convert every document to **Markdown** (with frontmatter), **OKF v0.2** (with frontmatter), or both — with an omp-style animated TUI.

```bash
headcleaner convert ~/Documents/inbox --format both --output ~/Documents/inbox.clean
```

`headcleaner` is a Python CLI that scans a directory you provide, identifies each document by extension, runs the appropriate extraction engine (OfficeCLI for Office formats, pdfplumber for PDFs, BeautifulSoup for HTML, etc.), and emits clean normalized output — either side-by-side Markdown and OKF, or just one.

- **Output formats:** `--format md` (Markdown), `--format okf` (OKF v0.2 bundle), `--format both` (default)
- **Engine coverage:** 7 formats out of the box (XLSX, DOCX, PPTX, PDF, HTML, HTM, TXT) — see [docs/FORMAT_MATRIX.md](docs/FORMAT_MATRIX.md) for the 16-format v1.0 roadmap
- **TUI:** omp-inspired animated terminal (box-drawing panels, neon palette, powerline separators)
- **Linter:** `headcleaner-lint` reviews the converted Markdown / OKF for formatting issues
- **Honest defaults:** OKF trust fields filled with `unverified` / `human:pending`, never invented

## Install

```bash
# 1. The Office engine — single binary, no Office install needed
npm install -g @officecli/officecli

# 2. The CLI itself (Python ≥3.12, uv-managed)
uv tool install headcleaner

# Or for development:
git clone <this repo>
cd headcleaner-cli
uv sync
uv run headcleaner --help
```

For other install methods (curl | bash, pip, brew, Windows PowerShell), see [docs/INSTALL.md](docs/INSTALL.md).

## Quick start

```bash
headcleaner ~/Documents/inbox --format both --output ./clean
```

This produces:

```
clean/
├── manifest.json                  # run summary: per-file status, engine, sha256
├── _md/                           # plain Markdown (one file per source)
│   ├── notes.docx.md
│   ├── q3.pdf.md
│   └── ...
└── okf/                           # OKF v0.2 bundle (one concept per source)
    ├── index.md                   # auto-generated directory index
    ├── notes.md                   # OKF concept: type=Document
    ├── q3.pdf.md
    └── ...
```

## CLI reference

```bash
headcleaner convert <INPUT_DIR> [OPTIONS]

Options:
  -f, --format {md,okf,both}   Output format(s) [default: both]
  -o, --output DIR             Output directory [default: ./out]
  --ocr                        Enable Tesseract OCR for scanned PDFs
  -i, --include GLOB           Include glob (repeatable)
  -e, --exclude GLOB           Exclude glob (repeatable)
  --no-continue-on-error       Stop on first failure
  --tui / --no-tui             Force / disable the animated TUI (default: auto-detect TTY)
  --no-okf-index               Skip OKF directory index.md generation

Other commands:
  headcleaner templates        List supported formats
  headcleaner agents           Show engine install status
  headcleaner-lint <DIR>       Review converted Markdown / OKF for formatting issues
  headcleaner-lint <DIR> --fix Auto-repair safe issues to <DIR>.fixed/
```

## Why OKF?

OKF (Open Knowledge Format, v0.2) is just **markdown + YAML frontmatter in a directory hierarchy**. That means:

- Every concept is a single `.md` file you can `cat`, `grep`, edit in any text editor
- Bundles live in git — pull requests, diffs, blame all work
- Obsidian, Notion, MkDocs, Hugo, Jekyll all consume OKF natively
- Required frontmatter key is just `type` — anything beyond that is producer freedom

See [docs/OKF_NOTES.md](docs/OKF_NOTES.md) for the OKF v0.2 specifics this CLI emits.

## Trust stance (honest defaults)

We never auto-claim review. Every emitted OKF concept gets:

- `status: unverified`
- `verified: human:pending`
- `generated: human:<user>@<host>` (OKF §7 actor convention)
- `stale_after: <today + 180d>`
- `sources: [{uri: file://..., sha256: ...}]`

A human can grep `human:pending` later to find concepts needing review. See [docs/OKF_NOTES.md](docs/OKF_NOTES.md) for the full contract.

## Supported formats

See [docs/FORMAT_MATRIX.md](docs/FORMAT_MATRIX.md) for the full engine × library table. At a glance:

| Format | Engine | Library |
|---|---|---|
| `.docx`, `.xlsx`, `.pptx` | OfficeCLI binary | (native DOM) |
| `.pdf` | pdfplumber (text-layer), pytesseract if `--ocr` | pdfplumber / pytesseract |
| `.html`, `.htm` | BeautifulSoup | beautifulsoup4 |
| `.txt` | chardet + read | chardet |
| `.md`, `.markdown` | pass-through + frontmatter inject | stdlib |
| `.csv`, `.tsv` | Sniffer dialect + GFM table | stdlib `csv` |
| `.json` | pretty-print + fenced block | stdlib `json` |

v1.0 roadmap adds: `.md`, `.csv`, `.json`, `.epub`, `.rtf`, `.odt`/`.ods`/`.odp`, `.eml`, `.msg`, `.pst`.

## Documentation

| Document | Purpose |
|---|---|
| [README.md](README.md) | this file — install, quick start, CLI reference |
| [docs/INSTALL.md](docs/INSTALL.md) | all install paths (curl, pip, brew, PowerShell, uv, Docker) |
| [docs/USAGE.md](docs/USAGE.md) | detailed usage guide with worked examples |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | how the pipeline fits together, where to extend |
| [docs/FORMAT_MATRIX.md](docs/FORMAT_MATRIX.md) | every supported format × engine × library |
| [docs/OKF_NOTES.md](docs/OKF_NOTES.md) | OKF v0.2 contract this CLI emits + trust policy |
| [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) | common errors and fixes |
| [docs/FAQ.md](docs/FAQ.md) | frequently asked questions |
| [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) | how to add a new format / engine / emitter |
| [docs/CHANGELOG.md](docs/CHANGELOG.md) | release history |
| [docs/ENHANCEMENTS.md](docs/ENHANCEMENTS.md) | 25+ proposed improvements (including the post-conversion linter) |

## Troubleshooting

**`officecli not found`** — install with `npm install -g @officecli/officecli`. Run `headcleaner agents` to verify.

**PDF with no extractable text** — your PDF is image-only. Re-run with `--ocr` (requires `pytesseract` + Tesseract binary on PATH).

**Hidden files skipped** — intentional. Files starting with `.` are dropped by the walker.

**OKF index.md missing for root** — auto-generated when the bundle has ≥1 concept. Use `--no-okf-index` to opt out.

**More** — see [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md).

## Development

```bash
git clone <this repo>
cd headcleaner-cli
uv sync
uv run pytest                # 30 tests, ~5s
uv run headcleaner convert ./tests/fixtures --format both --output ./out
```

## Architecture

```
src/headcleaner/
├── walk.py         # recursive folder walker
├── router.py       # extension → engine dispatch
├── normalize.py    # CanonicalDoc + OKF/MD frontmatter builders
├── lint.py         # post-conversion linter (OKF + Markdown)
├── run.py          # pipeline orchestrator
├── cli.py          # Click CLI (headcleaner command)
├── tui.py          # Textual TUI (omp-style)
├── engines/
│   ├── base.py     # Adapter ABC
│   ├── officecli.py
│   ├── pdf.py
│   ├── html.py
│   └── txt.py
└── emit/
    ├── markdown.py
    ├── okf.py
    ├── okf_index.py
    └── manifest.py
```

Adding a new format: drop a module in `engines/`, register the adapter in `router.py`, add a row to [docs/FORMAT_MATRIX.md](docs/FORMAT_MATRIX.md). See [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) for the full extension guide.

## License

Apache-2.0
