# 100x Enhancements Plan

> A research-grounded roadmap for turning headcleaner from a high-quality folder-to-Markdown/OKF converter into a trusted document-intelligence, knowledge-ingestion, and agent-ready workflow.

**Status:** Proposed — no item in this document is implemented merely by being listed here.

**Research date:** 2026-08-17

## Executive summary

headcleaner already has a strong conversion core: format routing, parallel conversion, idempotent cache/resume behavior, Markdown and OKF emission, source hashes, policy evaluation, review/trust primitives, plugins, watch/serve/MCP modules, JSON output, and local-first operation. The largest step-change is not “add more file extensions.” It is to make every conversion **measurably faithful, reviewable, retrievable, governable, and reusable by both people and agents**.

This plan contains **32 enhancements**, prioritized into delivery horizons. The first horizon deliberately favors quality evidence and a durable content model before adding search, AI, hosted services, or broad integrations. That order protects headcleaner’s trust stance: conversion must never automatically claim human review.

## Research method and evidence

### Method

- Ran **10 live GitHub landscape searches** spanning document conversion, document intelligence, unstructured processing, RAG ingestion, OCR/layout, knowledge graphs, provenance, file workflows, personal knowledge search, and MCP document servers.
- Retained **56 raw results**, deduplicated to **56 unique repositories**.
- Individually validated metadata for **11 mature reference projects** and archived six upstream READMEs in `research/100x-enhancements/`.
- Research artifacts:
  - `research/100x-enhancements/raw_github_*.json`
  - `research/100x-enhancements/consolidated.json`
  - `research/100x-enhancements/bucketed.json`
  - `research/100x-enhancements/curated.json`
  - `research/100x-enhancements/verified_repos.jsonl`

> The Agent Reach Exa backend was not configured on this host during research, so the external corpus is GitHub/API-backed rather than falsely presented as a broader web crawl.

### Mature reference projects

