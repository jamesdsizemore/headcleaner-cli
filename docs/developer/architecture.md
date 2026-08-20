# Architecture

This page describes headcleaner's architecture at the module level. It explains the layers, the data flow between them, and the contracts that hold the layers together. If you are new to the codebase, this is the page that orients you before you read source.

## The layers

Headcleaner's source is organized into four layers. Each layer has a narrow responsibility and a small set of dependencies on the layers below it.

### Layer 1: Adapters

The adapters layer is the bottom of the stack. Each adapter knows how to read one specific file format and produce a normalized output. Adapters live in `src/headcleaner/engines/` and follow the `Adapter` protocol defined in `src/headcleaner/engines/base.py`.

The adapters headcleaner ships with cover the formats listed in the [engine directory](../reference/engine-directory.md): Office documents (via OfficeCLI), legacy Office (via LibreOffice), PDFs (via pdfplumber), OCR (via Tesseract), HTML (via BeautifulSoup), plain text, and email (`.eml`, `.msg`, `.pst`).

Adapters are the only layer that talks to external processes. Every other layer is in-process.

### Layer 2: Routing

The routing layer is the bridge between the adapters and the rest of the pipeline. It lives in `src/headcleaner/router.py` and `src/headcleaner/engine_plan.py`. The router picks the right adapter based on file extension and capability, with optional fallback to the next available adapter on failure.

The router does not call adapters directly. It builds a deterministic plan that records which adapters will be tried, in what order, and with what fallback rules. The plan is part of the audit trail and is reflected in the run manifest.

### Layer 3: Normalization and canonicalization

The normalization layer takes adapter output and produces a `CanonicalDoc`. The canonicalization is the heart of the system: every format-specific quirk is reduced to a small set of typed elements (`heading`, `paragraph`, `list`, `table`, `image`, `code`, `quote`, `attachment_ref`, `page_break`) plus frontmatter and metadata.

This layer lives in `src/headcleaner/normalize.py` and `src/headcleaner/model.py`. The `Element` dataclass is the typed representation; the `CanonicalDoc` is the per-source container.

### Layer 4: Pipeline and derivatives

The pipeline layer is the top of the stack. It owns the run lifecycle: walking the input folder, orchestrating the routing and normalization, emitting the canonical output as Markdown and OKF, and then emitting the rebuildable derivatives (chunks, search index, knowledge graph, dedupe analysis, claims analysis, sync state).

The pipeline lives in `src/headcleaner/run.py`. The emission helpers live in `src/headcleaner/emit/`. The CLI surface that drives the pipeline lives in `src/headcleaner/cli.py`.

## The data flow

A conversion run follows a fixed sequence:

```text
   INPUT folder                  OUTPUT folder
        |                              ^
        | walk                         | write
        v                              |
   +-----------+   route   +-------+   |
   |  walk.py  | ------->  |router |   |
   +-----------+           +-------+   |
                              | adapter|
                              v         |
                          +-------+     |
                          |engine |     |
                          +-------+     |
                              | extract |
                              v         |
                          +---------+   |
                          | normalize|  |
                          +---------+   |
                              | CanonicalDoc
                              v         |
                          +---------+   |
                          |   emit  | --> manifest.json, REPORT.md
                          +---------+   | --> _md/, okf/
                              |         | --> chunks.jsonl, graph.jsonl,
                              |         |     duplicate-families.json,
                              |         |     claim-review.json
                              v
                          +-----------+
                          | derivatives|
                          +-----------+
```

The pipeline writes to the output folder at three points: the manifest and report (top-level), the canonical Markdown and OKF (`_md/` and `okf/`), and the rebuildable derivatives (which live inside the OKF bundle).

## The contracts

Each layer exposes a contract that the layer above depends on. The contracts are small and stable; they are the reason headcleaner can evolve without breaking downstream consumers.

### The Adapter contract

