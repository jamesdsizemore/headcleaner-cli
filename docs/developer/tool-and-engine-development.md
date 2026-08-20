# Tool and engine development

This page walks through adding a new adapter to headcleaner. The recipe is the same whether you are adding support for a new file format, integrating an existing tool, or registering a third-party plugin.

## When to add an adapter

Add a new adapter when headcleaner does not yet support a file format you care about, or when an existing adapter does not produce good output for your inputs. The threshold is "I have a corpus I want to convert and the current output is not good enough." Below that threshold, prefer filing an issue and contributing improvements to the existing adapter.

## The Adapter contract

Every adapter implements a small protocol defined in `src/headcleaner/engines/base.py`:

```python
class Adapter(Protocol):
    name: str
    extensions: tuple[str, ...]

    def extract(self, path: Path, *, source_uri: str, source_sha256: str) -> AdapterResult: ...
```

`name` is a stable identifier used in the manifest, the graph, and the sync state. `extensions` is the tuple of file extensions the adapter handles (lowercase, with leading dot). `extract` takes a file path plus the source URI and SHA-256 that have already been computed by the walker. It returns an `AdapterResult`.

## The AdapterResult

```python
@dataclass
class AdapterResult:
    title: str
    body_md: str
    elements: list[Element]
    frontmatter: dict[str, Any]
    metadata: dict[str, Any]
    warnings: list[str]
```

The fields:

- `title` is the document's title, extracted from the source if the format supports it. Fall back to the source filename stem.
- `body_md` is the readable Markdown body. Emitters project this to the `_md/` and `okf/` outputs. Adapters should produce clean, well-structured Markdown.
- `elements` is the typed element sequence. If the adapter cannot produce typed elements, it may leave this empty and the normalization layer will synthesize a paragraph element from `body_md`.
- `frontmatter` is the OKF-style frontmatter dict. The normalization layer merges this with the trust defaults.
- `metadata` is the adapter-specific metadata (page count, sheet names, etc.). Used by reports and diagnostics.
- `warnings` is a list of human-readable warning strings. These become per-file warnings in the manifest.

## Worked example: adding a CSV adapter

This walkthrough adds an adapter for CSV files. The adapter reads CSV with the standard library and produces a Markdown table plus typed table elements.

### Step 1 — Create the module

Create `src/headcleaner/engines/csv_adapter.py` with the adapter class:

```python
from __future__ import annotations
import csv
from pathlib import Path
from typing import Any

from .base import AdapterResult
from ..model import Element


class CsvAdapter:
    name = "csv"
    extensions = (".csv",)

    def extract(
        self,
        path: Path,
        *,
        source_uri: str,
        source_sha256: str,
    ) -> AdapterResult:
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.reader(handle)
            rows = [row for row in reader]
        if not rows:
            return AdapterResult(
                title=path.stem,
                body_md="",
                elements=[],
                frontmatter={},
                metadata={"row_count": 0},
                warnings=["empty CSV"],
            )
        headers, *body_rows = rows
        # Build Markdown table
        header_line = "| " + " | ".join(headers) + " |"
        separator = "| " + " | ".join("---" for _ in headers) + " |"
        body_lines = ["| " + " | ".join(row) + " |" for row in body_rows]
        body_md = "\n".join([header_line, separator, *body_lines])
        # Build typed table element
        element = Element.create(
            source_sha256,
            "table",
            0,
            body_md,
        )
        return AdapterResult(
            title=path.stem,
            body_md=body_md,
            elements=[element],
            frontmatter={},
            metadata={"row_count": len(body_rows), "column_count": len(headers)},
            warnings=[],
        )
```

### Step 2 — Register the adapter

Open `src/headcleaner/router.py` and add the import plus the registry entry:

```python
from .engines.csv_adapter import CsvAdapter

_ADAPTERS: tuple[Adapter, ...] = (
    OfficeCliAdapter(),
    LibreOfficeAdapter(),
    PdfPlumberAdapter(),
    TesseractAdapter(),
    BeautifulSoupAdapter(),
    TxtAdapter(),
    EmlAdapter(),
    MsgAdapter(),
    PstAdapter(),
    CsvAdapter(),  # <-- new
)
```

The order matters: the router walks the tuple in order and uses the first adapter whose `extensions` match. Put your adapter after the built-ins unless you have a reason to override.

### Step 3 — Write the round-trip test

Create `tests/test_csv_adapter.py`. The minimum coverage is:

- A passing fixture: a CSV file is converted to Markdown with the expected table structure.
- An empty file: produces an empty body and a warning.
- A file with quoted fields: preserves the quoting in the output.
- A file with newlines in fields: preserves the newlines.

A typical passing test:

```python
def test_csv_adapter_emits_markdown_table(tmp_path: Path) -> None:
    from headcleaner.engines.csv_adapter import CsvAdapter

    source = tmp_path / "data.csv"
    source.write_text("name,age\nAlice,30\nCarol,25\n", encoding="utf-8")
    adapter = CsvAdapter()
    result = adapter.extract(source, source_uri=source.as_uri(), source_sha256="a" * 64)
    assert "| name | age |" in result.body_md
    assert "| Alice | 30 |" in result.body_md
    assert result.metadata["row_count"] == 2
```

### Step 4 — Add a row to the format matrix

Add a row to `docs/schemas/FORMAT_MATRIX.md` (the archived version is preserved at `docs/_archive/legacy-docs/FORMAT_MATRIX.md`; the new matrix lives at `docs/reference/engine-directory.md`). The row should include the format, the engine name, the file extensions, and any optional tools required.

### Step 5 — Add a changelog entry

Add an entry to `CHANGELOG.md` (preserved in the archive) describing the new adapter and any user-visible behavior changes.

## Plugin adapters

If you are writing an adapter for distribution as a third-party plugin, the steps are slightly different:

- Create a Python package that depends on headcleaner.
- Implement the adapter class with the same contract.
- Register it through the `headcleaner_plugin` entry-point group in your package's `pyproject.toml`.
- Document the install, the supported versions, and the diagnostic output.

The headcleaner plugins documentation (in the archive) covers the entry-point format in detail. The plugins loader is in `src/headcleaner/plugins.py`.

## Common pitfalls

The pitfalls most new adapter authors hit:

- **Trust defaults.** Adapters should not set `verified: human:reviewed`. The normalization layer sets the trust defaults; the adapter's frontmatter should only contain format-specific fields.
- **Element IDs.** If you produce typed elements, use `Element.create(source_sha256, kind, ordinal, text)` so the IDs are deterministic. Random UUIDs break reproducibility.
- **Path handling.** Use `pathlib.Path` and forward-slash POSIX separators for any string you put in the manifest. Host-specific separators break cross-platform runs.
- **Encoding.** Default to UTF-8 unless the format requires otherwise. Use `chardet` for byte-source detection.
- **Large files.** Stream large sources rather than loading them entirely. The adapter contract does not require streaming, but doing so keeps memory bounded.

## What to read next

The [routing and fallback developer guide](routing-and-fallback.md) covers the engine plan and fallback semantics. The [configuration development guide](configuration-development.md) covers the policy file format. The [testing guide](testing-guide.md) explains the test layers and fixtures.