| Reference | What it validates for headcleaner |
|---|---|
| [Docling](https://github.com/docling-project/docling) | Layout-aware document understanding, structured extraction, and a modular document-processing model. |
| [MarkItDown](https://github.com/microsoft/markitdown) | The market demand for reliable, broadly compatible conversion into LLM-ready Markdown. |
| [Marker](https://github.com/datalab-to/marker) | High-fidelity PDF-to-Markdown, table, math, and image-aware conversion quality as a competitive bar. |
| [Unstructured](https://github.com/Unstructured-IO/unstructured) | Partitioning documents into typed elements before downstream indexing or enrichment. |
| [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) | Layout-aware OCR, multilingual text recognition, and structured document extraction. |
| [OCRmyPDF](https://github.com/ocrmypdf/OCRmyPDF) | A robust preprocessing pattern: make scanned PDFs searchable before extraction. |
| [Apache Tika](https://github.com/apache/tika) | Broad-format parsing and metadata extraction as an optional compatibility backend. |
| [RAGFlow](https://github.com/infiniflow/ragflow) | Retrieval quality depends on document-aware chunking, citations, and ingestion quality—not merely a vector database. |
| [Qdrant](https://github.com/qdrant/qdrant) | A self-hostable, filterable vector index option for semantic retrieval. |
| [in-toto](https://github.com/in-toto/in-toto) | Signed, verifiable supply-chain/provenance attestations for high-trust output. |
| [Model Context Protocol servers](https://github.com/modelcontextprotocol/servers) | An interoperable pattern for exposing local tools and curated content to agents. |

**Interpretation:** These are design references, not automatic dependencies. Headcleaner should preserve its small, local-first CLI by putting heavier engines and semantic services behind explicit optional extras and capability discovery.

---

## Product principles

1. **Faithfulness before fluency.** A prettier Markdown file is not better if tables, citations, formulas, headings, or source meaning are lost.
2. **Evidence over claims.** Report extraction quality and confidence; never silently label an output reviewed or correct.
3. **Local-first by default.** Cloud OCR, embeddings, and LLM enrichment require explicit opt-in and a visible data-boundary notice.
4. **One canonical source of truth.** Preserve source hashes, paths, engine versions, extraction settings, and derivation history with every output.
5. **Optional capability layers.** Core conversion remains usable without GPU, credentials, a vector DB, or a network service.
6. **Human review is a first-class workflow.** Automation should queue high-risk documents for review rather than masking uncertainty.
7. **Portable knowledge.** Markdown/OKF remains the durable substrate; indexes, embeddings, and UI databases are rebuildable derivatives.

---

## Priority overview

| Horizon | Enhancements | Outcome |
|---|---:|---|
| H0 — Quality foundation | 1–8 | Measurable extraction fidelity and safe engine selection. |
| H1 — Knowledge-ready output | 9–16 | Searchable, linked, version-aware knowledge bundles. |
| H2 — Trust and review | 17–24 | Reviewable, policy-governed, provenance-rich output. |
| H3 — Agent and platform workflows | 25–32 | Useful at scale for agents, teams, and integrations. |

### Ranking rubric

- **Impact:** expected improvement to successful user outcomes.
- **Effort:** relative implementation and operational complexity.
- **Priority:** P0 is the next implementation batch; P1 follows after P0 proves its value; P2 is strategic/optional.

---

# H0 — Quality foundation

## 1. Conversion quality scorecard and golden corpus

**Priority:** P0 · **Impact:** Very high · **Effort:** Medium

Create a versioned fixture corpus covering every supported file type, including scanned PDFs, malformed Office files, multi-column documents, complex tables, image-heavy slides, multilingual documents, and real-world email/PST samples. Score output on text retention, heading hierarchy, table fidelity, link/citation retention, and source-hash/provenance correctness.

**Why it is 100x:** It turns “conversion seems good” into a release gate and prevents quality regressions as adapters evolve.

**Implementation boundary:** Create `tests/quality/`, fixture attribution records, a machine-readable `quality-baseline.json`, and a `headcleaner benchmark` command. Extend CI with a non-flaky baseline comparison.

**Research signal:** Marker, Docling, and Unstructured all make quality of structured extraction the product, not an incidental test case.

## 2. Per-document extraction diagnostics and confidence report

**Priority:** P0 · **Impact:** Very high · **Effort:** Medium

Emit a structured quality report for every output: engine used, fallback chain, detected language, OCR status, page/slide/sheet counts, missing-text indicators, table/image counts, warnings, and a calibrated confidence band. Include the report in `manifest.json` and expose it through JSON output.

**Why it is 100x:** Users can identify the 2% of documents that need attention instead of manually checking 100%.

**Implementation boundary:** Extend `FileResult` in `src/headcleaner/emit/manifest.py`, normalization in `src/headcleaner/normalize.py`, and report emission in `src/headcleaner/emit/report.py`. Add schema validation and fixtures for warning cases.

## 3. Adaptive engine cascade instead of extension-only routing

**Priority:** P0 · **Impact:** High · **Effort:** High

Retain the current extension router, but add a transparent decision layer that can choose a fallback based on document traits and prior failure signals. Example: native PDF text extraction → OCR preprocessing → layout-aware optional engine; OfficeCLI → LibreOffice normalization → alternate parser.

**Why it is 100x:** One bad engine path no longer determines a failed conversion.

**Implementation boundary:** Add an `EnginePlan`/capability model beside `src/headcleaner/router.py`; retain deterministic precedence, record every attempted engine, and require explicit `--allow-cloud` for any remote fallback.

## 4. Render-and-compare visual fidelity checks

**Priority:** P0 · **Impact:** High · **Effort:** High

Render source PDFs/Office documents and generated Markdown/HTML previews, then calculate a visual/structural difference score. Flag large divergences for review rather than attempting to auto-repair them.

**Why it is 100x:** It detects dropped columns, misplaced tables, invisible text, and order errors that text-only tests miss.

**Implementation boundary:** Add an optional `headcleaner verify-render` command and an isolated renderer interface. Store artifacts outside normal output by default; add a compact report path to the manifest.

## 5. Layout-aware document element model

**Priority:** P0 · **Impact:** Very high · **Effort:** High

Evolve the internal adapter result beyond one `body_md` string into typed, ordered elements—title, heading, paragraph, list, table, image, caption, equation, footnote, page break—with optional page coordinates and source spans. Markdown/OKF remains a rendering target, not the only internal representation.

**Why it is 100x:** Typed elements enable faithful tables, citations, search chunks, visual review, and reliable downstream exports.

**Implementation boundary:** Add `src/headcleaner/model.py`; evolve `CanonicalDoc` in `normalize.py` compatibly; update emitters to render elements; provide a compatibility adapter for existing plugins.

**Research signal:** Docling and Unstructured demonstrate the value of typed document partitions before indexing or enrichment.

## 6. First-class table, spreadsheet, and formula preservation

**Priority:** P0 · **Impact:** High · **Effort:** Medium

Capture tables as structured data alongside Markdown: CSV/JSON/HTML representations, sheet names, cell ranges, merged cells, formulas, number formats, and source coordinates. Keep a Markdown summary for readability while preserving the data needed for reliable reuse.

**Why it is 100x:** A converted financial model or dataset becomes analyzable rather than a lossy block of pipe characters.

**Implementation boundary:** Extend Office, CSV, and PDF adapters; add `attachments`/sidecar conventions to OKF emission; verify formula and merged-cell cases with the quality corpus.

## 7. OCR preprocessing profiles and multilingual language packs

**Priority:** P0 · **Impact:** High · **Effort:** Medium

Add named OCR profiles—`fast`, `balanced`, `archival`, `handwriting-experimental`—with deskew, rotation detection, binarization, language selection, and page-level retry behavior. Detect likely language/script before choosing installed OCR packs and report missing packs clearly.

**Why it is 100x:** Scanned and multilingual documents stop being a single `--ocr` best-effort toggle.

**Implementation boundary:** Expand `src/headcleaner/engines/pdf.py`, doctor checks, CLI config, and test fixtures. Keep PaddleOCR/cloud engines optional; Tesseract remains the baseline.

## 8. Safe archive, embedded-file, and attachment extraction

**Priority:** P0 · **Impact:** High · **Effort:** Medium

Support ZIP-like Office embedded objects, email attachments, archives, and document portfolios through a recursive extraction queue with depth, size, path-traversal, password, and malware-risk safeguards. Preserve parent-child provenance links.

**Why it is 100x:** Users can convert a real document package or mailbox without manually exploding files first.

**Implementation boundary:** Add `src/headcleaner/attachments.py`, recursive `RunOptions` controls, a quarantine directory convention, and policy limits. Default to metadata-only for password-protected content.

---

# H1 — Knowledge-ready output

## 9. Stable semantic chunks with source citations

**Priority:** P0 · **Impact:** Very high · **Effort:** High

Generate deterministic chunks from the typed element model, respecting headings, tables, code, and page boundaries. Each chunk receives a stable ID, source file hash, heading path, page/span references, token/word count, and Markdown citation target.

**Why it is 100x:** Converted output becomes reliable retrieval input and every answer can cite an exact source location.

**Implementation boundary:** Add `src/headcleaner/chunking.py`, emit optional `chunks.jsonl`, and define an OKF-compatible `resource`/citation extension. Test chunk stability across unchanged reruns.

## 10. Local hybrid search index

**Priority:** P0 · **Impact:** Very high · **Effort:** High

Build a local, rebuildable search index over emitted concepts and chunks. Start with BM25/full-text plus filters for path, tag, type, date, engine, review status, and source hash. Add vector search only as an opt-in backend.

**Why it is 100x:** A converted folder becomes a usable knowledge base rather than a directory of files.

**Implementation boundary:** Add `headcleaner search`, a SQLite FTS5 baseline, and an index metadata file that can be rebuilt entirely from Markdown/OKF.

**Research signal:** Qdrant and RAGFlow reinforce that retrieval needs document-aware chunking and filterable metadata, not embeddings alone.

## 11. Opt-in local and remote embedding providers

**Priority:** P1 · **Impact:** High · **Effort:** Medium

Provide pluggable embedding backends: local CPU/GPU model, OpenAI-compatible HTTP endpoint, and a user-supplied provider plugin. Cache vectors by chunk hash and model identity; keep source text local unless the user explicitly chooses a remote provider.

**Why it is 100x:** Semantic recall becomes available without forcing a cloud account or a single vendor.

**Implementation boundary:** Add `src/headcleaner/embeddings.py`, provider entry points, a cache table, and `--embedding-provider`/`--allow-network` controls.

## 12. Cross-document entity, topic, and relationship extraction

**Priority:** P1 · **Impact:** High · **Effort:** High

Extract candidate people, organizations, projects, dates, document references, and key terms into an explicit graph. Keep every edge linked to source chunks and mark machine-suggested edges as unverified until approved.

**Why it is 100x:** A folder becomes navigable by meaning and relationship, not just filename and full text.

**Implementation boundary:** Extend `src/headcleaner/crossref.py` with a structured graph store; emit `graph.jsonl`; add a local graph query command. Do not rewrite user text automatically.

## 13. Duplicate, near-duplicate, and version-family detection

**Priority:** P0 · **Impact:** High · **Effort:** Medium

Group exact duplicates by source hash and near duplicates by content fingerprint/semantic similarity. Identify likely version families even when filenames differ, then expose a canonical candidate without deleting any originals.

**Why it is 100x:** It eliminates repeated conversion/review work and reveals the latest authoritative document.

**Implementation boundary:** Add `src/headcleaner/dedupe.py`, manifest fields for family/canonical status, and a report command. Require confirmation before any deletion or move.

## 14. Meaningful document diffs and change summaries

**Priority:** P0 · **Impact:** High · **Effort:** Medium

Compare normalized elements/chunks rather than raw Markdown lines. Summarize changed sections, altered numbers/tables, added/removed claims, changed trust metadata, and source-version deltas.

**Why it is 100x:** Users can review a new contract, policy, or quarterly report in minutes rather than rereading it.

**Implementation boundary:** Add `headcleaner diff OLD NEW`, element-aware comparators, JSON output, and optional Markdown/HTML review reports.

## 15. Contradiction and stale-claim detection

**Priority:** P1 · **Impact:** High · **Effort:** High

Find potential conflicts among documents (dates, owners, amounts, policy requirements, product names) and stale assertions that exceed `stale_after`. Present evidence pairs and confidence—not a claim that the tool has determined the truth.

**Why it is 100x:** A knowledge bundle becomes actively maintainable instead of silently decaying.

**Implementation boundary:** Build on chunks, graph edges, and existing OKF lifecycle fields. Start with deterministic rules; make LLM-assisted comparison opt-in and evidence-backed.

## 16. Bidirectional source synchronization and rename tracking

**Priority:** P1 · **Impact:** Medium · **Effort:** High

Extend existing watch/cache behavior to track renamed/deleted sources, output ownership, and safe updates. Detect source movement through hashes, retain history, and avoid orphaned outputs or accidental deletion of user-authored Markdown edits.

**Why it is 100x:** Long-running document repositories remain clean without destructive resyncs.

**Implementation boundary:** Evolve `src/headcleaner/watch.py`, manifest identity records, and a `sync` command with preview mode and an explicit conflict policy.

---

# H2 — Trust and review

## 17. Interactive review workbench with evidence panes

**Priority:** P0 · **Impact:** Very high · **Effort:** High

Upgrade review from status management to a focused workflow: source preview, rendered output, extraction diagnostics, side-by-side diff, page/chunk jump links, reviewer notes, and an explicit approve/reject/escalate decision. Support keyboard-first TUI operation and a static HTML review packet for sharing.

**Why it is 100x:** It turns review from an external manual process into a fast, auditable part of conversion.

**Implementation boundary:** Extend `src/headcleaner/review.py`, `tui.py`, `viewer.py`, and report emission. Keep the current “never auto-claim review” invariant intact.

## 18. Policy packs and content-level governance

**Priority:** P0 · **Impact:** High · **Effort:** Medium

Expand existing trust policy support into named, versioned policy packs: `research`, `legal-hold`, `publication`, `PII-safe`, `RAG-ready`, and organization-specific rules. Validate not just frontmatter but quality thresholds, missing provenance, prohibited paths, age, unreviewed sensitive files, and required citations.

**Why it is 100x:** Teams get repeatable standards without reimplementing checks in shell scripts.

**Implementation boundary:** Evolve `src/headcleaner/policy.py`, ship sample TOML packs under `docs/policies/`, and add `headcleaner policy test` with clear findings and exit codes.

## 19. PII/secret detection, redaction proposals, and safe derivatives

**Priority:** P0 · **Impact:** Very high · **Effort:** High

Detect likely credentials, keys, government IDs, health identifiers, contact data, and configurable organization patterns before output leaves the machine. Generate a proposed-redaction report and a separate redacted derivative; never alter the original or silently redact canonical output.

**Why it is 100x:** Headcleaner becomes safe to use before indexing, sharing, or passing documents to an LLM.

**Implementation boundary:** Add `src/headcleaner/redact.py`, configurable detectors, an approval workflow, redaction provenance fields, and regression fixtures with synthetic secrets only.

## 20. Secure quarantine and hostile-file defense

**Priority:** P0 · **Impact:** High · **Effort:** Medium

Add archive-bomb limits, MIME/type mismatch detection, macro and embedded-object inventory, encrypted-file quarantine, antivirus hook integration, and policy-driven denial before optional engines execute content.

**Why it is 100x:** The converter becomes suitable for untrusted inboxes rather than only curated folders.

**Implementation boundary:** Add a pre-routing security stage, `headcleaner inspect`, structured warnings, and tests for path traversal/zip-bomb simulations.

## 21. Reproducible conversion attestations

**Priority:** P1 · **Impact:** High · **Effort:** Medium

Extend existing attestation support to capture source hash, normalized output hash, adapter/engine versions, configuration hash, optional binary checksums, timestamp, and operator identity. Offer optional signing and verification with no claim of human review.

**Why it is 100x:** A downstream consumer can reproduce or verify how an output was generated months later.

**Implementation boundary:** Evolve `src/headcleaner/attest.py`; support in-toto-style statement exports behind an optional dependency; add `headcleaner verify-attestation`.

**Research signal:** in-toto validates provenance as a chain of verifiable statements rather than an unverifiable text note.

## 22. Human review sampling and risk-based queues

**Priority:** P1 · **Impact:** High · **Effort:** Medium

Rank documents for review using quality diagnostics, source type, sensitive-data findings, OCR use, document age, policy failures, and random sampling. Generate review queues that optimize human attention while preserving an audit trail.

**Why it is 100x:** Review capacity is spent where it most improves trust.

**Implementation boundary:** Add `src/headcleaner/review_queue.py`, priority fields in the manifest, and reproducible sampling seeds.

## 23. Readiness grades for RAG and agent consumption

**Priority:** P1 · **Impact:** High · **Effort:** Medium

Publish a per-document readiness grade for retrieval/agent use: source citation coverage, chunk cohesion, table handling, OCR confidence, PII status, freshness, review state, and policy compliance. Explain every deduction with evidence.

**Why it is 100x:** Teams know which content is safe and useful to expose to assistants before deploying it.

**Implementation boundary:** Add a policy-derived `readiness` report, JSON output, and CI thresholds. Never label an item “safe” only because it converted successfully.

## 24. Public regression dashboard and benchmark transparency

**Priority:** P2 · **Impact:** Medium · **Effort:** Medium

Publish versioned conversion-quality results across the golden corpus, engine matrix, and platform configurations. Include known limitations and fixture provenance.

**Why it is 100x:** Quality claims become inspectable, and contributors can improve the highest-value failures rather than adding formats blindly.

**Implementation boundary:** Generate a static report from the benchmark suite; keep privacy-sensitive fixtures out of public artifacts.

---

# H3 — Agent and platform workflows

## 25. Citation-first MCP retrieval tools

**Priority:** P0 · **Impact:** Very high · **Effort:** High

Expand the existing MCP surface so agents can search concepts/chunks, fetch a cited passage, inspect provenance, list quality warnings, and request a review queue. Every retrieval result must contain a stable document/chunk ID, source path/hash, and citation target.

**Why it is 100x:** Agents can use the converted corpus without hallucinating what source material says.

**Implementation boundary:** Extend `src/headcleaner/mcp.py`; define strict JSON schemas; enforce local-root and policy boundaries; test against MCP clients without exposing arbitrary filesystem paths.

**Research signal:** MCP reference servers demonstrate a broad ecosystem pattern, while RAGFlow reinforces citation-centric retrieval.

## 26. Agent-ready context packages

**Priority:** P1 · **Impact:** High · **Effort:** Medium

Generate bounded context packs for a task: relevant chunks, source citations, glossary/entities, conflicts, freshness/review status, and a machine-readable manifest. Packs can be produced for a query, folder, policy, or named topic.

**Why it is 100x:** A model receives the smallest trustworthy context instead of an uncontrolled dump of documents.

**Implementation boundary:** Add `headcleaner context` and `src/headcleaner/context_pack.py`; provide Markdown and JSONL outputs; enforce byte/token budgets deterministically.

## 27. Configurable document classification and routing profiles

**Priority:** P1 · **Impact:** High · **Effort:** Medium

Add declarative profiles that classify documents by filename, metadata, text cues, or optional local/remote classifier. Profiles select conversion settings, OCR language, policy pack, chunking rule, output destination, and review priority.

**Why it is 100x:** A legal inbox, research archive, and product-support mailbox can share one tool without sharing one unsafe default.

**Implementation boundary:** Add `src/headcleaner/profiles.py`, TOML/YAML profile schema, `--profile`, doctor validation, and a `--dry-run` routing report.

## 28. Durable job queue and resumable service mode

**Priority:** P1 · **Impact:** High · **Effort:** High

Build on existing serve/watch capabilities with a durable SQLite-backed job queue: submit, cancel, retry, inspect logs, preserve artifacts, and resume after restart. Keep the CLI as the canonical worker protocol.

**Why it is 100x:** Headcleaner becomes reliable for many folders and continuous ingestion, not only one interactive command.

**Implementation boundary:** Evolve `src/headcleaner/serve.py` and `watch.py`; add migrations, job states, resource limits, and authenticated local-only defaults.

## 29. Webhooks and event-driven downstream workflows

**Priority:** P1 · **Impact:** Medium · **Effort:** Medium

Formalize existing webhook capability into signed events such as `conversion.completed`, `conversion.failed`, `review.required`, `policy.failed`, and `bundle.updated`. Include event schema versioning, retry/dead-letter behavior, and source-safe payloads.

**Why it is 100x:** Search indexes, issue trackers, storage systems, and agents can react immediately to trustworthy lifecycle events.

**Implementation boundary:** Evolve `src/headcleaner/webhook.py`, add event schemas/tests, and make delivery opt-in.

## 30. Native bidirectional connectors for Obsidian, Notion, and Git

**Priority:** P2 · **Impact:** High · **Effort:** High

Build on existing Obsidian, Notion, and Git integration modules with explicit import/export maps, field ownership rules, conflict reporting, deletion safety, and per-connector sync state.

**Why it is 100x:** Users can adopt headcleaner without abandoning the knowledge system they already use.

**Implementation boundary:** Evolve `obsidian.py`, `notion.py`, and `git_commit.py`; add connector fixtures/mocks and a preview-only sync default.

## 31. Plugin capability manifests, isolation, and compatibility tests

**Priority:** P1 · **Impact:** Medium · **Effort:** Medium

Extend the current entry-point adapter protocol with declared extensions, required binaries, network behavior, supported output features, settings schema, version compatibility, and optional isolated execution.

**Why it is 100x:** Third-party formats and engines become discoverable and safer without destabilizing core conversion.

**Implementation boundary:** Evolve `src/headcleaner/plugins.py` and `docs/PLUGINS.md`; add capability validation to `headcleaner doctor` and a plugin conformance test kit.

## 32. Stable automation API contract and client SDK examples

**Priority:** P1 · **Impact:** Medium · **Effort:** Medium

Promote existing `--json` output into a documented, schema-versioned event contract with stable exit codes, run IDs, pagination/streaming conventions, and examples for Python, shell, GitHub Actions, and MCP consumers.

**Why it is 100x:** Headcleaner becomes dependable infrastructure in pipelines instead of a CLI that other tools scrape.

**Implementation boundary:** Version `src/headcleaner/jsonlog.py` events, publish JSON Schemas in `docs/schemas/`, add compatibility tests, and document consumer migration rules.

---

# Recommended implementation sequence

## Release A — “Trustworthy conversion” (P0 foundation)

1. Quality corpus and scorecard (#1).
2. Extraction diagnostics (#2).
3. Typed document elements (#5).
4. Table/spreadsheet fidelity (#6).
5. OCR profiles (#7).
6. Safe embedded/attachment extraction (#8).

**Gate:** no semantic-search or agent feature lands until the quality corpus proves conversion has not regressed.

## Release B — “Knowledge-ready bundles”

1. Semantic chunks with citations (#9).
2. Local full-text/hybrid search baseline (#10).
3. Duplicate/version detection (#13).
4. Meaningful diffs (#14).
5. Policy packs and RAG readiness scoring (#18, #23).

**Gate:** every query result must map to a source hash and a stable citation.

## Release C — “Human-governed intelligence”

1. Review workbench and sampling queues (#17, #22).
2. PII/redaction and hostile-file safeguards (#19, #20).
3. Reproducible attestations (#21).
4. Classification profiles and synchronization (#27, #16).

**Gate:** no remote provider is enabled by default; policy and provenance remain visible in all outputs.

## Release D — “Agent and ecosystem platform”

1. Citation-first MCP tools and context packages (#25, #26).
2. Durable jobs/events (#28, #29).
3. Connector hardening and plugin manifests (#30, #31).
4. Stable automation contract (#32).
5. Embeddings, graph, contradiction detection, and transparent benchmark publication (#11, #12, #15, #24).

---

# Cross-cutting validation requirements

Every enhancement must include:

- Unit tests plus a golden-corpus integration fixture where extraction/output changes.
- `unset PYTHONPATH` before project tooling on the Windows Hermes host.
- `uv run pytest` green on the final tree.
- A schema/contract test for any manifest, event, policy, MCP, or plugin interface change.
- Clear optional-dependency behavior: missing OCR, vector, Office, cloud, or security engines must not break unrelated conversion.
- A privacy/data-boundary test for any network-capable feature.
- Trust-state tests proving auto-conversion never upgrades `verified: human:pending` to a reviewed status.
- Documentation that names limitations and fallback behavior, not only ideal outcomes.

# Success measures

The roadmap is successful when headcleaner can demonstrate all of the following:

1. Conversion quality is measured across a representative, attributed corpus at every release.
2. Every output has enough evidence to locate and verify its source.
3. A user can find an answer across a converted corpus and inspect cited passages locally.
4. Risky, low-confidence, stale, or sensitive content is automatically surfaced for review—not hidden.
5. A reviewer can approve a precise output with an audit trail without the tool ever claiming review by itself.
6. An agent can retrieve bounded, cited, policy-compliant context through a stable local interface.
7. Optional heavyweight capabilities expand the product without compromising the basic CLI’s portability or privacy.