```python
class Adapter(Protocol):
    name: str
    extensions: tuple[str, ...]

    def extract(self, path: Path, *, source_uri: str, source_sha256: str) -> AdapterResult: ...
```

The contract is: an adapter takes a file path and produces an `AdapterResult` containing the body Markdown, the typed elements, the metadata, and any warnings. Adapters do not write to the output folder; they produce in-memory data.

The contract is documented in detail in `src/headcleaner/engines/base.py`.

### The Element contract

```python
@dataclass(frozen=True)
class Element:
    id: str
    kind: str  # heading | paragraph | list | table | image | code | quote | attachment_ref | page_break
    ordinal: int
    text: str
    source_location: SourceLocation | None
    attributes: dict[str, Any]
```

The contract is: an element has a deterministic ID derived from the source SHA, kind, ordinal, and normalized content. The kind is one of nine values. The source location is `{page, start, end}` with nullable members. The attributes are JSON-safe.

The full contract is in `src/headcleaner/model.py`.

### The CanonicalDoc contract

The `CanonicalDoc` is the per-source container. It carries the source metadata (URI, SHA, size, format, engine), the body Markdown, the typed elements, and the trust defaults. The trust defaults set `verified: human:pending` and `stale_after: <today + 180d>` for every auto-converted doc.

### The Pipeline contract

The pipeline (`run_pipeline`) takes a `RunOptions` and returns a `RunRecord`. The options carry the input folder, the output folder, the format, the OCR settings, the dedupe threshold, and the policy suppressions. The record carries the per-file results, the run metadata, the engine summary, the totals, and the paths to the emitted derivatives.

The contract is documented in `src/headcleaner/run.py`.

## What lives where

The source tree at a glance:

```
src/headcleaner/
  __init__.py
  cli.py          # Click entrypoint (headcleaner command)
  tui.py          # Textual TUI (legacy)
  theme.py        # ANSI colors + box-drawing symbols
  walk.py         # folder walker
  router.py       # ext → engine dispatch
  engine_plan.py  # deterministic plan + fallback
  normalize.py    # adapter output → CanonicalDoc
  model.py        # Element, CanonicalDoc, typed element model
  run.py          # pipeline orchestrator
  lint.py         # post-conversion linter
  chunking.py     # deterministic cited chunks (Phase 2)
  index.py        # SQLite FTS5 local search index (Phase 2)
  search.py       # shared parameterized search API (Phase 2)
  embeddings.py   # embedding providers + vector cache (Phase 2)
  graph.py        # evidence-linked knowledge graph (Phase 2)
  dedupe.py       # exact + near-duplicate families (Phase 2)
  diff.py         # element-aware diff (Phase 2)
  claims.py       # stale + conflict candidates (Phase 2)
  sync.py         # rename/deletion-safe sync (Phase 2)
  policy.py       # policy TOML parsing + evaluation
  engines/
    base.py       # Adapter ABC
    officecli.py  # DOCX/XLSX/PPTX
    pdf.py        # PDF (pdfplumber, opt-in pytesseract)
    html.py       # HTML/HTM (BeautifulSoup + markdownify)
    txt.py        # TXT (chardet)
    eml.py        # email messages
    msg.py        # Outlook .msg
    pst.py        # Outlook .pst
  emit/
    markdown.py   # write .md with lightweight frontmatter
    okf.py        # write OKF v0.2 concept
    okf_index.py  # per-directory index.md
    manifest.py   # run-level manifest.json
    report.py     # run-level REPORT.md
```

Every module has a focused responsibility. The contracts between modules are small. The dependencies between modules flow downward only — adapters do not import from `run.py`, `run.py` does not import from `cli.py`, and so on.

## What to read next

The [canonical model developer guide](canonical-model.md) documents every dataclass. The [tool and engine development guide](tool-and-engine-development.md) walks through adding a new adapter. The [source tree developer guide](source-tree.md) documents every test family and fixture.