# headcleaner Architecture

How the pieces fit together, where to extend, and how the data flows.

## Bird's-eye view

```
                          headcleaner convert INPUT_DIR
                                    │
                                    ▼
   ┌──────────────────────────────────────────────────────────────┐
   │                       cli.py (Click)                          │
   │  parses flags → builds RunOptions → picks TUI or plain mode   │
   └──────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
   ┌──────────────────────────────────────────────────────────────┐
   │                       run.py (orchestrator)                   │
   │  walk → route → normalize → emit (md + okf + manifest)        │
   └──────────────────────────────────────────────────────────────┘
        │              │              │              │
        ▼              ▼              ▼              ▼
   ┌─────────┐   ┌──────────┐   ┌────────────┐   ┌─────────┐
   │ walk.py │   │router.py │   │normalize.py│   │ emit/   │
   │ walker  │──▶│ dispatch │──▶│ CanonicalDoc│──▶│ MD/OKF  │
   └─────────┘   └──────────┘   └────────────┘   └─────────�
                       │
                       ▼
                 ┌──────────────────────┐
                 │ engines/             │
                 │   base.py (Adapter)  │
                 │   officecli.py       │
                 │   pdf.py             │
                 │   html.py            │
                 │   txt.py             │
                 └──────────────────────┘
```

The data flows strictly **left to right** — each stage transforms its
input into a normalized form for the next. Stages never look backward.

## The CanonicalDoc

`CanonicalDoc` (in `normalize.py`) is the single intermediate representation
shared by every engine output and every emitter. Its fields:

| Field | Purpose |
|---|---|
| `title` | Best-effort title (from `<h1>`, metadata, or filename stem) |
| `body_md` | Canonical Markdown body |
| `source_path` / `source_relpath` / `source_uri` | Where the source lives |
| `source_sha256` | Content hash, used in OKF `sources[]` and idempotency |
| `source_size_bytes` | File size, recorded in manifest |
| `source_format` | Extension (`.docx`, `.pdf`, etc.) |
| `engine` | Which adapter produced this |
| `elements` | Immutable typed structure (`heading`, `paragraph`, `list`, `table`, `image`, `code`, `quote`, `attachment_ref`, `page_break`) with deterministic IDs |
| `tabular_assets` | CSV, worksheet, or PDF-table data plus provenance and deterministic sidecar metadata |
| `metadata` / `attachments` | Engine extras and logical child provenance; attachment filenames never determine output paths |
| `okf_*` | OKF v0.2 trust family pre-filled with honest defaults |

Every adapter's `extract()` returns the same compatible dict shape;
`normalize()` validates optional `elements`/`tabular_assets` and synthesizes a
legacy paragraph element when an adapter only returns `body_md`. Invalid
elements fail only their source with an `INVALID_ELEMENT` diagnostic. Emitters
render canonical elements and never see raw engine output.

## The Adapter contract

`engines/base.py` defines:

```python
class Adapter(ABC):
    name: ClassVar[str]
    extensions: ClassVar[set[str]]

    def supports(self, path: Path) -> bool: ...
    def extract(self, source: Path) -> dict: ...
```

The dict returned by `extract()` has the shape:

```python
{
    "title": str | None,
    "body_md": str,
    "metadata": dict,
    "attachments": list[dict],
    "elements": list[Element | dict],        # optional
    "tabular_assets": list[TabularAsset | dict],  # optional
}
```

That's it. Adding a new format is:

1. Drop a module in `src/headcleaner/engines/`.
2. Implement `Adapter` (one `extract()` method, declare `name` + `extensions`).
3. Register it in `router.py`.
4. Add a row to `docs/FORMAT_MATRIX.md`.
5. Add a fixture in `tests/fixtures/` and a round-trip test in `tests/test_router.py`.

See `docs/CONTRIBUTING.md` for the full extension guide.

## The Emitter contract

Three emitters, one input (`CanonicalDoc`):

- `emit/markdown.py` — writes `_md/<relpath>.md` with lightweight frontmatter.
- `emit/okf.py` — writes `okf/<relpath-without-ext>.md` with full OKF v0.2 frontmatter.
- `emit/okf_index.py` — walks the OKF bundle and generates `index.md` per directory (OKF §8).
- `emit/manifest.py` — writes run-level `manifest.json` with per-file results.

