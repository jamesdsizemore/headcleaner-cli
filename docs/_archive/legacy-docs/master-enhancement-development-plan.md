# Master Enhancement Development Plan

> **Single master plan.** This document organizes all 32 items in `docs/100x-enhancements-plan.md` into exactly four implementation phases. It does **not** create, require, or reference separate per-phase plan documents.

**Goal:** Evolve headcleaner into a measurable, citation-first, reviewable, local-first document-intelligence platform while preserving its conversion trust stance and portable CLI core.

**Architecture:** The program builds from durable foundations outward: (1) a typed conversion/quality substrate, (2) a local knowledge substrate, (3) human-governed safety and trust, then (4) agent/service/integration workflows. Markdown and OKF remain the canonical durable outputs; typed elements, diagnostics, chunks, indexes, vectors, review queues, and service state are rebuildable derivatives.

**Tech stack:** Python 3.12–3.13, `uv`, Click, Textual, FastAPI, SQLite FTS5, existing Markdown/OKF emitters, and one complete required, exact-pinned product dependency set.

**Status:** Proposed master implementation plan. This document makes no code changes and does not claim any proposed enhancement is shipped.

---

## 1. Verified starting point

The plan is grounded in the current repository rather than an imagined blank slate:

| Existing seam | Verified implementation | Why it matters |
|---|---|---|
| Canonical representation | `src/headcleaner/normalize.py:20-154` defines `CanonicalDoc` with source hash, metadata, attachments, and trust defaults. | Phase 1 evolves this compatibly into typed elements. |
| Conversion orchestration | `src/headcleaner/run.py:41-75`, `137-229` already owns options, engine dispatch, cache/resume, and emission. | New stages must be introduced here without bypassing the pipeline. |
| Routing/plugins | `src/headcleaner/router.py:26-113`, `src/headcleaner/plugins.py:30-113`. | Engine planning and plugin manifests build on the current precedence and entry-point model. |
| Review/trust | `src/headcleaner/review.py:52-248`, `src/headcleaner/policy.py:36-172`, `src/headcleaner/attest.py:234-420`. | Review, policy, and attestation enhancements extend existing behavior; auto-conversion must remain `human:pending`. |
| Bundle access | `src/headcleaner/mcp.py:13-28`, `224-480`; `src/headcleaner/serve.py:92-267`. | Phase 4 upgrades existing MCP/search/HTTP surfaces rather than adding a competing service. |
| Long-running workflows | `src/headcleaner/watch.py:30-122`, `src/headcleaner/webhook.py:25-73`. | Sync, durable jobs, and event contracts begin from working watcher/webhook behavior. |
| Test surface | Existing tests include `test_run.py`, `test_normalize.py`, `test_mcp.py`, `test_attest.py`, `test_plugins.py`, `test_serve.py`, `test_report.py`, and `test_batch5_review.py`. | Every task below names an exact new or modified test target. |

### Non-negotiable invariants

1. Automatic conversion never upgrades `verified: human:pending` to reviewed/approved.
2. The default command remains local-first and usable without a GPU, credentials, a vector DB, or a network service.
3. All Python product dependencies are installed and lock-verified together; outbound network actions still require explicit configuration and user intent.
4. The canonical artifact remains Markdown/OKF plus source/provenance data; indexes and embeddings can always be rebuilt.
5. No destructive source-file action, redaction, move, or connector sync occurs without preview and explicit confirmation.
6. Do not mix this work with broad Ruff cleanup, formatting churn, unrelated conversion engines, dashboard changes, or package-distribution work.

---

## 2. Research and verification register

### Evidence corpus

Research was completed before this plan was written and retained under `research/100x-enhancements/`:

- **10 GitHub landscape searches**, producing **56 live/unique raw results**.
- **11 individually verified mature references:** Docling, MarkItDown, Marker, Unstructured, PaddleOCR, OCRmyPDF, Apache Tika, RAGFlow, Qdrant, in-toto, and MCP reference servers.
- **Additional verified capability references:** Microsoft Presidio, RapidFuzz, Sentence Transformers, FastAPI, and Pydantic.
- Live PyPI metadata for all existing direct dependencies and each proposed dependency pin.

The Agent Reach Exa backend was unavailable on this host, so this evidence is explicitly GitHub/API/PyPI-backed rather than misrepresented as a general web crawl.

### Per-enhancement verification map

Every enhancement is backed by an existing local seam and at least one verified external/reference basis.

| ID | Enhancement | Local seam verified | External/reference basis verified |
|---:|---|---|---|
| 1 | Golden corpus and scorecard | `tests/`, `run.py`, CI workflows | Marker, Docling, Unstructured |
| 2 | Diagnostics/confidence report | `emit/manifest.py`, `emit/report.py`, `jsonlog.py` | Docling, Unstructured |
| 3 | Adaptive engine cascade | `router.py`, `run.py`, adapter API | Docling, Apache Tika, current engine-capability model |
| 4 | Render/fidelity verification | `viewer.py`, `serve.py`, existing PDF/Office paths | Marker, ImageHash/Pillow metadata |
| 5 | Typed element model | `normalize.py:20-154`, emitters | Docling, Unstructured |
| 6 | Tables/formulas/structured sidecars | Office/CSV/PDF adapters, `attachments` field | Marker, Docling |
| 7 | OCR profiles/language detection | `engines/pdf.py`, doctor, required OCR dependencies | PaddleOCR, OCRmyPDF |
| 8 | Safe recursive attachments | existing `attachments`, email/PST adapters | `defusedxml` metadata, archive-safety design |
| 9 | Stable cited chunks | `CanonicalDoc`, OKF source fields | RAGFlow, Qdrant |
| 10 | Local hybrid search | `serve.py`, `mcp.py`, SQLite stdlib | Qdrant, RAGFlow |
| 11 | Embedding providers | plugin/required-dependency model | Sentence Transformers, Qdrant |
| 12 | Entity/topic relationship graph | `crossref.py`, viewer graph data | Docling/Unstructured element model; RAGFlow graph-oriented retrieval patterns |
| 13 | Duplicate/version families | source SHA in `normalize.py`, manifests | RapidFuzz |
| 14 | Element-aware document diffs | MCP `okf_diff`, manifests | typed-element/citation design from Docling/RAG workflows |
| 15 | Contradiction/stale claims | `stale_after`, policy, MCP doctor | RAGFlow citation/retrieval patterns |
| 16 | Rename/deletion-safe synchronization | `watch.py`, cache in `run.py` | watchfiles/current cache design |
| 17 | Evidence-based review workbench | `review.py`, `viewer.py`, Textual | existing review architecture plus diagnostics from #2 |
| 18 | Versioned policy packs | `policy.py` | existing TOML policy model and JSON Schema support |
| 19 | PII/secret proposal redaction | policies, canonical outputs | Microsoft Presidio |
| 20 | Quarantine/hostile-file defense | router/pre-extraction boundary, doctor | `defusedxml`; engine isolation |
| 21 | Reproducible attestations | `attest.py` Merkle/signing path | in-toto |
| 22 | Risk-based review queues | review/policy/manifest data | diagnostics and review workflow foundations |
| 23 | RAG/agent readiness grades | policy, diagnostics, OKF trust fields | RAGFlow, Qdrant |
| 24 | Public benchmark transparency | reports, CI, quality corpus | Marker/Docling quality-oriented precedent |
| 25 | Citation-first MCP retrieval | `mcp.py` existing 10-tool server | MCP reference servers, RAGFlow |
| 26 | Agent context packages | existing `okf_context` | MCP context model, chunk/citation design |
| 27 | Classification/routing profiles | `RunOptions`, router, doctor | current TOML/engine configuration approach |
| 28 | Durable queue/service mode | `serve.py`, `watch.py`, FastAPI | FastAPI/Pydantic metadata |
| 29 | Signed event/webhook contracts | `webhook.py`, `jsonlog.py` | FastAPI/Pydantic contract model |
| 30 | Safe Obsidian/Notion/Git sync | `obsidian.py`, `notion.py`, `git_commit.py` | existing connector modules; #16 conflict model |
| 31 | Plugin manifests/conformance | `plugins.py`, `docs/PLUGINS.md` | Python entry-point model currently used |
| 32 | Versioned automation API | `jsonlog.py`, schemas, CLI JSON option | FastAPI/Pydantic schema/versioning model |

---

## 3. Dependency lock and readiness gate

### Locking policy

The implementation begins with one dependency-only commit. Every product dependency is exact-pinned in `pyproject.toml` under `[project].dependencies`; `uv.lock` is regenerated and committed as the authoritative transitive lock. There are no `project.optional-dependencies` extras in this program. Do not add an unpinned direct dependency in any later task.

Every implementation/CI environment uses:

```bash
unset PYTHONPATH
uv lock --check
uv sync --locked --python 3.13
uv run --no-sync --python 3.13 pytest -rs --no-header
```

Every development, CI, and release-candidate environment installs the same locked product dependency set. CPU/GPU acceleration and remote-service use are runtime configuration choices, not separately installed Python extras.

### Exact direct pins to establish

Replace existing broad direct requirements with the following live-verified Python 3.12–3.13-compatible pins. The implementation must validate their resolved lock on Windows, Ubuntu, and macOS CI before feature work proceeds.

```toml
[project]
requires-python = ">=3.12,<3.14"
dependencies = [
  "beautifulsoup4==4.15.0",
  "lxml==6.1.1",
  "pdfplumber==0.11.10",
  "pypdf==6.16.1",
  "chardet==7.6.0",
  "markdownify==1.2.3",
  "pyyaml==6.0.3",
  "tomli-w==1.2.0",
  "click==8.4.2",
  "rich==15.0.0",
  "textual==8.2.8",
  "extract-msg==0.56.1",
  "watchfiles==1.2.0",
  "ebooklib==0.20",
  "striprtf==0.0.33",
  "odfpy==1.4.1",
  "fastapi==0.141.1",
  "uvicorn==0.52.3",
  "jinja2==3.1.6",
  "all2md==1.12.0",
  "jsonschema==4.26.0",
  "office-oxide==0.1.8",
  "pytesseract==0.3.13",
  "Pillow==12.3.0",
  "libpff-python==20231205",
  "ImageHash==4.3.2",
  "opencv-python-headless==5.0.0.93",
  "lingua-language-detector==2.2.0",
  "defusedxml==0.7.1",
  "rapidfuzz==3.14.5",
  "sentence-transformers==6.0.0",
  "qdrant-client==1.19.0",
  "presidio-analyzer==2.2.364",
  "cryptography==50.0.0",
  "in-toto==3.1.0",
  "mcp==1.29.0",
  "httpx==0.28.1",
  "tenacity==9.1.4",
]

[dependency-groups]
dev = [
  "babel==2.18.0",
  "pytest==9.1.1",
  "ruff==0.16.3",
]
```

### Explicit dependency decisions

| Decision | Verified conclusion |
|---|---|
| `mcp` | Pin **`mcp==1.29.0`**, the latest available 1.x release. `src/headcleaner/mcp.py:45` imports the 1.x `MCPServer` API; do not introduce `mcp==2.0.0` without a separately tested migration task. |
| PyMuPDF | **Excluded.** Current PyPI metadata identifies dual AGPL/commercial licensing, unsuitable for this Apache-2.0 project plan. |
| `python-magic` | **Excluded.** It requires platform `libmagic`, which makes Windows support non-reproducible. Use stdlib signature checks and explicitly configured external scanner hooks instead. |
| SQLite FTS | **No new package.** Python’s supported SQLite provides the baseline FTS5 index. |
| Tesseract, LibreOffice, OfficeCLI, ClamAV | **Required system-tool contract.** Task 0 pins their installation source/version in `Dockerfile`, CI, and `docs/DEPENDENCIES.md`; doctor fails the environment gate when one is missing. They are not Python packages, so they do not belong in `pyproject.toml`. |
| Sentence Transformers/Qdrant | **Required Python dependencies.** Sentence Transformers is installed in every environment. SQLite FTS5 remains the local index; Qdrant service connection is an explicit runtime configuration, with local-client contract tests always run. |

### Program setup task (must complete before Phase 1)

**Files:**
- Modify: `pyproject.toml:21-52,97-105`
- Modify: `uv.lock`
- Modify: `.github/workflows/test.yml`
- Modify: `src/headcleaner/mcp.py`, `src/headcleaner/emit/manifest.py`, `src/headcleaner/jsonlog.py`, `src/headcleaner/attest.py`, `src/headcleaner/serve.py`
- Create: `tests/test_dependency_contract.py`
- Create: `docs/DEPENDENCIES.md`

**Actions:**
1. Apply the exact pins above and regenerate `uv.lock` with `uv lock`.
2. Add a test that asserts no `project.optional-dependencies` table exists, every product pin is exact, and `mcp` remains pinned to 1.x.
3. Add a CI lock job for Python 3.12 and 3.13 using `uv sync --locked` and run semantic, privacy, MCP, OCR, and service contract tests in that same fully provisioned environment.
4. Pin required system-tool installation sources/versions in Docker/CI and document the complete installation contract.

