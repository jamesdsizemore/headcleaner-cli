# FORMAT_MATRIX

> Every input extension → engine → library → fallback path. This is the contract
> between the walker and the emitters. Add a row here before adding a new engine.

## Legend

- **Engine:** the abstraction name used in `router.py` and `engines/`.
- **Library:** the Python import or external binary that does the work.
- **Output:** the canonical Markdown body produced after normalization.
- **Required:** ✓ = must be installed; ○ = optional (format silently skipped if missing); ✗ = no install needed.

## Matrix

### v0.1.0 (shipped)

| # | Extensions | Engine | Library | Required | Output | Fallback |
|---|---|---|---|---|---|---|
| 1 | `.docx` | `officecli` | `@officecli/officecli` (binary) | ✓ | full HTML → MD | none |
| 2 | `.xlsx` | `officecli` | `@officecli/officecli` (binary) | ✓ | full HTML → MD (tables) | none |
| 3 | `.pptx` | `officecli` | `@officecli/officecli` (binary) | ✓ | full HTML → MD | none |
| 4 | `.pdf` | `pdf` | `pdfplumber` | ✓ | text-layer MD; tables preserved | `--ocr` opt-in: `pytesseract` |
| 5 | `.html`, `.htm` | `html` | `beautifulsoup4`, `markdownify` | ✓ | semantic MD (h1-h6, p, ul, ol, code, pre, blockquote, table) | none |
| 6 | `.txt` | `txt` | `chardet` + stdlib | ✓ | raw text in fenced block | none |
| 7 | `.md`, `.markdown` | `md` | stdlib | ✓ | pass-through + frontmatter inject | none |
| 8 | `.csv`, `.tsv` | `csv` | stdlib `csv` | ✓ | GFM table | none |
| 9 | `.json` | `json` | stdlib `json` | ✓ | fenced ```json block + pretty-printed | none |
| 10 | `.eml` | `eml` | stdlib `email` | ✓ | headers + body MD + attachments | none |
| 11 | `.pst` | `pst` | `libpff-python` (optional) | ○ | item count stub (full extraction is a Batch 4 task) | best-effort: warn + skip if lib missing |
| 12 | `.doc`, `.xls`, `.ppt` | `legacy_office` | (none shipped) | ○ | clear error: convert with LibreOffice first | none |

### v1.0 roadmap (planned, not yet implemented)

| # | Extensions | Engine | Library | Required | Notes |
|---|---|---|---|---|---|
| 13 | `.epub` | `epub` | `ebooklib` | ✓ | per-chapter MD, joined with `---` |
| 14 | `.rtf` | `rtf` | `striprtf` | ✓ | plain text in fenced block |
| 15 | `.odt`, `.ods`, `.odp` | `odf` | `odfpy` | ✓ | ODT → MD; ODS → GFM table; ODP → "see source: <uri>" |
| 16 | `.msg` | `msg` | `extract-msg` | ✓ | headers + body MD |

## Engine selection

The router matches by extension. Unknown extensions are skipped (logged, not failed). To extend:

1. Add a row above.
2. Add `src/headcleaner/engines/<name>.py` implementing the `Adapter` interface.
3. Register it in `src/headcleaner/router.py:_ADAPTERS`.
4. Add a fixture in `tests/fixtures/`.
5. Add a round-trip test in `tests/test_router.py`.
6. Add an entry to `docs/CHANGELOG.md`.

## Engine detail

### officecli (DOCX/XLSX/PPTX)

OfficeCLI is a single binary installed via npm (`npm install -g @officecli/officecli`).
The CLI shells out to:

```
officecli view <file> html
```

…then post-processes the HTML with BeautifulSoup to strip OfficeCLI's
render scaffolding (page wrappers, span block markers, etc.) before
markdownifying.

Verification (2026-08-16):
- `officecli --version` → `1.0.144`
- `officecli view sample.docx html` → real HTML with `<h1>`, `<p>` tags and content

### pdf (text-layer via pdfplumber)

`pdfplumber.open(file)` per page:
1. `extract_tables()` → emit as GFM tables
2. `extract_text()` → emit as paragraphs

If a page has no extractable text and `--ocr` is on, pytesseract runs
on the page image (slow). Without `--ocr`, the page is recorded in
`metadata.image_only_pages` and a warning is added to the body.

Encrypted PDFs: error out cleanly with a clear message.

### html (BeautifulSoup + markdownify)

1. Parse with `BeautifulSoup(raw, "lxml")`.
2. Strip non-content tags: `script`, `style`, `nav`, `header`, `footer`, `aside`, `noscript`, `iframe`, `form`.
3. Extract title from `<main h1>`, `<article h1>`, or `<h1>` (first found); fall back to `<title>`.
4. markdownify with `heading_style="ATX"`, `bullets="-"`, `tables=True`.

### txt (chardet + read)

1. `chardet.detect()` on first 64KB
2. Read with errors='replace' (never crash on bad bytes)
3. Wrap in fenced ```text block (preserves leading whitespace)

## Engine caveats

### PST

`libpff-python` ships binary wheels for Windows x64 and macOS arm64 only.
On Linux it's source-only and requires `libpff` headers. We mark it
optional and gracefully skip if the import fails. Users on Linux can
install `libpff-python` from source or convert their PST to MSG with
`readpst -e` first.

### OCR

OCR is **off by default**. Enable per-run with `--ocr` (flag flips on
`pytesseract`). OCR requires:

- `pytesseract` Python wrapper
- Tesseract binary on PATH (`brew install tesseract`, `choco install tesseract`, etc.)

OCR is slow (~1 sec per page on commodity hardware). Keep it opt-in.

### Legacy Office formats (`.doc`, `.xls`, `.ppt`)

Pre-2007 binary formats are NOT supported by OfficeCLI. Options:

- Use LibreOffice headless: `libreoffice --convert-to docx old.doc`
  (produces a `.docx` you can then convert with headcleaner)
- Use `antiword` for `.doc` and `xlrd` for `.xls` (third-party)

ENHANCEMENTS.md #18 plans to ship a `libreoffice` shim adapter.
