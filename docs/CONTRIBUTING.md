# Contributing to headcleaner

Thanks for your interest. This guide covers the development workflow,
how to add a new file format, and the project's coding conventions.

## Code of conduct

Be kind. Disagree on substance, never on tone. Review PRs for code,
not for people.

## Development setup

```bash
git clone https://github.com/local/headcleaner-cli
cd headcleaner-cli

# Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

# Sync deps
uv sync

# Run the test suite
uv run pytest
```

You'll also need `officecli` for the Office-engine tests to run end-to-end:

```bash
npm install -g @officecli/officecli
```

Tests that need it will `pytest.skip()` if the binary is missing, so the
suite stays green on hosts without Node/npm.

## Project layout

```
src/headcleaner/
├── __init__.py
├── cli.py          # Click CLI entrypoint
├── tui.py          # Textual TUI
├── theme.py        # ANSI colors + box-drawing symbols
├── walk.py         # folder walker
├── router.py       # extension → adapter dispatch
├── normalize.py    # CanonicalDoc
├── run.py          # pipeline orchestrator
├── lint.py         # post-conversion linter
├── engines/
│   ├── base.py
│   ├── officecli.py
│   ├── pdf.py
│   ├── html.py
│   └── txt.py
└── emit/
    ├── markdown.py
    ├── okf.py
    ├── okf_index.py
    └── manifest.py

tests/                  # pytest, 43 tests
docs/                   # INSTALL, USAGE, ARCHITECTURE, FORMAT_MATRIX, OKF_NOTES, FAQ, TROUBLESHOOTING, CONTRIBUTING, CHANGELOG, ENHANCEMENTS
```

## Adding a new file format

The most common kind of contribution. Walk-through using a hypothetical
`.eml` adapter as an example.

### Step 1 — pick the right library

For `.eml` (RFC 5322 email), `email` is stdlib — no new dep needed.
For `.docx/.xlsx/.pptx`, you already have OfficeCLI. For everything
else, check the FORMAT_MATRIX first.

### Step 2 — write the adapter

```python
# src/headcleaner/engines/eml.py
"""EML adapter — RFC 5322 email files."""
from __future__ import annotations

import email
from email import policy
from pathlib import Path

from .base import Adapter


class EmlAdapter(Adapter):
    name = "eml"
    extensions = {".eml"}

    def extract(self, source: Path) -> dict:
        with source.open("rb") as f:
            msg = email.message_from_binary_file(f, policy=policy.default)
        subject = msg.get("Subject", "")
        from_ = msg.get("From", "")
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    body = part.get_content()
                    break
        else:
            body = msg.get_content()

        md = f"# {subject or source.stem}\n\n**From:** {from_}\n\n{body}"
        return {
            "title": subject or source.stem,
            "body_md": md,
            "metadata": {"engine": self.name, "source_format": ".eml"},
            "attachments": [],
        }
```

### Step 3 — register in `router.py`

```python
from .engines.eml import EmlAdapter

_ADAPTERS: list[Adapter] = [
    TxtAdapter(),
    HtmlAdapter(),
    PdfAdapter(),
    OfficeCLIAdapter(),
    EmlAdapter(),   # ← add
]
```

### Step 4 — add a row to `docs/FORMAT_MATRIX.md`

Either the v0.1.0 "shipped" section (if it's in v0.1) or the v1.0 roadmap
section.

### Step 5 — write tests

```python
# tests/test_router.py
def test_eml_adapter_extracts_headers_and_body(eml_path: Path) -> None:
    out = EmlAdapter().extract(eml_path)
    assert "Subject" in out["body_md"] or out["title"]
    assert "From:" in out["body_md"]
```

### Step 6 — update optional dependencies if needed

If you added a new PyPI dep, add it to `pyproject.toml`:

```toml
dependencies = [
    ...
    "beautifulsoup4>=4.12",
]
```

Or to optional-dependencies if it's heavy:

```toml
[project.optional-dependencies]
eml = []   # ← only if you need a non-stdlib helper
```

### Step 7 — verify

```bash
uv run pytest
uv run headcleaner templates   # confirm the new extension is listed
```

## Coding conventions

- **Python 3.12 only.** No `from __future__ import annotations` for typing;
  but DO use `from __future__ import annotations` in module headers for
  forward references (matches the rest of the codebase).
- **Type hints on every public function.** Use `pathlib.Path` over `str`
  for filesystem paths.
- **Dataclasses for value objects.** No Pydantic, no attrs — stdlib
  dataclasses are enough.
- **Match the surrounding code style.** 100-char line limit, Black-ish
  formatting (we don't run Black in CI, but be consistent).
- **No LLM calls.** `headcleaner` is deterministic. If you need an LLM,
  add it as an optional adapter behind a flag.
- **No background services.** No daemons, no schedulers. If you need
  one, build a separate CLI subcommand.

## Commit messages

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(engines): add .eml adapter
fix(lint): don't crash on missing frontmatter
docs: add ENHANCEMENTS.md
test: cover orphan-fence rule
chore: bump ruff
```

## Pull request workflow

1. Fork the repo, branch from `main`.
2. Make your change. Add tests.
3. Run `uv run pytest` — must stay green.
4. Run `uv run ruff check .` (if you have ruff installed).
5. Open a PR with a description of what changed and why.
6. Expect at least one round of review before merge.

## Reporting bugs

Open an issue with:
- `headcleaner --version` output
- `headcleaner agents` output
- A minimal reproducible input file (or a description of the format)
- The exact command you ran
- The output you expected vs. what you got

## Security

Found a vulnerability? Email jamesdsizemore@gmail.com instead of opening
a public issue. Allow 48 hours for an acknowledgment before going public.

## License

By contributing, you agree your contributions will be licensed under
Apache-2.0 (the project's license).
