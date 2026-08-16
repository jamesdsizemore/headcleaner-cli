# AGENTS.md

This file orients AI coding agents working in this repo.

## What is headcleaner?

A Python CLI that walks a folder and converts every supported document
into Markdown and/or OKF v0.2 with frontmatter. Companion linter
(`headcleaner lint`) reviews the converted output. Built with an
omp-inspired TUI in a neon cyan/pink/purple palette.

The lightning-bolt jar is the brand mark.

## Stack

- **Language:** Python 3.12 (pinned in `.python-version`)
- **Package manager:** uv (creates `.venv/`, manages deps from `pyproject.toml`)
- **TUI:** Textual + custom `theme.py` (rounded box-drawing, powerline separators, neon palette)
- **Office engine:** `officecli` binary (single binary on PATH; npm-installable: `npm i -g @officecli/officecli`)
- **Output formats:** Markdown (with YAML frontmatter), OKF v0.2 (with full trust family), or both
- **Linter:** `headcleaner lint` — review converted MD/OKF for formatting issues

## Commands

```bash
uv sync                              # install all deps into .venv
uv run headcleaner --help            # CLI help
uv run headcleaner convert IN OUT    # convert a folder
uv run headcleaner lint OUT          # review converted output
uv run pytest                        # run tests
uv run python -m headcleaner.cli    # same as `headcleaner`
```

## Layout

```
src/headcleaner/
  __init__.py
  cli.py          # Click entrypoint (headcleaner command)
  tui.py          # Textual TUI
  theme.py        # ANSI colors + box-drawing symbols
  walk.py         # folder walker
  router.py       # ext → engine dispatch
  normalize.py    # adapter output → CanonicalDoc
  run.py          # pipeline orchestrator
  lint.py         # post-conversion linter
  engines/
    base.py       # Adapter ABC
    officecli.py  # DOCX/XLSX/PPTX
    pdf.py        # PDF (pdfplumber, opt-in pytesseract)
    html.py       # HTML/HTM (BeautifulSoup + markdownify)
    txt.py        # TXT (chardet)
  emit/
    markdown.py   # write .md with lightweight frontmatter
    okf.py        # write OKF v0.2 concept
    okf_index.py  # per-directory index.md
    manifest.py   # run-level manifest.json

tests/             # pytest, 43 tests
  conftest.py     # shared fixtures
  test_walk.py
  test_router.py
  test_normalize.py
  test_emit.py
  test_run.py
  test_lint.py
  fixtures/
    sample.xlsx   # hand-rolled valid XLSX

docs/              # 9 doc files — see README.md "Documentation" table
scripts/
  verify.sh       # post-install sanity check

install.sh         # macOS / Linux / WSL one-line installer
install.ps1        # Windows PowerShell installer
```

## Output shape (default)

When run on `./inbox` with `--format both`:

```
./out/
├── manifest.json                  # run summary: {path, sha256, status, engine, format}
├── _md/                           # plain Markdown (one file per source)
│   ├── notes.docx.md
│   └── q3.pdf.md
└── okf/                           # OKF v0.2 bundle (one concept per source)
    ├── index.md                   # auto-generated directory index
    ├── notes.docx.md              # extension stripped in OKF names
    └── q3.pdf.md
```

`--format md` skips `okf/`. `--format okf` skips `_md/`.

## Trust stance (NEVER violate)

When the CLI auto-converts, it sets:

- `type: Document` (OKF required)
- `status: unverified`
- `generated: human:<user>@<host>` from `$USER` / `$USERNAME`
- `verified: human:pending`
- `stale_after: <today + 180d>`
- `sources: [{uri: file://..., sha256: ...}]`

**Never auto-claim review.** Auto-conversion is not review. A human must
explicitly run `headcleaner review` (planned in ENHANCEMENTS.md #3) to
change `verified: human:pending` to `verified: human:reviewed`.

## Adding a new format

See `docs/CONTRIBUTING.md` → "Adding a new file format" for the full
walk-through. TL;DR:

1. Drop a module in `src/headcleaner/engines/<format>.py`
2. Implement `Adapter` (one `extract()` method + `name` + `extensions`)
3. Register it in `src/headcleaner/router.py:_ADAPTERS`
4. Add a row to `docs/FORMAT_MATRIX.md`
5. Add a fixture in `tests/fixtures/` and a round-trip test
6. Add an entry to `docs/CHANGELOG.md`

## Color discipline

When adding UI strings, never use red or yellow. The headcleaner palette
is **neon cyan + neon pink + neon purple** only. Status colors map as:

- ok / success → neon cyan
- active / running → neon pink
- info → neon purple
- failed → neon pink (bright, not red)
- skipped / muted → grey

See `src/headcleaner/theme.py` for the constants.