**Acceptance:** lock check and the complete required product test suite pass on Python 3.12 and 3.13; `pyproject.toml` has no optional-dependency table; doctor verifies every required system tool.

**Commit:** `build: lock enhancement program dependencies`

---

# Phase 1 of 4 — Faithful and measurable conversion substrate

**Purpose:** Build the quality and internal-data foundations required by every later phase.

**Dependencies:** Program setup task complete; the complete required locked environment and required system-tool contract are available.

**Phase exit gate:** The golden corpus has a recorded baseline; typed elements render through the Markdown/OKF emitters shipped at v0.14.0 without breaking the legacy fixture bytes or plugin entry points; no quality metric regresses without an explicit approved baseline update.

**File-status notation:** In every phase table, paths in **Create** are new production, schema, fixture, or documentation files. Each path in **Test** is an exact test target: create it when it is not currently present in `tests/`; otherwise edit the existing test file. Paths in **Modify** are existing repository files to edit. This avoids implicit test-file creation and makes the complete file scope auditable.

| Task | Enhancements delivered | Create | Modify | Test |
|---:|---|---|---|---|
| 1.1 | #1 Golden corpus and scorecard | `src/headcleaner/benchmark.py`, `tests/quality/`, `tests/quality/fixtures/ATTRIBUTION.md`, `tests/quality/baseline.json` | `cli.py`, `.github/workflows/test.yml`, `docs/CONTRIBUTING.md` | `tests/quality/test_benchmark.py` |
| 1.2 | #2 Diagnostics/confidence | `src/headcleaner/diagnostics.py` | `emit/manifest.py`, `emit/report.py`, `run.py`, `jsonlog.py`, `cli.py` | `tests/test_diagnostics.py`, `tests/test_report.py`, `tests/test_run.py` |
| 1.3 | #3 Engine plans/cascade | `src/headcleaner/engine_plan.py` | `router.py`, `run.py`, `doctor.py`, `cli.py` | `tests/test_engine_plan.py`, `tests/test_router.py`, `tests/test_doctor.py` |
| 1.4 | #4 Render/fidelity checks | `src/headcleaner/render_verify.py` | `viewer.py`, `emit/report.py`, `cli.py` | `tests/test_render_verify.py` |
| 1.5 | #5 Typed element model | `src/headcleaner/model.py` | `normalize.py`, `engines/base.py`, `emit/markdown.py`, `emit/okf.py`, `plugins.py`, `docs/PLUGINS.md` | `tests/test_model.py`, `tests/test_normalize.py`, `tests/test_emit.py`, `tests/test_plugins.py` |
| 1.6 | #6 Structured table/spreadsheet output | `src/headcleaner/tabular.py` | `engines/officecli.py`, `engines/csv_json.py`, `engines/pdf.py`, `model.py`, `emit/okf.py` | `tests/test_tabular.py`, `tests/test_office_oxide.py`, `tests/test_zsv_adapter.py` |
| 1.7 | #7 OCR profiles/language packs | `src/headcleaner/ocr.py` | `engines/pdf.py`, `doctor.py`, `cli.py`, `config` command implementation | `tests/test_ocr_profiles.py`, `tests/test_doctor.py` |
| 1.8 | #8 Safe attachment recursion | `src/headcleaner/attachments.py` | `run.py`, `router.py`, `engines/eml.py`, `engines/msg.py`, `engines/pst.py`, `policy.py`, `cli.py` | `tests/test_attachments.py`, `tests/test_pst_per_message.py`, `tests/test_adapters_batch1.py` |

## Phase 1 task sequence

### Task 1.1 — Establish the quality corpus and benchmark contract

**Objective:** Make conversion fidelity measurable before changing extraction behavior.

**Implementation steps:**
1. Create attributed fixtures for headings, tables, images, forms, scans, multi-column PDFs, formulas, multilingual text, malformed files, and attachment-bearing mail.
2. Define deterministic per-fixture assertions: retained text anchors, heading sequence, table cells, source hashes, output files, and expected diagnostic warnings.
3. Implement `headcleaner benchmark` with JSON output and a checked-in baseline that records tool/engine versions and per-fixture metric values.
4. Add CI to fail on a regression while allowing an explicitly reviewed baseline update.

**Acceptance:** Running `headcleaner benchmark tests/quality/fixtures` yields deterministic JSON; intentionally deleting an expected table/text anchor fails `tests/quality/test_benchmark.py`.

### Task 1.2 — Add diagnostics as a first-class result field

**Objective:** Ensure every conversion reports evidence rather than only success/failure.

**Implementation steps:**
1. Introduce typed `Diagnostic` and `ExtractionMetrics` records (engine attempts, OCR state, language, source dimensions/pages, typed-element counts, warnings, confidence inputs).
2. Extend `FileResult` with backward-compatible optional fields; maintain old manifest readers.
3. Include diagnostics in final manifests, reports, and JSON line events with a declared schema version.
4. Calculate confidence from explicit, documented deterministic signals; do not claim semantic correctness.

**Acceptance:** A text PDF, scanned PDF, unsupported file, and fallback-engine fixture all emit the expected metrics/warnings and schema-valid JSON.

### Task 1.3 — Implement deterministic engine plans

**Objective:** Replace one-shot extension dispatch with a recorded, safe fallback plan.

**Implementation steps:**
1. Define engine capabilities, prerequisites, cost class, network requirement, and supported trait predicates in `engine_plan.py`.
2. Preserve existing router ordering as the default first choice.
3. Permit a fallback only after a typed failure/low-confidence condition; record attempted engines and reasons in diagnostics.
4. Add `--engine`, `--no-fallback`, and `--allow-network` only where their behavior is fully tested. Network defaults to disabled.

**Acceptance:** Existing adapter precedence tests still pass; fallback behavior is deterministic and never invokes unavailable or network engines implicitly.

### Task 1.4 — Add on-demand render verification

**Objective:** Detect structural/layout losses that text assertions cannot detect.

**Implementation steps:**
1. Define renderer interfaces for source and output previews; use existing viewer/HTML emission before adding external renderers.
2. Compute a compact image/hash/structural report using the required ImageHash/Pillow dependencies; retain artifacts only under an explicit verification directory.
3. Flag a threshold breach as `warning`/review-needed, never as a false conversion failure unless policy requires it.

**Acceptance:** A deliberately altered fixture triggers a fidelity warning; a normal fixture produces a stable report without modifying canonical output.

### Task 1.5 — Introduce typed document elements with a compatibility bridge

**Objective:** Make document structure reusable by emitters, chunking, review, and search.

**Implementation steps:**
1. Define immutable typed elements with sequence, source span/page, content, attributes, and optional attachment references.
2. Add an optional `elements` field to adapter results; adapt legacy `body_md` results into one or more compatible text elements.
3. Render typed elements through existing Markdown and OKF emitters with byte-for-byte compatible output for legacy fixtures where feasible.
4. Update plugin documentation and tests so existing third-party adapters continue to work unchanged.

**Acceptance:** Existing adapters and plugin fixtures pass unchanged; new typed fixture renders headings/lists/tables in stable order and preserves source references.

### Task 1.6 — Preserve structured data beside Markdown

**Objective:** Keep spreadsheet/table information analyzable rather than flattening it irreversibly.

**Implementation steps:**
1. Define `TabularAsset` metadata with source range, headers, formula/format availability, and sidecar paths.
2. Emit CSV/JSON sidecars only when they are faithfully available; Markdown remains a readable projection.
3. Preserve formulas, merged-cell metadata, and sheet names for Office sources; preserve detected table spans for PDFs with confidence warnings.
4. Link assets through the existing `attachments` model and documented OKF extension fields.

**Acceptance:** Formula, merged-cell, and CSV fixtures produce correctly linked sidecars; missing/inferred PDF table structure is marked in diagnostics.

### Task 1.7 — Upgrade OCR from a boolean to tested profiles

**Objective:** Make OCR behavior explicit, reproducible, and multilingual-aware.

**Implementation steps:**
1. Define `fast`, `balanced`, `archival`, and experimental handwriting profiles with documented preprocessing/retry policies.
2. Detect installed Tesseract languages and fail with actionable doctor findings when requested languages are absent.
3. Use `lingua-language-detector` only for language selection hints; do not label a language certain without OCR evidence.
4. Keep PaddleOCR out of this locked dependency set until its version, license, platform support, and conformance suite are separately verified; do not silently add it as an unpinned fallback.

**Acceptance:** Profile selection is serialized in diagnostics; missing language packs, rotated scans, and normal PDFs have deterministic test outcomes.

### Task 1.8 — Safely recurse through attachments and embedded content

**Objective:** Convert contained content without creating archive-bomb, path-traversal, or provenance gaps.

**Implementation steps:**
1. Add limits for depth, total extracted bytes, member count, individual member size, and encrypted/password-protected objects.
2. Normalize child artifacts through the same router/pipeline with a parent-source chain.
3. Use `defusedxml` for XML-family inspection paths and reject unsafe archive members before extraction.
4. Default to metadata-only output for password-protected content and require explicit unsafe override for any future bypass.

**Acceptance:** Synthetic zip-bomb/path-traversal/encrypted fixtures are quarantined; safe email attachments produce child results with parent/child provenance.

### Phase 1 authoritative implementation contracts

The following contracts override the brief task summaries above. An implementer must not infer an unlisted data field, CLI flag, fallback, status transition, or write path. When a contract needs an additional field or file, amend this master document and its schema/test first; do not silently improvise it in code.

#### Contract 1.1 — Golden corpus and benchmark scorecard

- **Owned files:** create `src/headcleaner/benchmark.py`, `tests/quality/test_benchmark.py`, `tests/quality/baseline.json`, and `tests/quality/fixtures/ATTRIBUTION.md`; edit only `cli.py`, `.github/workflows/test.yml`, and `docs/CONTRIBUTING.md` from the Phase 1 table.
- **Fixture contract:** each fixture directory contains the original attributed input, `expectations.json`, and no derived output. `expectations.json` contains `fixture_id`, `source_sha256`, `license_or_permission`, `expected_engine`, required text anchors, ordered heading strings, expected table-cell strings, expected warning codes, and `minimum_score`. A test rejects missing fields, duplicate `fixture_id`, unpinned source hash, or a fixture whose attribution is absent.
- **Result contract:** `benchmark.py` emits JSON only when `--json` is passed: `{schema_version, generated_at, tool_version, fixtures:[{fixture_id, source_sha256, status, metrics, warnings}], summary}`. `metrics` is a named map of `text_anchor_recall`, `heading_order`, `table_anchor_recall`, and `output_exists`; no single opaque quality score replaces component metrics. The checked-in baseline is the same shape minus wall-clock fields.
- **CLI/error contract:** add `headcleaner benchmark INPUT [--baseline PATH] [--json] [--update-baseline]`. Missing fixture metadata, hash mismatch, or metric regression exits non-zero. `--update-baseline` requires an explicit path and must refuse untracked/unknown fixtures; ordinary benchmark execution never rewrites a baseline.
- **Tests and boundary:** test a passing fixture, a missing anchor, changed source bytes, unordered headings, and an update attempt without explicit consent. Do not reuse private real-world documents, call an AI service, or alter conversion output in this task.

#### Contract 1.2 — Diagnostics and deterministic confidence

- **Owned files:** create `src/headcleaner/diagnostics.py` and `tests/test_diagnostics.py`; edit `run.py`, `emit/manifest.py`, `emit/report.py`, `jsonlog.py`, `cli.py`, `tests/test_run.py`, and `tests/test_report.py`.
- **Data model:** define frozen `Diagnostic(code, severity, message, evidence: dict[str, JSONScalar])` and `ExtractionMetrics(page_count, character_count, element_counts, engine_attempts, ocr_used, detected_languages, confidence_inputs)`. `severity` is exactly `info|warning|error`; diagnostic codes are stable uppercase identifiers declared in one registry. Store lists in pipeline order and sort dictionary keys at emission.
- **Confidence rule:** create `compute_confidence(metrics) -> float` that only combines documented measurable signals (non-empty extraction, engine success, OCR warning state, required-anchor outcome, structural counts). It must return a value in `[0, 1]`, plus the named input contributions. It must not inspect private content semantically, invoke a model, or mean “correct.”
- **Integration:** add nullable `diagnostics`, `metrics`, and `confidence` fields to `FileResult`; old manifests without them must deserialize as empty lists/`None`. `run_pipeline` constructs them once per source and every report/JSON event consumes the same object rather than recomputing divergent results.
- **Tests and boundary:** assert exact serialized field names, stable list ordering, legacy-manifest compatibility, each severity, and known confidence inputs. Never turn a warning/confidence score into `verified` state.

