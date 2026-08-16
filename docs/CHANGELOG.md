# Changelog

All notable changes to headcleaner are documented here. The format is
based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and
this project adheres to [Semantic Versioning](https://semver.org/).

## [0.1.0] — 2026-08-16

First public release. Rebranded from `doc-ingest` to `headcleaner`.

### Added

- **Conversion pipeline** (`headcleaner convert`)
  - Walks a folder recursively, skipping hidden files and VCS internals
  - Dispatches by extension to one of four active adapters:
    - `officecli` — DOCX, XLSX, PPTX (via the OfficeCLI binary)
    - `pdf` — PDF text-layer extraction via pdfplumber (--ocr flag for Tesseract)
    - `html` — HTML/HTM via BeautifulSoup + markdownify
    - `txt` — TXT via chardet (encoding auto-detected)
  - Emits `_md/` (plain Markdown) and/or `okf/` (OKF v0.2 bundle) plus `manifest.json`
  - Auto-generates `okf/index.md` per directory (OKF §8 progressive disclosure)
- **OKF v0.2 trust family** with honest defaults:
  - `status: unverified`
  - `verified: human:pending`  (never auto-claims review)
  - `generated: human:<user>@<host>` (OKF §7 actor convention)
  - `stale_after: <today + 180d>`
  - `sources: [{uri: file://..., sha256: ...}]` (OKF v0.2 §5.1 provenance)
- **TUI** (`headcleaner convert --tui`, default when stdout is a TTY)
  - omp-inspired visual language (rounded box-drawing panels, powerline separators)
  - Neon palette: cyan primary, pink active, purple info
  - Lightning-bolt jar (⚡) brand mark in header + segmented footer
  - Live progress bar, per-file engine attribution, animated spinner
- **Plain mode** (`headcleaner convert --no-tui`)
  - One progress line per file on stderr, exit code 0/1
  - Designed for CI / pipes / scripts
- **Post-conversion linter** (`headcleaner lint <DIR>`)
  - OKF structural rules: required `type`, valid `resource` URI, valid SHA-256, sources[] shape
  - Markdown body rules: orphan code fences, heading hierarchy, line length
  - `--strict` treats warnings as errors; exit code 1 on any error
- **Other subcommands**:
  - `headcleaner templates` — list supported formats
  - `headcleaner agents` — show engine install status
- **Install paths** (documented in `docs/INSTALL.md`):
  - `curl | bash` and `irm | iex` one-liners
  - `uv tool install headcleaner`
  - `pipx install headcleaner`
  - `pip install --user`
  - From source
- **CI** — GitHub Actions matrix on Python 3.12 + 3.13, OfficeCLI installed
  via npm, full pytest on push and PR.

### Engine coverage at v0.1.0

| Format | Engine | Library |
|---|---|---|
| `.docx`, `.xlsx`, `.pptx` | officecli | @officecli/officecli (binary) |
| `.pdf` | pdf | pdfplumber |
| `.html`, `.htm` | html | beautifulsoup4 + markdownify |
| `.txt` | txt | chardet |

### Tests

43 pytest tests covering walker, router, normalize, emitters, full
pipeline, and linter rules. Suite runs in ~5 seconds.

### Known gaps (planned for v1.0)

See `docs/ENHANCEMENTS.md` for the full 25+ item roadmap. Highlights:

- `.md`, `.csv`, `.json`, `.epub`, `.rtf`, `.odt`/`.ods`/`.odp`,
  `.eml`, `.msg`, `.pst`, legacy `.doc`/`.xls`/`.ppt`
- `headcleaner watch` for live folder monitoring
- `headcleaner serve` for live OKF bundle browser
- Pluggable trust policy (so orgs can require `verified: human:reviewed`)
- Cross-concept link inference
- Homebrew formula

### Changed

- Renamed project from `doc-ingest` to `headcleaner`. The Python package
  is now `headcleaner`; the console script is `headcleaner`; the
  linter is `headcleaner-lint` (also reachable as `headcleaner lint`).

### Removed

- The old `doc-ingest` console script. Users upgrading should
  uninstall the old package first:
  ```
  uv tool uninstall doc-ingest
  uv tool install headcleaner
  ```

---

## Pre-history

Versions ≤ 0.0.x lived under the `doc-ingest` name in
`~/developer/doc-ingest`. They are no longer supported. See git history
of that repo (now removed; this project is its successor).
