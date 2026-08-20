# Coding standards

This page documents the coding standards every headcleaner contribution is expected to follow. The standards cover Python style, type annotations, naming, documentation, error handling, and the project's visual identity.

## Python style

Headcleaner uses Ruff for linting and formatting. The configuration is in `pyproject.toml`. The two commands every contributor should run before opening a pull request are:

```bash
unset PYTHONPATH
uv run --no-sync --python 3.13 ruff check .
uv run --no-sync --python 3.13 ruff format .
```

The first command checks for lint violations; the second applies the formatter. The formatter is opinionated; do not argue with it. If you disagree with a formatting choice, the right place to discuss it is the `pyproject.toml` configuration, not your code.

## Type annotations

Headcleaner's code is fully type-annotated. The annotations use PEP 604 syntax (`X | None`) for unions and the `from __future__ import annotations` directive at the top of each module. Generic types use the built-in syntax (`list[str]`, `dict[str, int]`) on Python 3.9+.

Every public function has a return type annotation. Every public function's parameters have type annotations. Private helpers may use less strict annotations, but the convention is to annotate everything.

## Naming

The naming conventions:

- **Modules**: lowercase with underscores (`chunking.py`, `embeddings.py`).
- **Classes**: `PascalCase` (`CanonicalDoc`, `EmbeddingProvider`).
- **Functions and methods**: `snake_case` (`rebuild_index`, `embed`).
- **Variables**: `snake_case` (`source_sha256`, `chunk_count`).
- **Constants**: `UPPER_SNAKE_CASE` (`CHUNKING_VERSION`, `INDEX_SCHEMA_VERSION`).
- **Private members**: leading underscore (`_init`, `_hash`).

Names should be descriptive. A name like `x` is a smell; `source_path` is fine; `current_chunk_ordinal` is better when there is ambiguity.

## Dataclasses over dicts

Headcleaner uses dataclasses for every structured value that crosses a module boundary. The benefit is type safety, validation through `__post_init__`, and stable serialization through `asdict` or `to_dict`.

If you find yourself building a `dict[str, Any]` to pass data between modules, stop and define a dataclass. The dataclass is the contract.

## Immutability

Dataclasses are `frozen=True` by default. This is intentional: immutability prevents accidental mutation across module boundaries, makes values hashable, and makes test assertions simpler (no need to copy before comparison).

If you need to modify a frozen dataclass, use `dataclasses.replace` to produce a new value. Never mutate a frozen dataclass in place.

## Error handling

Headcleaner distinguishes between three kinds of errors:

- **Validation errors**: `ValueError`. Use for invalid arguments, malformed input, malformed configuration.
- **Permission errors**: `PermissionError` (or the subclass `NetworkPermissionError`). Use for operations that require explicit permission that has not been granted.
- **Internal errors**: `RuntimeError` (or a subclass). Use for unexpected conditions that suggest a bug.

The CLI converts `ValueError` to a `ClickException` with exit code 2. `RuntimeError` exceptions produce exit code 2 as well but with a different message. `PermissionError` exceptions produce exit code 1 with a clear "permission required" message.

## Logging

Headcleaner uses the standard `logging` module. The convention:

- Use `logger = logging.getLogger(__name__)` at the top of each module.
- Log at INFO for normal lifecycle events (start, finish, key milestones).
- Log at WARNING for recoverable conditions that the user should know about.
- Log at ERROR for unexpected conditions that suggest a bug.
- Log at DEBUG for detailed information useful for debugging.

Do not print to stdout or stderr from production code. The CLI output is structured (human-readable lines, or JSON with `--json`); logging goes to stderr.

## Documentation

Every public function should have a docstring. The docstring should describe what the function does, what it returns, and what it raises. The convention is the Google-style docstring:

```python
def rebuild_index(bundle_root: Path) -> Path:
    """Atomically rebuild the search index from canonical chunks.

    Returns the path to the rebuilt database. Raises ValueError if a
    chunk references a concept that does not exist in the bundle.
    """
```

Private helpers do not need docstrings, but a one-line comment explaining intent is welcome.

## Visual identity

Headcleaner's CLI and TUI use a strict color palette: neon cyan, neon pink, and neon purple. No red, no yellow, no warm whites. The constants are in `src/headcleaner/theme.py`. The brand mark is a lightning-bolt jar (⚡).

When adding UI strings, never use red or yellow. Map status to colors as follows:

- `ok` and success → neon cyan
- active and running → neon pink
- info → neon purple
- failed → bright pink (not red)
- skipped and muted → grey

The palette is enforced by convention; nothing in the codebase refuses a non-palette color. Be disciplined.

## Documentation style

Two audiences, two styles. The user-facing pages use narrative prose, plain English, and tutorial-shaped explanations. The developer-facing pages use contract-shaped references, code blocks, and ASCII diagrams. The two styles must not be mixed on the same page.

The full style guide is in `docs/maintainers/documentation-style-guide.md`. The voice discipline for user pages is "warm, clear, confident, product-oriented." The voice discipline for developer pages is "comprehensive, contract-shaped, no narrative filler."

## What to read next

The [contributor onboarding guide](contributor-onboarding.md) covers the platform-specific setup. The [architecture developer guide](architecture.md) explains how the modules fit together. The [testing guide](testing-guide.md) covers the test layers and the RED/GREEN cycle.