#### Contract 1.3 — Deterministic engine plans and fallbacks

- **Owned files:** create `src/headcleaner/engine_plan.py` and `tests/test_engine_plan.py`; edit `router.py`, `run.py`, `doctor.py`, `cli.py`, `tests/test_router.py`, and `tests/test_doctor.py`.
- **Data model:** define `EngineCapability(name, extensions, requires_tools, network_mode, priority, supports_traits)` and `EngineAttempt(engine, reason, outcome, diagnostic_codes)`. Define `EnginePlan(source, requested_engine, attempts)` before extraction. `network_mode` is exactly `never|explicit`; unknown capability traits do not match an engine.
- **Prerequisite availability:** `build_engine_plan` receives an immutable `available_tools` snapshot when availability filtering is required; it does not probe host PATH itself. A candidate whose `requires_tools` are absent remains an `EngineAttempt` with `outcome: unavailable`, reason `required-tool-unavailable`, and diagnostic code `ENGINE_REQUIRED_TOOL_UNAVAILABLE`; the runner records that attempt but never executes it, then considers the next declared candidate only when fallback is allowed.
- **Selection rule:** start with the current router-selected adapter. Only schedule the next declared candidate after `AdapterError`, unavailable required tool, or an explicit diagnostic code listed in `engine_plan.py`; never fallback after an arbitrary exception. A named `--engine` yields a one-engine plan unless `--allow-fallback` is supplied. `--no-fallback` accepts no alternate engine.
- **CLI/doctor contract:** expose `--engine NAME`, `--no-fallback`, `--allow-fallback`, and `--allow-network`; default network permission is false. Doctor lists each capability, missing required tool, and whether it is selectable under the active flags. Persist the complete attempt list in diagnostics/manifest.
- **Tests and boundary:** test current precedence, unavailable first engine, typed extraction failure, forbidden network engine, forced engine, and untyped exception propagation. Do not reorder the global adapter registry, mutate plugin registration, or use low confidence alone as permission to send content to a network engine.

#### Contract 1.4 — On-demand render/fidelity verification

- **Owned files:** create `src/headcleaner/render_verify.py` and `tests/test_render_verify.py`; edit `viewer.py`, `emit/report.py`, and `cli.py`.
- **Input/output model:** `RenderVerification(source_ref, output_ref, renderer, page_results, aggregate, warnings)` consumes already-created source/output artifacts. Each `page_result` includes `page_index`, dimensions, structural/text-anchor comparison outcome, embedded-image hash comparison when both sides contain the same extracted image, and diagnostic codes. Full-page perceptual hashes are not a Markdown/PDF fidelity threshold. Store reports under `<output>/_verification/<source_sha256>/report.json`; never write into source directories or canonical Markdown/OKF paths.
- **Renderer policy:** register source and output renderers by supported format. If either renderer is unavailable, return `status: unavailable` with a diagnostic; do not install binaries, silently convert through a new engine, or fail a successful conversion merely because verification cannot run.
- **CLI/error contract:** add `headcleaner verify-render INPUT OUTPUT [--output-dir DIR] [--json]`. Exit non-zero only for malformed arguments, unreadable inputs, or a policy-enforced threshold breach. A fidelity mismatch is a warning/review finding by default and must cite the compared page/artifact.
- **Tests and boundary:** fixtures cover identical render, changed page, unavailable renderer, page-count mismatch, deterministic report location, and no mutation of canonical files. Threshold constants live in one named policy/config object and are never embedded in tests or emitters.

#### Contract 1.5 — Typed elements with legacy adapter compatibility

- **Owned files:** create `src/headcleaner/model.py` and `tests/test_model.py`; edit `normalize.py`, `engines/base.py`, `emit/markdown.py`, `emit/okf.py`, `plugins.py`, `docs/PLUGINS.md`, `tests/test_normalize.py`, `tests/test_emit.py`, and `tests/test_plugins.py`.
- **Data model:** define immutable `Element(id, kind, ordinal, text, source_location, attributes)` where `kind` is exactly `heading|paragraph|list|table|image|code|quote|attachment_ref|page_break`; `source_location` is `{page, start, end}` with nullable members; `attributes` only contains JSON-safe values. Element ID is a deterministic digest of source SHA, kind, ordinal, and normalized content—not a random UUID.
- **Adapter contract:** add `elements: list[Element] = field(default_factory=list)` to `CanonicalDoc`; extend the adapter result dictionary with an optional `elements` list. `normalize()` validates supplied elements, assigns deterministic IDs when absent, and builds a legacy element sequence from `body_md` when an adapter has no elements. Invalid plugin elements produce an `INVALID_ELEMENT` diagnostic and fail that source only; they do not corrupt another source’s run.
- **Emitter contract:** Markdown/OKF emitters render the element sequence; when elements came from legacy body Markdown, preserve current output bytes except explicitly versioned frontmatter additions. Emitters must not independently parse body text into a second divergent structure.
- **Tests and boundary:** cover deterministic IDs, JSON-safe validation, legacy adapter byte compatibility, plugin valid/invalid element behavior, and source-location propagation. No semantic NLP classification belongs in this task.

#### Contract 1.6 — Structured table and spreadsheet assets

- **Owned files:** create `src/headcleaner/tabular.py` and `tests/test_tabular.py`; edit `engines/officecli.py`, `engines/csv_json.py`, `engines/pdf.py`, `model.py`, `emit/okf.py`, `tests/test_office_oxide.py`, and `tests/test_zsv_adapter.py`.
- **Data model:** define `TabularAsset(id, kind, source_location, columns, rows, formula_cells, merged_ranges, provenance, sidecar_relpath)`. `kind` is `csv|worksheet|pdf_table`; `formula_cells` retains formula text and displayed value separately; inferred PDF cells carry `inferred: true` and confidence evidence. Sidecars are UTF-8 CSV plus JSON metadata, named from source hash and asset ID.
- **Emission contract:** write sidecars only below the output root at `_assets/tables/`; add a relative asset reference to the parent concept/manifest. Table Markdown remains a projection and must include the asset ID. No sidecar may expose a source path outside the output root or overwrite a user-owned file.
- **Engine contract:** Office/CSV engines provide native rows/headers/formulas where available. PDF table extraction may provide inferred rows but must never label an inferred value as source-native. Empty/no-table input returns no asset, not an empty sidecar.
- **Tests and boundary:** assert formulas, merged ranges, CSV quoting/newlines, safe sidecar path, inferred-PDF diagnostic, and asset linkage. Do not introduce spreadsheet recalculation, formula evaluation, or editing.

#### Contract 1.7 — OCR profiles and language/tool verification

- **Owned files:** create `src/headcleaner/ocr.py` and `tests/test_ocr_profiles.py`; edit `engines/pdf.py`, `doctor.py`, `cli.py`, the existing config-command implementation, and `tests/test_doctor.py`.
- **Data model:** define `OCRProfile(name, preprocess_steps, tesseract_psm, requested_languages, retry_policy)` with allowed names `fast|balanced|archival|handwriting_experimental`. Profiles are immutable shipped defaults; user configuration may select a name or copy one under a new profile name, never mutate shipped defaults in place.
- **Tool contract:** `doctor` calls the configured Tesseract executable once, parses installed language codes, and reports profile-language incompatibility as a machine-readable finding. `ocr.py` passes only declared profile options to the subprocess, records executable/version/languages in diagnostics, and captures stderr without leaking file contents.
- **CLI/error contract:** add `--ocr-profile NAME` and `--ocr-lang CODE[,CODE...]`. Unknown profile or language unavailable on the host fails before document processing with an actionable doctor code. No OCR profile authorizes a network request or changes the human-review trust state.
- **Tests and boundary:** mock executable discovery/output for installed/missing language, verify exact invocation arguments, profile selection, rotation/retry diagnostic, and no OCR on text-native PDF unless explicitly selected. PaddleOCR is explicitly out of scope for this task.

#### Contract 1.8 — Bounded attachment recursion and provenance

- **Owned files:** create `src/headcleaner/attachments.py` and `tests/test_attachments.py`; edit `run.py`, `router.py`, `engines/eml.py`, `engines/msg.py`, `engines/pst.py`, `policy.py`, `cli.py`, `tests/test_pst_per_message.py`, and `tests/test_adapters_batch1.py`.
- **Policy model:** declare `AttachmentLimits(max_depth, max_members, max_member_bytes, max_total_bytes)` in one policy/config module. The policy is required on every recursion call; default values are documented/configured centrally and tested by boundary fixtures, never hidden in adapter code.
- **Child identity:** each child has `parent_source_sha256`, `parent_attachment_id`, `child_ordinal`, original filename, declared media type, and extracted-byte SHA. Its `source_uri` is a logical `attachment:` URI, while the parent source remains the root trust source. Child output paths derive from parent source hash plus child ordinal, not unsanitized attachment names.
- **Safety/error contract:** reject traversal paths, symlinks, encrypted members, duplicate member IDs, depth/size/member-limit breaches, and unsafe XML before dispatch. Enforce member/total-byte limits again while streaming decompression; on breach abort, purge partial staging data, emit `ATTACHMENT_QUARANTINED` with reason/evidence, and continue unrelated siblings unless policy says stop. Never prompt for or log passwords.
- **Tests and boundary:** cover safe child conversion, depth boundary, total/member-byte boundary, traversal/symlink/encrypted archive, PST/EML lineage, and sibling continuation. This task does not recursively execute macros, scripts, or arbitrary binaries.

**Phase 1 verification:**

```bash
unset PYTHONPATH
uv sync --locked --python 3.13
uv run --no-sync --python 3.13 pytest tests/quality tests/test_diagnostics.py tests/test_engine_plan.py tests/test_render_verify.py tests/test_model.py tests/test_tabular.py tests/test_ocr_profiles.py tests/test_attachments.py -q
uv run --no-sync --python 3.13 headcleaner benchmark tests/quality/fixtures --json
```

---

# Phase 2 of 4 — Cited, searchable, version-aware knowledge bundles

**Purpose:** Turn reliable converted output into a local, rebuildable knowledge substrate.

**Dependencies:** Phase 1 exit gate passed; the complete required locked environment is installed. SQLite FTS5 is the local baseline; Sentence Transformers and Qdrant client are required installed dependencies.

**Phase exit gate:** Every search/context result carries a stable citation to a source hash/span. Search indexes and derived semantic data can be discarded and rebuilt from canonical output.

| Task | Enhancements delivered | Create | Modify | Test |
|---:|---|---|---|---|
| 2.1 | #9 Stable cited chunks | `src/headcleaner/chunking.py`, `docs/schemas/chunk.schema.json` | `model.py`, `emit/okf.py`, `emit/manifest.py`, `cli.py` | `tests/test_chunking.py`, `tests/test_okf_schema.py` |
| 2.2 | #10 Local hybrid search | `src/headcleaner/index.py`, `src/headcleaner/search.py` | `cli.py`, `serve.py`, `mcp.py` | `tests/test_index.py`, `tests/test_search.py`, `tests/test_serve.py` |
| 2.3 | #11 Pluggable embeddings | `src/headcleaner/embeddings.py` | `index.py`, `plugins.py`, `cli.py`, `pyproject.toml`, `uv.lock` | `tests/test_embeddings.py` |
| 2.4 | #12 Entity/topic graph | `src/headcleaner/graph.py`, `docs/schemas/graph.schema.json` | `crossref.py`, `viewer.py`, `mcp.py`, `cli.py` | `tests/test_graph.py`, `tests/test_viewer.py`, `tests/test_mcp.py` |
| 2.5 | #13 Duplicate/version families | `src/headcleaner/dedupe.py` | `run.py`, `emit/manifest.py`, `emit/report.py`, `cli.py` | `tests/test_dedupe.py`, `tests/test_run.py` |
| 2.6 | #14 Element-aware diffs | `src/headcleaner/diff.py` | `cli.py`, `viewer.py`, `mcp.py`, `emit/report.py` | `tests/test_diff.py`, `tests/test_mcp.py` |
| 2.7 | #15 Contradiction/stale claims | `src/headcleaner/claims.py` | `policy.py`, `graph.py`, `emit/report.py`, `cli.py` | `tests/test_claims.py`, `tests/test_policy.py` |
| 2.8 | #16 Rename/deletion-safe sync | `src/headcleaner/sync.py` | `watch.py`, `run.py`, `emit/manifest.py`, `cli.py` | `tests/test_sync.py`, `tests/test_batch2.py` |

## Phase 2 task sequence

### Task 2.1 — Produce deterministic, cited chunks

**Objective:** Establish a chunk contract that is safe for search and agents.

**Implementation steps:**
1. Chunk typed elements by heading/path/table/code boundaries; never split a table row or source citation without an explicit continuation marker.
2. Derive stable chunk IDs from source hash, normalized element IDs, chunk ordinal, and chunking version.
3. Emit `chunks.jsonl` as an optional derivative with source URI/hash, heading path, page/span, trust state, and citation target.
4. Validate chunk schema and test identical output on cache/no-cache reruns.

