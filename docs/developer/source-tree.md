# Source tree

This page is the per-module and per-test-file documentation of the headcleaner source tree. It assigns responsibility to every package, module, test family, fixture set, CI file, and documentation area. Use it as the map when you are looking for where a thing lives.

## Production source

### Top-level modules

| Module | Responsibility |
|---|---|
| `src/headcleaner/__init__.py` | Package marker; exposes the public version string. |
| `src/headcleaner/cli.py` | The Click-based CLI entrypoint. Defines every command, every flag, every exit code. |
| `src/headcleaner/tui.py` | The Textual TUI. A legacy surface that is not part of the active development focus. |
| `src/headcleaner/theme.py` | ANSI color constants and box-drawing symbols. The neon cyan/pink/purple palette is defined here. |
| `src/headcleaner/walk.py` | Folder walking. Computes SHA-256 hashes lazily so the walker can be reused by sync and watch. |
| `src/headcleaner/router.py` | Extension-to-adapter dispatch. Reads the plugin registry and the built-in adapter list. |
| `src/headcleaner/engine_plan.py` | Deterministic engine plans and fallback semantics. Defines `EngineCapability`, `EngineAttempt`, and `EnginePlan`. |
| `src/headcleaner/normalize.py` | Adapter output → `CanonicalDoc`. Sets trust defaults and frontmatter. |
| `src/headcleaner/model.py` | `Element` and the typed element model. Defines element IDs, kinds, and source locations. |
| `src/headcleaner/run.py` | Pipeline orchestrator. Owns the run lifecycle, options, results, and derivative emission. |
| `src/headcleaner/lint.py` | Post-conversion linter. Checks frontmatter shape, citation completeness, link integrity. |
| `src/headcleaner/policy.py` | Policy TOML parsing and evaluation. Defines `Policy`, `PolicyFinding`, and the section parsers. |
| `src/headcleaner/chunking.py` | Deterministic, cited chunk derivatives. Emits `chunks.jsonl` under the OKF bundle. |
| `src/headcleaner/index.py` | SQLite FTS5 local search index. Atomic temp+replace build with integrity check. |
| `src/headcleaner/search.py` | Shared parameterized search API used by CLI, HTTP server, and MCP server. |
| `src/headcleaner/embeddings.py` | Embedding provider protocol, local Sentence Transformers, HTTP provider, vector cache, Qdrant adapter. |
| `src/headcleaner/graph.py` | Evidence-linked knowledge graph. Builds `graph.jsonl` from canonical chunks with bounded vocabulary. |
| `src/headcleaner/dedupe.py` | Exact and near-duplicate document families. Emits `duplicate-families.json`. |
| `src/headcleaner/diff.py` | Element-aware Markdown diff. Surfaces frontmatter and table-cell changes as named kinds. |
| `src/headcleaner/claims.py` | Stale and potential-conflict claim candidates. Emits `claim-review.json`. |
| `src/headcleaner/sync.py` | Rename/deletion-safe sync state and reconciliation. Persists `.headcleaner/sync.json`. |
| `src/headcleaner/serve.py` | Local HTTP server exposing the search and graph APIs. |
| `src/headcleaner/mcp.py` | MCP server exposing headcleaner's tools to compatible AI assistants. |
| `src/headcleaner/plugins.py` | Plugin discovery and registration. |
| `src/headcleaner/attachments.py` | Attachment recursion with safety limits. |

### Engine modules

| Module | Responsibility |
|---|---|
| `src/headcleaner/engines/base.py` | `Adapter` abstract base class. Defines the contract every adapter implements. |
| `src/headcleaner/engines/officecli.py` | DOCX/XLSX/PPTX extraction via the OfficeCLI binary. |
| `src/headcleaner/engines/pdf.py` | PDF extraction via `pdfplumber`, with optional Tesseract OCR. |
| `src/headcleaner/engines/html.py` | HTML/HTM extraction via BeautifulSoup and `markdownify`. |
| `src/headcleaner/engines/txt.py` | Plain text extraction with `chardet` encoding detection. |
| `src/headcleaner/engines/eml.py` | RFC 822 email messages. |
| `src/headcleaner/engines/msg.py` | Microsoft Outlook `.msg` files via `extract-msg`. |
| `src/headcleaner/engines/pst.py` | Microsoft Outlook `.pst` archives via `readpst`. |