OKF table sidecars are emitted only when structured source data is faithfully
available. PDF inferred cells retain inference/confidence metadata rather than
claiming exact source structure.

Emitters are independent. You can swap or extend any one without touching
the others.

## The pipeline

`run.run_pipeline(opts)` does this in order:

1. Pre-scan via `walk()` to get the total file count (so the TUI's progress
   bar can render an ETA).
2. For each file:
   a. `router.get_adapter(path)` picks the right engine.
   b. If the engine returns successfully, `normalize.normalize()` produces
      a `CanonicalDoc`.
   c. The orchestrator calls the enabled emitters (md / okf) to write outputs.
   d. Per-file result is appended to the `RunRecord`.
3. After all files, `okf_index.generate()` writes directory indices.
4. `manifest.write()` writes the final `manifest.json`.

`run.py` also applies the deterministic engine plan before extraction. A named
engine is not silently replaced; unavailable requirements and typed fallback
attempts are retained in diagnostics. After an email or declared ZIP extraction,
the runner applies central `AttachmentLimits`, quarantines unsafe members, and
recursively routes safe logical children through the same normalization/emission
path. Child staging is temporary and is removed after the run.

The progress hook (`opts.on_progress`) is called from inside step 2; the
TUI uses it to drive its progress bar.

## Honest defaults

The most important architectural choice is **never invent provenance**.
When `normalize()` builds a `CanonicalDoc`, it pre-fills the OKF trust
family with:

- `status: unverified`
- `verified: human:pending`  ← never set this to anything stronger
- `generated: human:<user>@<host>` (OKF §7 actor convention)
- `stale_after: <today + 180d>` (OKF §5.2 freshness)
- `sources: [{uri: file://..., sha256: ...}]` (OKF v0.2 §5.1)

A human reviewer can grep `verified: human:pending` to find concepts
that still need a manual sign-off. We do NOT silently flip this to
`human:reviewed` or `machine-confirmed`. See `docs/OKF_NOTES.md` for the
full contract and policy.

## The TUI

`src/headcleaner/tui.py` is a Textual app that wraps `run_pipeline()`.
The TUI runs the pipeline on a worker thread (so the UI stays responsive)
and forwards per-file progress callbacks back to the main thread via
`call_from_thread`.

Visual language: omp-inspired segmented header + footer with the
neon cyan/pink/purple palette. See `src/headcleaner/theme.py` for the
constants.

The TUI is opt-out: pipe stdout to anything and you get plain text
progress on stderr. The plain mode shares `cli.py`'s progress hook with
the TUI.

## Where to extend

| Want to add | Edit |
|---|---|
| A new file format | `src/headcleaner/engines/<format>.py`, register in `router.py` |
| A new output format | `src/headcleaner/emit/<format>.py`, wire in `run.py` |
| A new CLI subcommand | `src/headcleaner/cli.py` (Click group) |
| A new linter rule | `src/headcleaner/lint.py` |
| A new TUI theme | `src/headcleaner/theme.py` |
| An optional dep (e.g. EML) | `pyproject.toml` `[project.optional-dependencies]` |
| A CI matrix | `.github/workflows/test.yml` |

## What's deliberately NOT here

- **No DB.** Everything is plain files. The manifest is JSON, the bundle
  is markdown. No SQLite, no vector store, no embeddings.
- **No network calls** unless you add an HTTP adapter. The Office engine
  is a local binary; everything else is stdlib or PyPI packages.
- **No LLM calls.** `headcleaner` is a deterministic converter. No
  summarization, no rewriting, no "AI formatting."
- **No background services.** No daemon, no scheduler, no file watcher
  (yet — see ENHANCEMENTS.md #4 for the planned `watch` mode).

## Why Python 3.12 + uv

- 3.12 has the structural pattern matching and `dataclass` improvements
  we lean on (`field(default_factory=...)`, `@dataclass(frozen=True)`).
- `uv` is dramatically faster than `pip`/`poetry` for resolution and
  installs, and the `uv tool install` flow is the cleanest CLI installer
  on the market right now.
- Cross-platform: same `pyproject.toml`, same commands on Windows /
  macOS / Linux. No MSBuild quirks, no Homebrew-specific build steps.