**Acceptance:** Chunks are stable for unchanged input, every result traces to a source hash/span, and no chunk claims reviewed status independently of its concept.

### Task 2.2 — Implement local FTS5-first search

**Objective:** Deliver useful local retrieval with no model/server dependency.

**Implementation steps:**
1. Create a SQLite database schema for concepts, chunks, tags, source hashes, trust state, and rebuild metadata.
2. Implement deterministic FTS5 ranking/filtering and `headcleaner search` JSON/text output.
3. Add a `headcleaner index rebuild` command that reads canonical Markdown/OKF plus chunks only.
4. Reuse the index behind FastAPI and MCP only after command-level tests are green.

**Acceptance:** Deleting the index then rebuilding yields equivalent query results; filters by type/tag/path/status/source hash work; no network call occurs.

### Task 2.3 — Add explicitly selected embedding providers

**Objective:** Improve semantic recall using required installed dependencies without making a provider, model download, or cloud request implicit.

**Implementation steps:**
1. Define an embedding provider protocol with local Sentence Transformers, OpenAI-compatible HTTP, and third-party plugin implementations.
2. Cache vectors by `(chunk_hash, model_identifier, provider_version)` and invalidate deterministically.
3. Add explicit `--embedding-provider`, `--allow-network`, model, timeout, and data-boundary settings.
4. Add the Qdrant adapter using the required client dependency; SQLite remains the local baseline and Qdrant connection is activated only by explicit service configuration.

**Acceptance:** Local search works in the complete required environment with no remote-service configuration; mocked provider tests prove no HTTP is attempted without `--allow-network`; vector cache invalidates on chunk/model changes.

### Task 2.4 — Add a provenance-linked knowledge graph

**Objective:** Represent relationships without rewriting or asserting truth over user content.

**Implementation steps:**
1. Define graph nodes/edges for concepts, chunks, entities, topics, citations, and explicit cross-links.
2. Keep machine-suggested edges as `unverified`; preserve evidence chunk IDs and extraction method for every edge.
3. Emit a rebuildable `graph.jsonl`, add local graph queries, and surface evidence in viewer/MCP responses.

**Acceptance:** No edge lacks source evidence; graph round-trips through schema validation; unresolved entities/links remain warnings rather than invented connections.

### Task 2.5 — Detect duplicate and version families

**Objective:** Reduce repeated review and reveal likely canonical/latest documents without deleting anything.

**Implementation steps:**
1. Group exact duplicates by source hash.
2. Use `rapidfuzz==3.14.5` on normalized text/title/metadata fingerprints for deterministic near-duplicate candidates.
3. Add a semantic similarity pass using the required provider stack only when the active profile enables it.
4. Emit family IDs/candidate relationships in reports; expose `--apply` nowhere in this phase.

**Acceptance:** Exact and near-duplicate fixtures group correctly; false-positive candidates remain explicitly labeled candidates with score/evidence.

### Task 2.6 — Build element-aware diffs

**Objective:** Compare document meaning/structure more usefully than raw Markdown line diffs.

**Implementation steps:**
1. Align typed elements using stable IDs and similarity fallbacks.
2. Classify heading, paragraph, table-cell, attachment, frontmatter/trust, and source-hash changes.
3. Add `headcleaner diff OLD NEW` with Markdown and JSON reports; upgrade MCP’s snapshot diff only after CLI behavior is verified.

**Acceptance:** Table/formula and frontmatter fixtures identify correct changed units; unchanged documents produce an empty structured diff.

### Task 2.7 — Surface stale and potentially conflicting claims

**Objective:** Identify evidence pairs requiring attention without claiming the system knows factual truth.

**Implementation steps:**
1. Implement deterministic stale checks using existing `stale_after`, generated/review dates, and policy rules.
2. Extract structured claim candidates only from explicitly supported fields/deterministic patterns first (dates, amounts, named owners, policy labels).
3. Emit potential conflict pairs with citations, rule IDs, and confidence inputs; keep LLM comparison out of this phase.

**Acceptance:** A known conflicting fixture produces cited candidate findings; identical claims do not; policy status remains independent of the finding.

### Task 2.8 — Synchronize safely through rename/delete events

**Objective:** Make continuous ingestion preserve identity and user edits.

**Implementation steps:**
1. Extend manifest identity data with source hash, prior path, generated artifact ownership, and sync generation.
2. Detect rename by content hash before treating a file as delete/create.
3. Implement `headcleaner sync --dry-run` as default; refuse output deletion when a generated file has user modifications outside declared generated regions.
4. Wire watch events to sync logic after CLI-level preview tests pass.

**Acceptance:** Rename fixtures retain lineage, deletions are previewed, and modified output is never silently removed.

### Phase 2 authoritative implementation contracts

#### Contract 2.1 — Deterministic chunks with source citations

- **Owned files:** create `src/headcleaner/chunking.py`, `docs/schemas/chunk.schema.json`, and `tests/test_chunking.py`; edit `model.py`, `emit/okf.py`, `emit/manifest.py`, `cli.py`, and `tests/test_okf_schema.py`.
- **Data model:** define `Chunk(id, concept_id, source_sha256, element_ids, ordinal, heading_path, text, citation, token_estimate, chunking_version)`. `citation` is `{source_uri, source_sha256, page, start, end}`; `element_ids` is non-empty; `ordinal` is zero-based in source element order. ID is a digest of source SHA, ordered element IDs, ordinal, and `chunking_version`; do not use text alone.
- **Algorithm:** walk typed elements once in ordinal order. Close a chunk only at a heading boundary, after a complete table/code element, or when a configured size boundary is crossed; carry heading path forward. A table/code element is indivisible. If a single element exceeds the size boundary, emit it whole with `oversize: true`, never truncate source evidence.
- **Emission/CLI contract:** write `chunks.jsonl` atomically below the bundle output root and list its relative path, SHA, schema version, and chunking version in the manifest. When a policy selects redacted indexing, chunk from the redacted derivative; no suppressed value may enter chunks, FTS excerpts, vectors, MCP, or events. Add `headcleaner chunks BUNDLE [--rebuild] [--json]`; `--rebuild` replaces only the derived chunk file after validating canonical concepts.
- **Tests and boundary:** test deterministic rerun/cache rebuild, heading carry-forward, no table split, oversize element, missing citation rejection, and schema validation. Do not embed/vectorize, summarize, or modify canonical Markdown/OKF in this task.

#### Contract 2.2 — SQLite FTS5 local search index

- **Owned files:** create `src/headcleaner/index.py`, `src/headcleaner/search.py`, `tests/test_index.py`, and `tests/test_search.py`; edit `cli.py`, `serve.py`, `mcp.py`, and `tests/test_serve.py`.
- **Storage contract:** create one SQLite database per bundle under `<bundle>/.headcleaner/index.sqlite3`. Schema version is stored in `meta`; tables are `concept`, `chunk`, `chunk_fts` (FTS5 external-content), `tag`, `chunk_tag`, and `build`. Every row stores bundle-relative paths and source hashes, never absolute host paths.
- **Build semantics:** `index rebuild` opens a transaction, validates all chunk records first, writes into a temporary database, runs integrity check, then atomically replaces the previous database. `index update` compares concept/chunk hashes and only updates changed/deleted rows. A failed rebuild preserves the prior valid database and reports `INDEX_BUILD_FAILED`.
- **Query semantics:** implement `headcleaner search QUERY [--bundle PATH] [--tag TAG] [--type TYPE] [--status STATUS] [--path PREFIX] [--source-sha SHA] [--limit N] [--json]`. Results include rank, chunk ID, concept path, excerpt, citation, trust state, and index schema version. Reject malformed FTS syntax with a user-facing error; do not interpolate query text into SQL.
- **Tests and boundary:** test empty index, rebuild idempotence, incremental deletion, filter intersection, quoted/hostile query input, deterministic tie-break (`concept_path`, `ordinal`), and API/MCP reuse of the same search function. No remote database or embedding model is used in this task.

#### Contract 2.3 — Required embedding/provider layer with explicit data boundary

- **Owned files:** create `src/headcleaner/embeddings.py` and `tests/test_embeddings.py`; edit `index.py`, `plugins.py`, `cli.py`, `pyproject.toml`, and `uv.lock`.
- **Provider protocol:** define `EmbeddingProvider.name`, `model_id`, `dimension`, and `embed(texts) -> list[list[float]]`. Ship `local_sentence_transformer` and `openai_compatible_http` implementations; plugins implement this exact protocol. The packages are required, but provider selection is explicit configuration—there is no implicit model download or HTTP request.
- **Cache/storage contract:** cache by `sha256(chunk_text)`, provider name, model ID, dimension, and provider implementation version. Store vectors in a versioned local table/file with the source chunk ID; reject a dimension/model mismatch rather than mixing vectors. On a configured model/dimension change, invalidate/recreate the Qdrant collection before any new upsert. Index/vector rebuild and sync delete orphaned local/Qdrant vectors. Qdrant adapter receives the same stable IDs and metadata; it may connect only when a configured endpoint exists.
- **CLI/error contract:** add `headcleaner index embed BUNDLE --provider NAME --model MODEL [--allow-network] [--timeout SECONDS]`. Local provider requires a readable locally available model path; missing model returns `EMBEDDING_MODEL_UNAVAILABLE`. HTTP provider refuses before request unless both provider is selected and `--allow-network` is present. Never include full chunk text in logs.
- **Tests and boundary:** use a deterministic fake provider for dimensions/cache/invalidation; mock HTTP and assert zero calls without permission; test local-model-missing and Qdrant-metadata payload. Do not make a remote vector service necessary for search or conversion.

#### Contract 2.4 — Evidence-linked graph derivative

- **Owned files:** create `src/headcleaner/graph.py`, `docs/schemas/graph.schema.json`, and `tests/test_graph.py`; edit `crossref.py`, `viewer.py`, `mcp.py`, `cli.py`, `tests/test_viewer.py`, and `tests/test_mcp.py`.
- **Data model:** define `GraphNode(id, kind, label, source_refs, attributes)` and `GraphEdge(id, kind, from_id, to_id, evidence_chunk_ids, method, status)`. Node kinds are `concept|chunk|entity|topic`; edge kinds are `contains|cites|mentions|related_to|duplicate_candidate|conflicts_candidate`. Edge `status` is exactly `explicit|unverified`; every edge requires one or more evidence chunk IDs except `contains`.
- **Build semantics:** generate explicit containment/citation edges deterministically from chunks and frontmatter. Entity/topic/similarity edges are suggestions, record the generating method/version, and are rebuilt from canonical/chunk data. Never overwrite a user-authored explicit cross-reference with a generated edge.
- **Query/output contract:** write `graph.jsonl` atomically under the bundle derivative directory; provide `headcleaner graph query NODE [--depth N] [--kind KIND] [--json]`. Viewer/MCP responses must include evidence chunk IDs and must hide edges excluded by active policy.
- **Tests and boundary:** test stable IDs, rejected dangling evidence, duplicate-node coalescing only with identical canonical identity, directed traversal depth, policy filtering, and schema round-trip. Do not treat suggested graph edges as factual claims or feed them into review approval automatically.

#### Contract 2.5 — Exact duplicates and version-family candidates

- **Owned files:** create `src/headcleaner/dedupe.py` and `tests/test_dedupe.py`; edit `run.py`, `emit/manifest.py`, `emit/report.py`, `cli.py`, and `tests/test_run.py`.
- **Data model:** define `DocumentFamily(id, exact_members, candidate_members, signals, algorithm_version)`. Exact membership is source-SHA equality. Candidate membership stores each pair as `{left_id, right_id, title_score, content_score, path_score, combined_score, evidence}` and is symmetric/canonically ordered.
- **Algorithm:** group exact hashes first. Compute RapidFuzz scores against normalized title/body/path fingerprints only after excluding frontmatter timestamps, generated fields, and volatile report content. Thresholds are named configuration values with an algorithm version; scores at/below threshold are omitted rather than stored as false candidates.
- **CLI/error contract:** add `headcleaner dedupe BUNDLE [--threshold FLOAT] [--json]`. Threshold outside `[0, 1]`, missing manifests, or mixed bundle roots fail before writing. The command writes a derivative report and manifests candidate links; it never deletes, merges, renames, or marks a document current.
- **Tests and boundary:** test exact duplicate, near duplicate, below threshold, timestamp-only difference, stable pair ordering, and no source/output mutation. Semantic vectors may contribute only when a selected provider has already populated version-compatible cache data.

#### Contract 2.6 — Element-aware semantic diff