### Emit modules

| Module | Responsibility |
|---|---|
| `src/headcleaner/emit/markdown.py` | Writes plain Markdown output with lightweight frontmatter. |
| `src/headcleaner/emit/okf.py` | Writes OKF v0.2 concept output. |
| `src/headcleaner/emit/okf_index.py` | Writes the auto-generated `index.md` per directory. |
| `src/headcleaner/emit/manifest.py` | Writes the run-level `manifest.json`. |
| `src/headcleaner/emit/report.py` | Writes the run-level `REPORT.md` including claim, dedupe, and graph sections. |

## Test surface

### Test families

| Test file | Responsibility |
|---|---|
| `tests/conftest.py` | Shared pytest fixtures: sample documents, OKF bundles, mock engines. |
| `tests/test_walk.py` | Folder walker behavior: source enumeration, SHA-256 computation. |
| `tests/test_router.py` | Router dispatch: extension matching, fallback semantics. |
| `tests/test_normalize.py` | Normalization: canonical doc shape, trust defaults, frontmatter. |
| `tests/test_emit.py` | Emitters: Markdown and OKF output, atomic write. |
| `tests/test_run.py` | Pipeline: run lifecycle, options, results, derivatives. |
| `tests/test_lint.py` | Linter: rule evaluation, finding structure. |
| `tests/test_chunking.py` | Chunking: deterministic IDs, oversize handling, indivisible tables. |
| `tests/test_index.py` | Search index: atomic rebuild, integrity check, rebuild idempotence. |
| `tests/test_search.py` | Search: FTS5 query, filters, deterministic ranking. |
| `tests/test_dedupe.py` | Dedupe: exact and near-duplicate families, threshold behavior. |
| `tests/test_diff.py` | Diff: frontmatter separation, table-cell coords, structural changes. |
| `tests/test_claims.py` | Claims: kinds, scope, suppression, stale lifecycle, cap. |
| `tests/test_sync.py` | Sync: rename, delete, conflict, corruption, durable ownership. |
| `tests/test_embeddings.py` | Embeddings: provider protocol, cache, network permission, Qdrant lifecycle. |
| `tests/test_graph.py` | Graph: bounded vocabulary, evidence, claim linkage, kind filter. |
| `tests/test_mcp.py` | MCP server: tool signatures, citations, stdio round-trips. |
| `tests/test_serve.py` | HTTP server: endpoint shapes, error envelopes. |
| `tests/test_watch.py` | Watcher: event normalization, deletion handling. |
| `tests/test_policy.py` | Policy: TOML parsing, section validation. |
| `tests/test_report.py` | Report: claim/dedupe/graph sections. |
| `tests/test_okf_schema.py` | OKF schema validation against `docs/schemas/okf-frontmatter.schema.json`. |

### Fixtures

| Fixture | Responsibility |
|---|---|
| `tests/fixtures/sample.xlsx` | Hand-rolled valid XLSX used by the normalization tests. |
| `tests/quality/` | Attributed fixtures for the quality benchmark (Phase 1). |

## CI

| File | Responsibility |
|---|---|
| `.github/workflows/test.yml` | CI workflow. Runs the locked-environment test suite on Python 3.12 and 3.13 across Windows, macOS, and Linux runners. |
| `scripts/verify.sh` | Post-install sanity check. Runs doctor and a minimal smoke conversion. |

## Documentation

The documentation tree is organized by audience: `docs/getting-started/`, `docs/user-guide/`, `docs/tutorials/`, `docs/reference/`, `docs/integrations/`, `docs/safety/`, `docs/developer/`, `docs/maintainers/`. The archived predecessor lives in `docs/_archive/`. The schemas that tests and downstream consumers depend on live in `docs/schemas/`.

The structure is documented in `docs/DOCS_REWRITE_TRACKER.md`, which is the authoritative map of what lives where in the documentation tree.

## What to read next

The [architecture developer guide](architecture.md) explains how the modules fit together. The [canonical model developer guide](canonical-model.md) documents every dataclass and contract. The [tool and engine development guide](tool-and-engine-development.md) walks through adding a new adapter.