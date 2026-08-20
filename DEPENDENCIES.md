# Dependencies

`pyproject.toml` and `uv.lock` are the authoritative dependency records. This page is the human-facing map and must be updated whenever either dependency intent or pinning policy changes.

## Runtime dependencies

The core runtime uses BeautifulSoup/lxml for HTML, pdfplumber and pypdf for PDF, chardet/markdownify/PyYAML/tomli-w for normalization and output, Click/Rich/Textual for the CLI/TUI, extract-msg for email, watchfiles for monitoring, ebooklib/striprtf/odfpy for formats, and FastAPI/Uvicorn/Jinja2 for serving. Phase 2 additionally uses RapidFuzz, Sentence Transformers, Qdrant client, and MCP.

## Optional and development groups

- `ocr`: pytesseract and Pillow.
- `pst`: libpff-python.
- `odf`, `epub`: format-specific helpers.
- `dev`: all2md, Babel, `httpx` (supported in-process ASGI transport for serve tests), jsonschema, office-oxide, pytest, and Ruff.

## Change policy

1. Explain why a dependency is necessary in the backlog and development history.
2. Update `pyproject.toml` and regenerate `uv.lock` with uv; do not hand-edit the lockfile.
3. Record exact pins in [PINS.md](PINS.md), then run `uv lock --check` and relevant tests.
4. Audit the user, integration, developer, and compatibility docs before commit.