- **Owned files:** create `src/headcleaner/diff.py` and `tests/test_diff.py`; edit `cli.py`, `viewer.py`, `mcp.py`, `emit/report.py`, and `tests/test_mcp.py`.
- **Data model:** define `DiffResult(left_ref, right_ref, summary, changes, algorithm_version)` and `ElementChange(kind, status, left_element_id, right_element_id, before, after, citation)`. `status` is `added|removed|modified|moved|unchanged`; `kind` comes from the typed-element enum. A frontmatter/trust difference is a separate named change, not embedded in body text.
- **Alignment rule:** align deterministic element IDs first. For unmatched elements, only compare within the same kind and nearest heading context; use a documented similarity threshold with deterministic tie-break. Tables compare cell coordinates; no raw Markdown line diff is used as the source of truth.
- **CLI/output contract:** `headcleaner diff LEFT RIGHT [--format text|json|md] [--include-unchanged]`. Validate both inputs belong to readable canonical bundles or files. JSON is schema-versioned; Markdown report cites both source locations. MCP delegates to this function and adds no alternate diff algorithm.
- **Tests and boundary:** cover heading move, paragraph text change, table-cell change, attachment add/remove, trust frontmatter change, exact equality, and ambiguous alignment. Do not apply patches or automatically resolve a conflict.

#### Contract 2.7 — Staleness and contradiction candidates

- **Owned files:** create `src/headcleaner/claims.py` and `tests/test_claims.py`; edit `policy.py`, `graph.py`, `emit/report.py`, `cli.py`, and create `tests/test_policy.py` if absent.
- **Data model:** define `ClaimCandidate(id, kind, normalized_value, source_chunk_id, citation, extraction_rule, status)` and `Finding(id, type, severity, claim_ids, evidence, rule_id)`. Initial claim kinds are only `date|amount|owner|status_label`; status is `extracted|unverified|suppressed`. Rule IDs are declared in policy configuration.
- **Detection rule:** stale findings derive solely from existing `stale_after`/generated/review fields. Extract at most 5,000 claims per document; emit `CLAIMS_TOO_MANY` and skip pairwise comparison above that cap. Conflict findings require two normalized claims of the same kind with unequal values and compatible scope selected by an explicit rule. Every finding retains both citations and must use the label `potential_conflict`, never `false` or `contradiction` as fact.
- **CLI/error contract:** `headcleaner claims BUNDLE [--policy PACK] [--json]` produces a report; malformed rule config fails schema validation before scan. Suppression is policy-recorded with a reason and does not erase source claims.
- **Tests and boundary:** test stale date, matching values, incompatible values, scope exclusion, suppression, rule-version serialization, and no LLM/network call. This task does not decide truth, update frontmatter, or change review state.

#### Contract 2.8 — Rename/deletion-safe synchronization

- **Owned files:** create `src/headcleaner/sync.py` and `tests/test_sync.py`; edit `watch.py`, `run.py`, `emit/manifest.py`, `cli.py`, and `tests/test_batch2.py`.
- **State model:** define `SyncRecord(source_sha256, current_relpath, prior_relpaths, generated_paths, generation, output_hashes, last_seen_at)`, keyed by `(current_relpath, source_sha256)` so identical-content files retain distinct lineage, stored in bundle-local `.headcleaner/sync.json` through atomic write/rename. Do not use absolute source paths as identity.
- **Reconciliation rule:** match unchanged source SHA before path; a matching SHA at a different path is `renamed`. A missing prior SHA is `deleted_candidate`; it cannot delete generated artifacts until dry-run/apply comparison proves the files are generated-owned and their recorded output hashes still match.
- **CLI/error contract:** `headcleaner sync INPUT OUTPUT [--dry-run] [--apply] [--prune-generated] [--json]`, with `--dry-run` default and `--apply` mandatory for any write/delete. `--prune-generated` refuses modified/user-owned files and reports `SYNC_CONFLICT` with paths/hashes. Watch invokes sync in dry-run planning mode, then uses the configured explicit apply policy.
- **Tests and boundary:** cover rename, create, delete candidate, changed generated file, partial failed run/restart, atomic-state corruption, and watcher event coalescing. Never move/delete a source file or overwrite user edits.

**Phase 2 verification:**

```bash
unset PYTHONPATH
uv sync --locked --python 3.13
uv run --no-sync --python 3.13 pytest tests/test_chunking.py tests/test_index.py tests/test_search.py tests/test_dedupe.py tests/test_diff.py tests/test_claims.py tests/test_sync.py -q
uv sync --locked --python 3.13
uv run --no-sync --python 3.13 pytest tests/test_embeddings.py tests/test_graph.py -q
```

---

# Phase 3 of 4 — Human-governed safety, review, and provenance

**Purpose:** Make the intelligent output safe to inspect, share, and govern without weakening the human-review boundary.

**Dependencies:** Phases 1–2 exit gates passed; the complete required locked environment and required system-tool contract remain installed.

**Phase exit gate:** A reviewer can audit evidence and make an explicit decision; sensitive/hostile content is surfaced before downstream exposure; all automated status remains unverified until a human action.

| Task | Enhancements delivered | Create | Modify | Test |
|---:|---|---|---|---|
| 3.1 | #17 Evidence workbench | `src/headcleaner/review_workbench.py` | `review.py`, `tui.py`, `viewer.py`, `emit/report.py`, `cli.py` | `tests/test_review_workbench.py`, `tests/test_batch5_review.py`, `tests/test_viewer.py` |
| 3.2 | #18 Policy packs | `docs/policies/*.toml`, `src/headcleaner/policy_packs.py` | `policy.py`, `cli.py`, `docs/SCHEMA.md` | `tests/test_policy_packs.py`, `tests/test_okf_schema.py` |
| 3.3 | #19 PII/secrets proposal redaction | `src/headcleaner/redact.py`, `docs/schemas/redaction.schema.json` | `model.py`, `emit/okf.py`, `policy.py`, `cli.py` | `tests/test_redact.py` |
| 3.4 | #20 Hostile-file inspection/quarantine | `src/headcleaner/inspect.py` | `attachments.py`, `router.py`, `run.py`, `doctor.py`, `cli.py` | `tests/test_inspect.py`, `tests/test_attachments.py` |
| 3.5 | #21 Reproducible attestations | `docs/schemas/attestation.schema.json` | `attest.py`, `cli.py`, `pyproject.toml`, `uv.lock` | `tests/test_attest.py`, `tests/test_attestation_schema.py` |
| 3.6 | #22 Risk-based review queues | `src/headcleaner/review_queue.py` | `review.py`, `diagnostics.py`, `policy.py`, `emit/manifest.py`, `cli.py` | `tests/test_review_queue.py` |
| 3.7 | #23 Readiness grades | `src/headcleaner/readiness.py`, `docs/schemas/readiness.schema.json` | `policy.py`, `diagnostics.py`, `emit/report.py`, `cli.py` | `tests/test_readiness.py` |
| 3.8 | #24 Benchmark transparency | `scripts/render_benchmark_dashboard.py`, `docs/QUALITY.md` | `.github/workflows/test.yml`, `benchmark.py`, `docs/CONTRIBUTING.md` | `tests/quality/test_dashboard.py` |

## Phase 3 task sequence

### Task 3.1 — Build an evidence-oriented review workbench

**Objective:** Let a human review the conversion with source/output/diagnostic evidence before changing trust status.

**Implementation steps:**
1. Add review panes for source reference, rendered output, element/chunk citations, diagnostics, diff findings, and policy violations.
2. Keep `approve`/`reject` as explicit operations in `review.py`; append reason/evidence references and preserve current audit fields.
3. Produce a static review packet when a TUI is unavailable; never send document content remotely.

**Acceptance:** Approve/reject tests still require human-invoked functions; a reviewer can navigate from a finding to cited output/source evidence.

### Task 3.2 — Ship versioned policy packs

**Objective:** Turn the current minimal TOML trust checker into reusable and testable governance profiles.

**Implementation steps:**
1. Define pack metadata/versioning and include `research`, `publication`, `pii-safe`, `rag-ready`, and `legal-hold` examples.
2. Add deterministic rules for diagnostics, sources, stale state, citations, prohibited locations, readiness score, and redaction status.
3. Add `headcleaner policy test` and a dry-run report with severity/exit-code rules.

**Acceptance:** Every sample pack has passing/failing fixture tests and schema validation; policy passes never imply human review.

### Task 3.3 — Add proposed redaction derivatives

**Objective:** Detect sensitive content and create traceable proposed redactions without mutating originals/canonical output.

**Implementation steps:**
1. Use deterministic secret patterns first; add Presidio as an opt-in detector for PII categories.
2. Produce a proposal report with category, span/citation, confidence/source detector, and replacement token.
3. Generate a separate redacted derivative only after `--write-redacted`; preserve the canonical output and provenance link.
4. Prohibit raw sensitive snippets in logs/webhooks by default.

**Acceptance:** Synthetic-only secret/PII fixtures detect expected spans; no original file changes; redacted derivatives retain source and redaction metadata.

### Task 3.4 — Inspect and quarantine hostile files before engines run

**Objective:** Safely handle untrusted inboxes.

**Implementation steps:**
1. Add `headcleaner inspect` for MIME/signature, archive limits, macro/embedded-object inventory, encryption, and policy assessment.
2. Gate recursive extraction and configured engines on inspection findings and declared policy.
3. Provide external AV scanner hooks as explicit commands/configuration, not bundled behavior.

**Acceptance:** Archive traversal, zip-bomb simulation, mismatched extension, encrypted document, and macro fixture outcomes are deterministic and non-executing.

### Task 3.5 — Upgrade attestations to reproducible statements

**Objective:** Bind generated output to source/config/engine evidence and optionally sign it.

**Implementation steps:**
1. Fix version metadata to derive from `headcleaner.__version__`, not historical constants.
2. Extend the attestation payload with source/output/config hashes, adapter/engine version/capability records, and lock-file hash.
3. Add JSON Schema validation and in-toto statement emission with the required `in-toto==3.1.0` dependency when the user invokes signing/export.
4. Retain current Merkle/Ed25519 support via `cryptography==50.0.0`; do not require a key for unsigned integrity verification.

**Acceptance:** Existing attestation tests pass; signed/unsigned, changed-config, and changed-output tests are covered; an attestation never states that content was human-reviewed.

### Task 3.6 — Prioritize review queues by evidenced risk

**Objective:** Focus human attention where it improves trust most.

**Implementation steps:**
1. Score risk from diagnostics, OCR/fallback use, sensitivity findings, age, policy failures, source type, and reproducible sampling seed.
2. Store score components rather than a magic opaque score.
3. Add queue filters and preserve reviewer decisions in the existing review audit path.

**Acceptance:** Queue ordering is reproducible from the same manifest/policy/seed and explanations list every factor.

### Task 3.7 — Grade RAG/agent readiness transparently

**Objective:** Report whether content is appropriate for retrieval/agent exposure.

**Implementation steps:**
1. Define a schema-versioned readiness report from citations, chunk cohesion, table/OCR diagnostics, PII/redaction state, freshness, policy, and review state.
2. Make it an evidence report, not a security certification.
3. Allow policy packs to set minimum thresholds for specific publishing routes.

**Acceptance:** Every deduction is cited to a field/finding; a successful conversion cannot automatically receive a high readiness grade.

### Task 3.8 — Publish safe benchmark transparency

**Objective:** Make quality results inspectable without disclosing private documents.

**Implementation steps:**
1. Render static benchmark summaries from public/attributed fixtures only.
2. Include engine versions, platform, baseline version, known limitations, and metric deltas.
3. Attach the report to CI artifacts; publication remains a separate release/documentation decision.

**Acceptance:** Dashboard generator is deterministic and rejects non-public fixture paths.

### Phase 3 authoritative implementation contracts

#### Contract 3.1 — Evidence-first review workbench

- **Owned files:** create `src/headcleaner/review_workbench.py` and `tests/test_review_workbench.py`; edit `review.py`, `tui.py`, `viewer.py`, `emit/report.py`, `cli.py`, `tests/test_batch5_review.py`, and `tests/test_viewer.py`.
- **State contract:** retain the existing review state model as the only authority. A workbench item is a projection `{concept_ref, review_state, diagnostics, policy_findings, diff_refs, citations}`; it cannot mutate frontmatter directly. Approval/rejection requires `reviewer`, `decision`, `reason`, timestamp, and selected evidence references.
- **UI/output contract:** Textual and static packet renderers consume the same `ReviewPacket` object. Pane order is fixed: summary, source/citation, output element/chunk, diagnostics, policy, diff, decision. Missing source preview yields a labeled unavailable pane, never a fabricated preview.
- **CLI/error contract:** add `headcleaner review-workbench BUNDLE [--concept ID] [--format tui|html|json]`. TUI is selected only when terminal support exists; HTML/JSON are offline static derivatives. A decision command refuses absent reason/evidence and never changes `verified` through a browse-only action.
- **Tests and boundary:** test pane evidence linkage, missing preview, required-decision fields, immutable browse path, and audit append behavior. No remote source retrieval, bulk approval, or machine auto-approval.

#### Contract 3.2 — Versioned policy packs

- **Owned files:** create `src/headcleaner/policy_packs.py`, `docs/policies/*.toml`, and `tests/test_policy_packs.py`; edit `policy.py`, `cli.py`, `docs/SCHEMA.md`, and `tests/test_okf_schema.py`.
- **Pack schema:** every TOML pack declares `id`, `version`, `extends`, `description`, and `rules`. Rules have stable `id`, `severity`, `when`, and `message`; conditions address only documented manifest/diagnostic/readiness/redaction fields. Resolve `extends` depth-first only from installed pack IDs or normalized descendants of the active bundle's `.headcleaner/policies/`; reject absolute paths, `..`, escaping symlinks, all URI schemes, cycles, duplicate rule IDs, unknown field paths, and versionless packs before any read/network action.
- **Evaluation contract:** return ordered `PolicyFinding(rule_id, severity, message, concept_ref, evidence)` records. Severity is exactly `info|warning|error`; rule evaluation is pure and deterministic for one input bundle/pack. A pass means no matched error rule, not human approval or factual verification.
- **CLI/error contract:** `headcleaner policy test BUNDLE --pack ID [--json]` and `headcleaner policy explain --pack ID --rule ID`. Missing/invalid packs fail before conversion/index mutation. Exit code is zero with no error findings, one with policy errors, and two for invalid invocation/config.
- **Tests and boundary:** cover inheritance, cycle, severity/exit code, missing evidence, version serialization, and sample pack pass/fail fixtures. No arbitrary Python expressions or network lookups in policy files.

#### Contract 3.3 — Proposed PII/secret redaction derivatives

- **Owned files:** create `src/headcleaner/redact.py`, `docs/schemas/redaction.schema.json`, and `tests/test_redact.py`; edit `model.py`, `emit/okf.py`, `policy.py`, and `cli.py`.
- **Data model:** define `RedactionFinding(id, category, detector, confidence, citation, replacement, status)` where status is `proposed|suppressed|applied_to_derivative`; store only source coordinates and a cryptographic digest of the matched value in persistent reports. Raw matched text may exist transiently in memory only to build the replacement.
- **Detector order:** run deterministic secret regexes first, then the required Presidio analyzer if configured by policy. Dedupe overlapping spans using documented longest-span/priority rules. Every detector result cites element/chunk/source span and retains detector/version metadata.
- **Write contract:** `headcleaner redact BUNDLE [--write-derivative] [--policy PACK] [--json]`. Without `--write-derivative`, emit proposal report only. With it, write a separate `_redacted/` derivative that links to the canonical concept and lists findings; never overwrite canonical output, source file, manifest, or review record.
- **Tests and boundary:** use synthetic identifiers only; test overlap, suppression, no raw value in JSON/logs, canonical immutability, and derivative linkage. Redaction proposal/application does not set review/verification status.

#### Contract 3.4 — Inspect/quarantine untrusted inputs

- **Owned files:** create `src/headcleaner/inspect.py` and `tests/test_inspect.py`; edit `attachments.py`, `router.py`, `run.py`, `doctor.py`, `cli.py`, and `tests/test_attachments.py`.
- **Inspection result:** define `InspectionResult(source_ref, declared_type, detected_type, archive_summary, encryption, macro_indicators, findings, disposition)`. `disposition` is exactly `allow|quarantine|reject`; findings are diagnostics with evidence fields, never executable payloads.
- **Execution order:** inspection runs before adapter selection, attachment expansion, OCR, or rendering. Compare extension, declared MIME, and bounded byte signature; scan archive inventory without extracting unsafe members. Route only `allow`; retain a quarantine record for `quarantine`; do not invoke any engine for `reject`.
- **CLI/error contract:** `headcleaner inspect INPUT [--policy PACK] [--json]`; conversion reports inspection disposition per file. Quarantine directory is bundle-local and contains metadata/report only unless an explicit evidence-copy policy is enabled. External scanner execution requires explicit configured command and sanitized argument list.
- **Tests and boundary:** test mismatch, traversal archive, encryption, macro marker, malformed file, policy overrides, and no engine invocation after rejection. Never execute macros, Office documents, shell content, or user-configured scanner commands in unit tests.

#### Contract 3.5 — Reproducible attestations and in-toto statements

- **Owned files:** create `docs/schemas/attestation.schema.json` and `tests/test_attestation_schema.py`; edit `attest.py`, `cli.py`, `pyproject.toml`, `uv.lock`, and `tests/test_attest.py`.
- **Statement contract:** canonicalize JSON with sorted keys/UTF-8/no insignificant whitespace before signing. Predicate includes `tool_version`, `lock_sha256`, normalized configuration SHA, source/output SHA sets, engine capability/versions, timestamp, and schema version. Exclude absolute paths, hostnames, usernames, wall-clock nondeterminism from the signed subject/predicate except the explicitly declared timestamp field.
- **Signing semantics:** replace duplicate-last-leaf Merkle construction with RFC 9162 split-point construction consistently for roots and inclusion proofs; `[A,B,C]` and `[A,B,C,C]` must differ. `headcleaner attest BUNDLE [--key PATH] [--in-toto PATH] [--verify]`. No key produces an unsigned integrity statement; `--key` signs only the canonical payload; `--verify` performs no write. In-toto emission consumes the same payload and cannot add claims of review/approval.
- **Error contract:** missing/unreadable key, invalid signature, schema failure, or changed output/config returns non-zero with a named error code; do not generate a replacement key or silently sign with another identity.
- **Tests and boundary:** test canonical-byte stability, sign/verify, changed source/output/config/lock failure, unsigned validity, schema validation, and version sourced from `headcleaner.__version__`. No key material is committed, logged, or placed in fixtures.

#### Contract 3.6 — Explainable risk-based review queues

- **Owned files:** create `src/headcleaner/review_queue.py` and `tests/test_review_queue.py`; edit `review.py`, `diagnostics.py`, `policy.py`, `emit/manifest.py`, and `cli.py`.
- **Data model:** define `QueueItem(concept_ref, priority, factors, state, created_at)` where `factors` is an ordered list of `{rule_id, value, weight, contribution, evidence}`. Priority is a numeric sort key plus deterministic tie-break (`source_sha256`, concept path); queue state is `pending|claimed|decided|suppressed`.
- **Scoring contract:** only registered factor functions may contribute: diagnostic severity, OCR/fallback state, sensitivity findings, policy errors, stale state, and age. Each pack declares weights; missing evidence contributes zero plus a diagnostic, never an assumed risk. Store score version and factor inputs so the exact priority can be recalculated.
- **CLI/error contract:** `headcleaner review queue BUNDLE [--pack ID] [--limit N] [--json]` and `review claim ITEM --reviewer ID`. Claim/decision updates append audit state; no queue command changes document trust state by itself.
- **Tests and boundary:** test deterministic ordering, tie break, missing factor, pack-weight change, claim race/duplicate claim, suppression reason, and decision removal. Do not use opaque ML ranking.

#### Contract 3.7 — Evidence-based readiness grades

- **Owned files:** create `src/headcleaner/readiness.py`, `docs/schemas/readiness.schema.json`, and `tests/test_readiness.py`; edit `policy.py`, `diagnostics.py`, `emit/report.py`, and `cli.py`.
- **Data model:** define `ReadinessReport(concept_ref, grade, score, deductions, requirements, schema_version)`. Grade is exactly `blocked|needs_review|conditional|ready`; each deduction/requirement carries rule ID, value, threshold, contribution, and citation/finding reference.
- **Evaluation contract:** start from a documented maximum score and apply only declared deductions for citation completeness, chunk integrity, OCR/table diagnostics, redaction state, freshness, policy, and human review. Missing inputs yield `needs_review`/deduction, never optimistic readiness. A `ready` grade is a suitability signal for a named profile, not a security certification or factual guarantee.
- **CLI/error contract:** `headcleaner readiness BUNDLE [--profile NAME] [--json]`; report generation is read-only. Policy packs may consume the report but cannot rewrite it. Unknown profile/schema mismatch fails explicitly.
- **Tests and boundary:** cover each grade, every deduction explanation, missing citation, stale content, unreviewed content, redaction finding, deterministic repeat, and schema validation. No readiness outcome may overwrite `verified`.

#### Contract 3.8 — Public benchmark transparency artifact

- **Owned files:** create `scripts/render_benchmark_dashboard.py`, `docs/QUALITY.md`, and `tests/quality/test_dashboard.py`; edit `.github/workflows/test.yml`, `benchmark.py`, and `docs/CONTRIBUTING.md`.
- **Input/output contract:** renderer accepts only validated `tests/quality/baseline.json`, current benchmark result JSON, and `ATTRIBUTION.md`. It emits a self-contained static HTML/JSON artifact with fixture IDs, metric deltas, engine versions, platform, baseline schema, and known limitations. It rejects file paths outside `tests/quality/fixtures` and any fixture marked non-public.
- **CI contract:** workflow uploads the generated artifact for the quality job; it does not publish externally, modify baseline, or upload original fixture bytes. A failed dashboard generation fails the quality job.
- **Tests and boundary:** test deterministic output excluding generated timestamps, rejected private path, missing attribution, delta direction, escaped fixture labels, and no network calls. Do not add product analytics/telemetry or a hosted dashboard.

**Phase 3 verification:**

```bash
unset PYTHONPATH
uv sync --locked --python 3.13
uv run --no-sync --python 3.13 pytest tests/test_review_workbench.py tests/test_policy_packs.py tests/test_redact.py tests/test_inspect.py tests/test_attest.py tests/test_review_queue.py tests/test_readiness.py tests/quality/test_dashboard.py -q
```

---

# Phase 4 of 4 — Citation-first agents, services, and extensible automation

**Purpose:** Expose the trusted knowledge substrate through stable local interfaces, then safely expand into persistent jobs, integrations, and plugin ecosystems.

**Dependencies:** Phases 1–3 exit gates passed; the complete required locked environment, including `mcp==1.29.0`, `httpx==0.28.1`, and `tenacity==9.1.4`, is installed. Outbound delivery remains an explicit runtime configuration.

**Phase exit gate:** Agent/API/event/integration clients receive schema-versioned, cited, policy-bounded data. Local CLI behavior remains fully functional without a running service or network access.

| Task | Enhancements delivered | Create | Modify | Test |
|---:|---|---|---|---|
| 4.1 | #25 Citation-first MCP retrieval | `docs/schemas/mcp-tools.schema.json` | `mcp.py`, `index.py`, `chunking.py`, `policy.py`, `pyproject.toml`, `uv.lock` | `tests/test_mcp.py`, `tests/test_mcp_citations.py` |
| 4.2 | #26 Agent context packages | `src/headcleaner/context_pack.py`, `docs/schemas/context-pack.schema.json` | `mcp.py`, `cli.py`, `index.py` | `tests/test_context_pack.py` |
| 4.3 | #27 Routing profiles | `src/headcleaner/profiles.py`, `docs/schemas/profile.schema.json`, `docs/profiles/*.toml` | `run.py`, `router.py`, `cli.py`, `doctor.py` | `tests/test_profiles.py`, `tests/test_engine_plan.py` |
| 4.4 | #28 Durable job queue | `src/headcleaner/jobs.py`, `src/headcleaner/job_store.py` | `serve.py`, `watch.py`, `run.py`, `cli.py` | `tests/test_jobs.py`, `tests/test_serve.py`, `tests/test_watch.py` |
| 4.5 | #29 Signed versioned events | `docs/schemas/event.schema.json` | `webhook.py`, `jsonlog.py`, `jobs.py`, `cli.py` | `tests/test_webhook.py`, `tests/test_jsonlog.py`, `tests/test_events.py` |
| 4.6 | #30 Safe connector sync | `src/headcleaner/connectors.py` | `obsidian.py`, `notion.py`, `git_commit.py`, `sync.py`, `cli.py` | `tests/test_connector_sync.py`, `tests/test_notion_import.py` |
| 4.7 | #31 Plugin capability/conformance | `src/headcleaner/plugin_contract.py`, `tests/plugin_conformance/` | `plugins.py`, `router.py`, `doctor.py`, `docs/PLUGINS.md` | `tests/test_plugin_contract.py`, `tests/test_plugins.py` |
| 4.8 | #32 Stable automation API | `docs/schemas/event-v1.schema.json`, `docs/AUTOMATION_API.md` | `jsonlog.py`, `cli.py`, `webhook.py`, `mcp.py` | `tests/test_jsonlog.py`, `tests/test_automation_contract.py` |

## Phase 4 task sequence

### Task 4.1 — Make MCP retrieval citation-first

**Objective:** Upgrade the existing MCP server so agent retrieval always returns bounded, attributable evidence.

**Implementation steps:**
1. Keep the current 14 MCP tools working under the pinned 1.x API; add the five named retrieval tools without replacing any current tool.
2. Add search/get-chunk/diagnostic/readiness/review-queue tools powered by Phase 2 indexes and Phase 3 reports.
3. Require every content-bearing response to include bundle, concept/chunk ID, source URI/hash, location/span, trust/review state, and schema version.
4. Enforce configured bundle roots and policy filters before loading or returning content.

**Acceptance:** MCP contract tests prove every search/result path is cited, access is root-bounded, and policy-blocked content is not returned.

### Task 4.2 — Generate bounded agent context packages

**Objective:** Give agents the smallest useful, cited, policy-compliant context for a task.

**Implementation steps:**
1. Select chunks by query, topic, graph neighborhood, profile, or explicit file set.
2. Enforce deterministic byte/token limits and inclusion order; record omitted chunks/reasons.
3. Emit Markdown and JSONL packages with a manifest containing source/review/readiness status.
4. Expose the same engine through CLI first, then MCP.

**Acceptance:** Same inputs/configuration generate byte-stable packages; every included passage has a citation and every omitted item has a reason.

### Task 4.3 — Add declarative routing profiles

**Objective:** Safely configure document classes without hard-coding organization-specific behavior.

**Implementation steps:**
1. Define TOML profile schema for filename/metadata/text predicates, engine/OCR selection, policy pack, chunking settings, output root, and review priority.
2. Evaluate profiles deterministically with explicit precedence/conflict errors.
3. Add `--profile` and `--dry-run` reporting; doctor validates referenced tools and prohibited network settings.

**Acceptance:** Profile fixtures prove precedence, invalid-schema errors, dry-run behavior, and no implicit remote classification.

### Task 4.4 — Add a durable local job queue

**Objective:** Make multi-folder/continuous ingestion recoverable across process restarts.

**Implementation steps:**
1. Use SQLite for job metadata, transitions, attempts, source/output roots, and append-only logs; do not introduce a server dependency.
2. Run the existing CLI pipeline as the canonical worker path.
3. Add submit/status/cancel/retry APIs/CLI commands with configured concurrency/resource limits.
4. Keep FastAPI bound to localhost by default and require an explicit security configuration before non-loopback binding.

**Acceptance:** Restart/retry/cancel fixture tests preserve job state and source provenance; ordinary `headcleaner convert` works without the queue.

### Task 4.5 — Formalize event/webhook delivery

**Objective:** Turn the current one-shot webhook into a safe, versioned event contract.

**Implementation steps:**
1. Define event names: `conversion.completed`, `conversion.failed`, `review.required`, `policy.failed`, `bundle.updated`, and job lifecycle events.
2. Include schema version, run/job ID, summary, citation-safe artifact references, and no raw sensitive content by default.
3. Add optional HMAC signatures, retry/backoff via `tenacity==9.1.4`, and a persisted dead-letter record.
4. Keep outbound URLs disabled unless explicitly configured and allowlisted.

**Acceptance:** Schema/signature/retry/dead-letter tests pass; network is never used by default; JSON log events remain valid offline.

### Task 4.6 — Add conflict-safe connector synchronization

**Objective:** Make existing Obsidian, Notion, and Git features safely interoperable rather than write-only helpers.

**Implementation steps:**
1. Define connector ownership maps for source fields, generated fields, and user-owned fields.
2. Reuse Phase 2 sync identity and diff logic for preview/conflict reporting.
3. Add `--dry-run` as default for any bidirectional operation; require explicit apply and retain sync state locally.
4. Mock Notion/Git interactions in tests; no live external mutation occurs in test suites.

**Acceptance:** User-owned changes survive sync; conflict fixtures produce actionable reports; no connector performs destructive actions in preview mode.

### Task 4.7 — Harden the plugin ecosystem

**Objective:** Make third-party adapters discoverable, diagnosable, and compatible without destabilizing core conversion.

**Implementation steps:**
1. Define a plugin manifest with extensions, required system/Python capabilities, network/data behavior, settings schema, supported element features, and compatible headcleaner range.
2. Keep legacy `Adapter` entry points valid; missing manifest means reduced capability metadata, not plugin breakage.
3. Add doctor capability output and a reusable conformance fixture suite for plugin authors.
4. Add optional isolated execution only after the manifest and contract suite are mature.

**Acceptance:** Existing plugin tests continue to pass; valid/invalid manifest fixtures yield predictable doctor/conformance outcomes.

### Task 4.8 — Freeze a stable automation API v1

**Objective:** Make CLI JSON, service responses, webhooks, and MCP-adjacent machine outputs contract-safe for downstream systems.

**Implementation steps:**
1. Define common envelope fields: `schema_version`, `event`, `run_id`, `timestamp`, `status`, `data`, `warnings`, and `errors`.
2. Publish JSON Schemas and compatibility rules: additive fields are allowed; breaking changes require a new major schema version and migration notes.
3. Version existing `--json` events without removing a documented compatibility mode during the deprecation window.
4. Add client examples for shell, Python, GitHub Actions, local service, and MCP consumers.

**Acceptance:** Contract fixtures validate every emitted event; compatibility tests reject accidental field removals/renames; CLI exit code behavior is documented and tested.

### Phase 4 authoritative implementation contracts

#### Contract 4.1 — Citation-first MCP retrieval

- **Owned files:** create `docs/schemas/mcp-tools.schema.json` and `tests/test_mcp_citations.py`; edit `mcp.py`, `index.py`, `chunking.py`, `policy.py`, `pyproject.toml`, `uv.lock`, and `tests/test_mcp.py`.
- **Compatibility/data:** preserve the 14 current tool names under `mcp==1.29.0`; add only `search_chunks`, `get_chunk`, `get_diagnostics`, `get_readiness`, and `list_review_queue` (19 total). Every content response is `{schema_version,bundle_id,concept_id,chunk_id,source_uri,source_sha256,location,trust_state,review_state,data}`. Empty results are `items: []`; denials contain no content excerpt.
- **Access/error:** configure bundle root before start; canonicalize/reject traversal before read; apply policy/readiness/redaction filters before loading. Invalid ID, missing index, schema mismatch, and policy denial have distinct stable codes. MCP starts no remote provider/service.
- **Tests/boundary:** test old tools, citation completeness, root traversal, denied/empty/missing-index cases, and schema. Retrieval tools never write, review, or sync.

#### Contract 4.2 — Deterministic context packages

- **Owned files:** create `src/headcleaner/context_pack.py`, `docs/schemas/context-pack.schema.json`, and `tests/test_context_pack.py`; edit `mcp.py`, `cli.py`, and `index.py`.
- **Data/selection:** `ContextPack(id,query,selection_rules,included,omitted,byte_budget,token_estimate,manifest)` hashes ordered chunk IDs/config/schema. Search, filter by root/policy/readiness, dedupe, rank by score plus `concept_path,ordinal`, then include whole chunks only. Omitted items use exactly `budget|policy|duplicate|low_rank|missing_content`.
- **CLI/write:** `headcleaner context BUNDLE QUERY [--max-bytes N] [--format md|jsonl] [--include ID] [--json]` writes atomically beneath `_context/<pack_id>.*`; MCP delegates to this builder. Invalid budget/index/query fails before write.
- **Tests/boundary:** test byte boundary, policy exclusion, deterministic output, explicit selector order, omission reasons, no network, and no review-state mutation.

#### Contract 4.3 — Declarative routing profiles

- **Owned files:** create `src/headcleaner/profiles.py`, `docs/schemas/profile.schema.json`, `docs/profiles/*.toml`, and `tests/test_profiles.py`; edit `run.py`, `router.py`, `cli.py`, `doctor.py`, and `tests/test_engine_plan.py`.
- **Schema/resolution:** profile has `id,version,priority,match,engine,ocr_profile,policy_pack,chunking,output_root,review_priority`; match is only `path_glob|extension|metadata_equals|text_anchor`. Order by descending priority then ID; equal-priority conflicting engine/output settings fail. Persist selected IDs/versions/config hash in manifest.
- **CLI/error:** `convert INPUT OUTPUT --profile ID [--dry-run]`; dry-run creates no output and displays resolved engine/policy. Doctor validates profile schema, tool/language/policy availability, output-root containment, and network setting.
- **Tests/boundary:** no match, precedence, conflict, malformed schema, dry-run no-write, manifest persistence. Profile cannot bypass inspection, policy, or explicit network permission.

#### Contract 4.4 — Durable local job queue

- **Owned files:** create `src/headcleaner/jobs.py`, `src/headcleaner/job_store.py`, `tests/test_jobs.py`, and `tests/test_watch.py`; edit `serve.py`, `watch.py`, `run.py`, `cli.py`, and `tests/test_serve.py`.
- **State:** SQLite tables `job,job_event,job_attempt`; states are exactly `queued|running|succeeded|failed|cancel_requested|cancelled`. Persist immutable source/output/profile/config hashes, attempt count, and bounded log refs. Document and enforce `running -> failed` with `CRASH_RECOVERY` and `running -> queued` only for an explicit bounded retry; only documented transitions are accepted.
- **Execution/API:** worker invokes `run_pipeline`; cancellation is checked only at file/stage boundaries. `jobs submit|status|cancel|retry` and localhost-only FastAPI endpoints validate concurrency/root overlap. Mutating loopback HTTP endpoints reject cross-origin browser requests and require a startup-generated restricted-file bearer token. Restart recovers active jobs; retry creates a new explicit attempt, never an infinite loop.
- **Tests/boundary:** state graph, cancellation boundary, recovery, retry, concurrent claim, duplicate prevention, localhost default. No Redis/Celery/cloud queue/MCP mutation.

#### Contract 4.5 — Signed, versioned event delivery

- **Owned files:** create `docs/schemas/event.schema.json`, `tests/test_webhook.py`, `tests/test_jsonlog.py`, and `tests/test_events.py`; edit `webhook.py`, `jsonlog.py`, `jobs.py`, and `cli.py`.
- **Envelope/delivery:** `{schema_version,event_id,event_type,occurred_at,run_id,job_id,status,data,warnings,errors}`; data has only IDs/counts/safe relative refs/citations. Persist local outbox first, then POST only allowlisted configured endpoints. If configured, HMAC covers canonical bytes; `tenacity` retry exhaustion creates a dead-letter record retained for at most 30 days or 1,000 records, pruned deterministically.
- **Errors:** replay requires `events replay EVENT_ID --endpoint NAME`. Delivery failure warns but does not change conversion success unless synchronous enforcement was explicitly requested. No source body, PII, keys, or absolute paths enter events.
- **Tests/boundary:** schema, payload redaction, signature, retry/dead-letter, disabled network, allowlist, idempotent replay, JSONL parity. No URL may be read from document metadata.

#### Contract 4.6 — Conflict-safe connector sync

- **Owned files:** create `src/headcleaner/connectors.py` and `tests/test_connector_sync.py`; edit `obsidian.py`, `notion.py`, `git_commit.py`, `sync.py`, `cli.py`, and `tests/test_notion_import.py`.
- **Ownership/plan:** `ConnectorSnapshot(external_id,remote_revision,generated_fields,user_fields,content_hash)` classifies fields `generated|user_owned|shared`. Dry-run emits ordered create/update/skip/conflict plan with hashes; apply requires its plan hash, re-fetches each remote revision/content hash immediately before mutation, and returns `SYNC_STALE_REMOTE` without mutation for any stale/user-owned conflict.
- **Command:** `connector sync NAME BUNDLE [--dry-run] [--apply] [--conflict fail|report]`; dry-run defaults. HTTP/Git interfaces are injected; Git commit occurs only after apply and only for generated paths. Redacted/suppressed content needs policy authorization.
- **Tests/boundary:** user-field preservation, generated update, shared conflict, stale plan, failed remote retry, idempotence, zero external calls in dry-run. Never delete remote content.

#### Contract 4.7 — Plugin manifest/conformance

- **Owned files:** create `src/headcleaner/plugin_contract.py`, `tests/plugin_conformance/`, and `tests/test_plugin_contract.py`; edit `plugins.py`, `router.py`, `doctor.py`, `docs/PLUGINS.md`, and `tests/test_plugins.py`.
- **Manifest/load:** `headcleaner-plugin.toml` requires `id,version,headcleaner_requires,adapters,extensions,required_tools,network_mode,settings_schema,element_kinds`. Validate it before entry-point import; old entry-point-only plugins are `legacy` with limited capability display. A failed plugin cannot remove/reorder core adapters.
- **Conformance:** check adapter output, element validation, diagnostics, safe failure, declared extensions, and declared no-network behavior. `plugins check PACKAGE_OR_PATH` reports each check and never installs a package.
- **Tests/boundary:** valid, legacy, malformed, incompatible, missing-tool, import failure, and network-declaration fixtures. Process sandboxing is not added in this task.

#### Contract 4.8 — Automation API v1

- **Owned files:** create `docs/schemas/event-v1.schema.json`, `docs/AUTOMATION_API.md`, and `tests/test_automation_contract.py`; edit `jsonlog.py`, `cli.py`, `webhook.py`, `mcp.py`, and `tests/test_jsonlog.py`.
- **Envelope/compatibility:** outbound events use the canonical `{schema_version,event_id,event_type,occurred_at,run_id,job_id,status,data,warnings,errors}` envelope; request/response correlation may add optional `request_id` and errors include `code,message,details`. `v1` is additive-only; field removal/rename/type change requires `v2`, parallel output selection, migration note, and contract update.
- **CLI/API:** JSON mode emits exactly one object/event per line with no ANSI/progress on stdout; diagnostics go stderr. HTTP and MCP use same semantics and retain citation/trust metadata.
- **Tests/boundary:** validate samples against schema, JSONL parseability, exit-code map, ANSI absence, compatibility snapshot, and docs examples. TUI/GUI DOM and internal dataclasses are not public API.

**Phase 4 verification:**

```bash
unset PYTHONPATH
uv sync --locked --python 3.13
uv run --no-sync --python 3.13 pytest tests/test_mcp.py tests/test_mcp_citations.py tests/test_context_pack.py tests/test_profiles.py tests/test_jobs.py tests/test_webhook.py tests/test_events.py tests/test_connector_sync.py tests/test_plugin_contract.py tests/test_automation_contract.py -q
```

---

## 4. Delivery discipline and release gates

### Per-task delivery loop

This protocol is mandatory for **every task and contract 1.1 through 4.8**. It is not a suggested project-wide convention: the task implementation record must retain the RTK, Graft, and context-mode outputs named below before implementation and review can pass.

**Coding-agent token-reduction requirement:** A coding agent implementing any task in this plan **must use RTK, Graft, and context-mode as its primary codebase-inspection workflow to reduce context/token consumption**. The agent must use the compact, targeted output from these tools before loading source into its model context. It must not substitute recursive tree scans, whole-file dumps, repeated generic searches, or speculative code reading when RTK/Graft/context-mode can answer the question with a smaller targeted result. This requirement applies during discovery, implementation, regression analysis, and review—not merely while writing the plan. A task is incomplete if the implementation record lacks the tool evidence required below.

**Required low-token order for every task:** (1) use RTK to locate only the named symbols and current diff/status; (2) use Graft to identify the smallest affected caller/dependency surface; (3) use context-mode to retrieve only the source/schema/test sections needed to implement the declared contract; (4) read a full file only if those targeted results show that its surrounding control flow is required. Re-index or rebuild only after a source change that makes the prior output stale. Do not re-run a broad inspection merely because a prior targeted result is already available in the task record.

1. **RTK discovery:** run `rtk git status --short`, `rtk grep` for the named symbols/files in that task's owned-file list, and `rtk diff` before and after the change. Use its compact results to avoid loading unrelated files; record the actual symbol locations and affected paths in the task/PR notes. Do not replace these with broad recursive searches or assume a symbol's shape from this plan.
2. **Graft dependency check:** run `graft --dir .hermes/graft build .` after source changes and `graft --dir .hermes/graft check .` before review. Use graph neighbors to reduce regression investigation to the edited public API/module’s actual callers, adapters, emitters, tests, and plugin seams. A graph-check failure blocks the task.
3. **context-mode grounding:** index the exact owned files and relevant schema/test files with `context-mode index ... --project . --source <task-id>`, then run `context-mode search` for the task's concrete data model/CLI/schema terms. Use the returned focused sections instead of whole-file context unless a specific control-flow dependency requires expansion. Save source locations in the task/PR notes. If context-mode conflicts with current source, current source wins and this master contract must be amended before code proceeds.
4. **Focused tests first:** create or amend every exact test file named by the task contract before implementation. Run the focused test and record the expected pre-implementation failure. Include one positive case, one validation/failure case, one deterministic/idempotence or ordering case where state/output exists, and one trust/privacy/no-network regression when the task crosses that boundary.
5. **Contract-complete implementation:** implement only the owned-file changes and explicit interface/data rules. Add an explicit contract amendment before adding a file, field, endpoint, state transition, dependency, or behavior the contract does not name.
6. **Comprehensive verification:** run the named focused tests, their existing caller/adapter/emitter regressions revealed by Graft, the phase command, schema validation, and `git diff --check`. For command/API/schema tasks, test help/error/JSON behavior and backwards compatibility; for stateful tasks, test restart/rollback/idempotence; for any network-capable seam, prove zero outbound calls without explicit configuration.
7. **Review evidence:** attach RTK locations/diff, Graft check result, context-mode query results, focused/phase test output, and a list of intentionally untouched files. A task cannot be marked complete with only a passing happy-path test.
8. Do not merge a task that changes a public schema without its schema/compatibility test and documentation update.

### Per-phase merge gate

```bash
unset PYTHONPATH
export PATH="/c/tmp/zsv-bin:$PATH"
uv sync --locked --python 3.13
uv run --no-sync --python 3.13 pytest -rs --no-header
uv run --no-sync --python 3.13 python -c "import pathlib, yaml; [yaml.safe_load(p.read_text()) for p in pathlib.Path('.github/workflows').glob('*.yml')]"
git diff --check
```

The phase-specific verification command above always uses the complete required locked environment. Do not broaden into a full Ruff cleanup; run only focused lint/format checks for newly created files when required by CI.

### Trust and privacy release gate

Before each release candidate:

- Golden corpus baseline has no unexplained regression.
- Schema validation passes for all new manifest/chunk/graph/redaction/readiness/event/attestation contracts.
- `human:pending` invariant is tested across conversion, review queue, readiness, MCP, and webhook paths.
- Any network-capable feature has a test proving no outbound request occurs without explicit user configuration.
- Public benchmark/report artifacts contain only attributed, approved fixtures.
- Required system-tool presence is tested at the environment gate; dedicated fault-injection tests verify actionable failure messages when a required tool is deliberately withheld.

### Program success criteria

This program is complete only when all 32 enhancement IDs are delivered and demonstrated as follows:

1. Conversion fidelity is measurable and regression-gated.
2. Every retrieval/context output has source-cited, trust-state-aware evidence.
3. A human can review and audit uncertain output efficiently without automation claiming review.
4. Sensitive/hostile content is discovered and controlled before it reaches an index, connector, or agent.
5. Outputs, indexes, vectors, graph data, and service state have clear canonical/rebuild boundaries.
6. MCP/API/events/connectors/plugins expose versioned, policy-bounded contracts.
7. The core CLI remains local-first with the complete required dependency set installed and without requiring remote-service configuration.

---

## 5. Files that must not be touched by this program

- `C:/Users/james/developer/headcleaner/` — separate, locked dashboard repository; it is never in scope.
- Git history, tags, releases, or published package versions — unless the user explicitly authorizes a release after a phase gate is green.
- Existing fixture attribution/license records — except to add correctly attributed new fixtures.
- Credential files, `.env` files, or real sensitive documents.

## 6. Research artifacts and audit trail

This master plan is traceable to the following retained evidence:

- `docs/100x-enhancements-plan.md` — original 32-item opportunity inventory.
- `research/100x-enhancements/consolidated.json` — raw GitHub candidate consolidation.
- `research/100x-enhancements/curated.json` and `verified_repos.jsonl` — verified mature references.
- `research/100x-enhancements/readme_*.md` — archived reference README evidence.
- `research/100x-enhancements/pypi-direct-dependencies.json` — live metadata for current direct requirement pins.
- `research/100x-enhancements/pypi-dependencies.json` — live metadata and explicit exclusions for enhancement dependencies.

No separate phase-plan documents are required or created by this plan.

---

## 7. Authoritative adversarial-review amendments

The following clauses supersede conflicting earlier wording. They are implementation requirements, not reviewer proposals. They preserve the required-only dependency policy and the mandatory RTK/Graft/context-mode token-reduction delivery loop.

### Program and Phase 1 amendments

1. **Task 0 environment and compatibility gate.** `docs/DEPENDENCIES.md`, Docker, CI, and doctor must pin/check `rtk==0.42.4`, `graft==0.8.2`, and `context-mode==1.1.14` as required coding-agent tooling; their absence blocks task delivery, not end-user conversion. Task 0 also edits `mcp.py`/MCP documentation to remove the obsolete `[mcp]`-extra install text, replaces every emitted historical version constant with `headcleaner.__version__`, and verifies Python 3.12/3.13 Windows and Linux installation. `libpff-python` is accepted only if that matrix installs it reproducibly; otherwise Task 0 must replace it with an exact-pinned cross-platform implementation before any phase begins. Required Sentence Transformers must not eagerly download a model: local model paths are explicit, CPU-only operation is supported, and missing local models fail with `EMBEDDING_MODEL_UNAVAILABLE`.
2. **Engine/render/model safety.** Engine attempts use isolated temporary workspaces, atomically promote only successful artifacts, and purge failed attempts before fallback. `EngineCapability` is adapter metadata with a backward-compatible default on the base adapter; it does not reorder the registry. Full-page perceptual hashes are forbidden as a Markdown/PDF fidelity threshold; image hashes compare extracted embedded images only, while structural/text anchors govern document verification. `Element.id` remains byte-provenance-bound, but `concept_id` is a stable bundle/path lineage key; changed sources stale review state rather than preserving approval, and unchanged anchored elements retain relationship keys across a revision. Tabular additions are additive and preserve legacy element serialization.
3. **Archive safety.** Header inventory may reject early, but archive/member limits are also enforced while streaming decompression. On any streamed-byte breach, abort, delete partial staging data, quarantine with a stable code, and continue unrelated siblings. Fixtures include forged-header expansion, exact limit, and partial-artifact cleanup cases.

### Phase 2 amendments

1. **Derived-data identity/privacy/lifecycle.** `chunks.jsonl` is the only chunk cache; rebuild either validates/reuses it or regenerates byte-identical output. When a policy selects redacted indexing, chunk/FTS/vector inputs are the redacted derivative and no suppressed value may enter chunks, FTS excerpts, vectors, MCP, or events. Canonical output remains unmodified. Index/vector rebuild and sync compute current chunk IDs, delete orphaned local/Qdrant vectors, and recompute vectors only for a configured provider. Tests cover deleted-source cleanup, redacted SSN absence from direct FTS query, and rebuild after cache deletion.
2. **Graph/dedupe/claims.** Graph status is exactly `explicit|unverified`; generated edges are `unverified`. Semantic dedupe is disabled unless `dedupe.semantic_enabled=true` or `--semantic` is supplied, and uses only a compatible already-populated provider cache. Claim extraction has a centrally configured per-document cap, emits `CLAIMS_TOO_MANY`, and never performs unbounded pairwise comparison. Tests cover both semantic switches, graph schema rejection of `suggested`, and bounded 5,000-claim input.

### Phase 3 amendments

1. **Policy and redaction containment.** `extends` accepts only installed pack IDs or normalized descendants of the active bundle's `.headcleaner/policies/`; absolute paths, `..`, symlinks escaping that root, and all URI schemes are rejected before any read/network action. A redaction policy explicitly selects the canonical or redacted index view; a `pii-safe` route requires the redacted view.
2. **Attestation and inspection.** `attest.py` must replace duplicate-last-leaf Merkle construction with RFC 9162 split-point tree construction consistently for root and inclusion proofs; `[A,B,C]` and `[A,B,C,C]` must have different roots. Inspection/attachments share streamed archive-limit enforcement and forged-metadata fixtures.

### Phase 4 amendments

1. **Local service and connector safety.** Mutating loopback HTTP endpoints reject cross-origin browser requests and require a startup-generated restricted-file bearer token; tests prove an attacker Origin/no-token POST changes no state. Connector `--apply` re-fetches every remote revision/content hash immediately before mutation and returns `SYNC_STALE_REMOTE` per conflicted item. Profile dry-run is a no-write conversion preview; connector dry-run is the default for bidirectional mutation and `--apply` is required. The service is a user-invoked local interface, never a dependency of core CLI conversion.
2. **Envelope/context alignment.** Event delivery is the canonical outbound envelope `{schema_version,event_id,event_type,occurred_at,run_id,job_id,status,data,warnings,errors}`. Automation API request correlation is an optional `request_id` field, not a replacement event identity. Context-pack schema includes `readiness_state` with `ready|pending|blocked`. Compatibility fixtures validate shared event fields, the 14 preserved plus five added MCP tools, and service-disabled CLI conversion.

### Required regression evidence

Each amendment's named behavior is added to its owning contract's exact test file(s), with positive, malicious/negative, deterministic/idempotence, schema/compatibility, and no-network cases where applicable. `git diff --check`, the phase command, Graft check, and the mandatory RTK/context-mode evidence remain merge gates.
