# Documentation Rewrite Tracker

**Authority:** User directive (2026-08-20) plus the documentation brief attached as `.hermes/desktop-attachments/DOCUMENTATION_BRIEF.md`. The brief was authored for a different product (Rush); this tracker adapts its *structure, audience split, and quality bar* to headcleaner-cli's actual surface (conversion pipeline, OKF bundles, chunks/indexes/embeddings/graph/claims/sync, MCP, FastAPI).

**Status (2026-08-20): Documentation rewrite complete; Phase 2 closure in progress.** The rewrite delivered the active documentation hierarchy and dark-themed SVG diagrams. Subsequent Phase 2 closure work added executable documentation governance and a warning remediation in source/tests, including an explicit test-only `httpx` dependency. The current authoritative completion evidence is [the Phase 2 audit](development/phase-audits/phase-2.json) plus [development history](../DEVELOPMENT_HISTORY.md), not the original draft checklist below.

**Goal:** Two rigorously separated audiences. *Beginner / non-technical reader* gets narrative, plain-English, tutorial-shaped pages with dark-themed SVG diagrams in the cyan/pink/purple palette. *Developer reader* gets contract-shaped, comprehensive, ASCII-diagrammed reference pages. No bullet-list-only docs anywhere; every list lives inside prose that explains what the list means.

**Diagram decision:** Do **not** install `cathrynlavery/diagram-design`. It is a Claude Code skills plugin, not a runtime dependency, and pulling it into headcleaner-cli's dependency surface would violate the locked-deps policy. Adopted its **editorial SVG standard** (self-contained HTML+SVG, dark variants, semantic-class CSS, sparse accent color) and produced diagrams with hand-written SVG in the same style.

---

## Original documentation-rewrite checklist (historical planning record)

The remaining unchecked items preserve the original planning text and are not the current Phase 2 acceptance ledger. The current inventory and executable audit are maintained under `docs/development/`.

## Stage 0 — Inventory and archive (do first, do not write any new content yet)

- [x] Inventory current `docs/` files and capture their first lines.
- [ ] Move current `docs/*.md` into `docs/_archive/legacy-docs/` (CHANGELOG, AGENTS, ARCHITECTURE, CONTRIBUTING, ENHANCEMENTS, FAQ, FORMAT_MATRIX, INSTALL, OKF_NOTES, OPERATIONS, PHASE2_BACKLOG, PLUGINS, PUBLISHING, REGISTRY, RESEARCH_*, SCHEMA, TROUBLESHOOTING, USAGE, USER_GUIDE, VIEWER, plus the schema JSONs and the master plan files).
- [ ] Add a top-level `docs/_archive/README.md` explaining the archive, what was archived, where the new docs live, and the link-back from new → archive for context.
- [ ] Leave one unarchived root README at `/README.md` (it gets rewritten in Stage 1).

---

## Stage 1 — Root and getting-started (entry points for both audiences)

These are the pages a brand-new visitor sees first. Build them in this order.

- [ ] Rewrite `/README.md` as product landing page: headline, value proposition, what headcleaner is/isn't, three-step quick start, "what this means" for the output, choose-your-next-step, ASCII of the conversion pipeline, documentation map by reader goal.
- [ ] Create `docs/getting-started/installation.md` — Windows / macOS / Linux, Python 3.12–3.13, `uv`, clone vs wheel, PATH verification, system-tool expectations.
- [ ] Create `docs/getting-started/first-run.md` — `convert ./inbox ./out`, reading the manifest, reading `_md/` vs `okf/`, reading REPORT.md, ASCII of output tree.
- [ ] Create `docs/getting-started/glossary.md` — OKF v0.2, FTS5, citation, trust family, schema version, `human:pending`, `stale_after`, chunk, embedding, sync state.

**Hero SVG diagrams for this stage:** dark-themed "what headcleaner does" (in → canonical → derivatives) using cyan/pink/purple. Use `archify` `architecture` type, color palette pinned to `theme.py` constants.

---

## Stage 2 — User guide (beginner/narrative layer)

Pages written for someone who has never heard of OKF or FTS5. Lead with outcomes. No internal jargon until introduced in their own glossary entry.

- [ ] `docs/user-guide/index.md` — friendly start-here table of contents with one-sentence summaries per page.
- [ ] `docs/user-guide/everyday-workflow.md` — before-PR / after-AI-session / "I just want clean markdown" walkthrough.
- [ ] `docs/user-guide/understanding-results.md` — `ok / warn / fail / error / skipped` with plain examples; emphasize that `skipped` ≠ broken.
- [ ] `docs/user-guide/checking-converted-output.md` — reading `_md/` vs `okf/`, `index.md`, `REPORT.md`, manifest fields.
- [ ] `docs/user-guide/citations-and-trust.md` — `human:pending`, `sources[]`, `sha256`, `stale_after`, why auto-conversion does not equal human review.
- [ ] `docs/user-guide/search-and-context.md` — `index rebuild`, `search`, when to use MCP, when to use the FastAPI serve.
- [ ] `docs/user-guide/working-with-ai-agents.md` — beginner framing of MCP, generic stdio template, useful prompts.
- [ ] `docs/user-guide/troubleshooting.md` — symptom → reason → exact fix.
- [ ] `docs/user-guide/faq.md`.

**Hero SVG diagrams for this stage:** dark-themed "what lives where in your output folder" (tree of `_md/` vs `okf/` vs `.headcleaner/`).

---

## Stage 3 — Tutorials (guided lessons, not command lists)

Each tutorial is a numbered lesson with: outcome, prerequisites, steps, exact commands, expected result, explanation, next step.

- [ ] `docs/tutorials/first-10-minutes.md`.
- [ ] `docs/tutorials/python-conversion.md` — DOCX/XLSX/PPTX with LibreOffice fallback.
- [ ] `docs/tutorials/pdf-and-ocr.md`.
- [ ] `docs/tutorials/email-and-attachments.md`.
- [ ] `docs/tutorials/local-search.md`.
- [ ] `docs/tutorials/ai-coding-assistant.md`.
- [ ] `docs/tutorials/ci-integration.md`.

---

## Stage 4 — Reference (lookup, not narrative)

For both audiences; cross-references explain when to read each page.

- [ ] `docs/reference/cli-reference.md` — every command, organized by user intent, with: purpose, when to use, basic form, useful options, what it checks, possible results, mutability, optional tools in plain language, related commands, "which command should I run?" decision tree.
- [ ] `docs/reference/result-reference.md` — `FileResult`, manifest, report fields; exit codes; status values; JSON consumption; the `skipped vs error vs fail vs warn` distinction through examples.
- [ ] `docs/reference/configuration-reference.md` — Policy TOML fields.
- [ ] `docs/reference/engine-directory.md` — one engine per page (DOCX/XLSX/PPTX/PDF/HTML/TXT/email/OCR), what it checks, who needs it, install commands, missing-experience, failure recovery.
- [ ] `docs/reference/mcp-tool-reference.md` — every tool, parameters, return shape, source for each MCP tool.
- [ ] `docs/reference/serve-api-reference.md` — FastAPI endpoints.
- [ ] `docs/reference/environment-variables.md` — `$USER`, `$USERNAME`, system-tool paths.
- [ ] `docs/reference/compatibility.md` — Python 3.12 vs 3.13, Windows CRLF, OS-specific notes.

---

## Stage 5 — Integrations

- [ ] `docs/integrations/mcp-overview.md`.
- [ ] `docs/integrations/mcp-client-setup.md` — generic stdio template (no client-specific claims unless verified).
- [ ] `docs/integrations/serve-overview.md`.
- [ ] `docs/integrations/ci-overview.md`.
- [ ] `docs/integrations/scripts-and-automation.md`.

---

## Stage 6 — Safety

- [ ] `docs/safety/safety-overview.md` — local-first, `human:pending` invariant, redacted derivative deferred to Phase 3.
- [ ] `docs/safety/permissions.md` — `--allow-network`, `--allow-fallback`, `--qdrant-endpoint`, `--recreate-qdrant-collection`, `--write-redacted`.
- [ ] `docs/safety/privacy-and-data-handling.md`.
- [ ] `docs/safety/security-model.md`.

---

## Stage 7 — Developer guide (comprehensive, ASCII diagrams, contract-shaped)

- [ ] `docs/developer/contributor-onboarding.md` — clone → `uv sync --locked --python 3.13` → first passing test on every platform; Windows PATH/Python troubleshooting.
- [ ] `docs/developer/architecture.md` — conversion pipeline, canonical output, derivative layer, ASCII of pipeline.
- [ ] `docs/developer/source-tree.md` — every package/module/test family/fixture/CI file documented.
- [ ] `docs/developer/canonical-model.md` — `CanonicalDoc`, `Element`, `Chunk`, `Graph`, `Claim`, `SyncRecord`, derived contracts.
- [ ] `docs/developer/tool-and-engine-development.md` — adding an adapter (worked example).
- [ ] `docs/developer/routing-and-fallback.md` — `EngineCapability`, `EnginePlan`.
- [ ] `docs/developer/configuration-development.md` — policy packs, `.headcleaner/policies/`.
- [ ] `docs/developer/chunking-and-indexing.md` — `chunking.py`, `index.py`, `search.py` contracts, atomic rebuild, integrity check, FTS5 schema.
- [ ] `docs/developer/embeddings-and-vectors.md` — `EmbeddingProvider`, `VectorCache` (chunk_id-keyed, versioned), `QdrantVectorStore` (compatibility inspection + remote orphan prune).
- [ ] `docs/developer/graph-development.md` — bounded node (`concept|chunk|entity|topic`) and edge (`contains|cites|mentions|related_to|duplicate_candidate|conflicts_candidate`) vocab enforced in `__post_init__`; evidence on every non-contains edge; claim-to-topic `related_to` linkage.
- [ ] `docs/developer/claims-and-policy.md` — `claims.py`, scope (`bundle|source`), suppression, `CLAIMS_TOO_MANY` cap, lifecycle dates.
- [ ] `docs/developer/sync-and-watch.md` — `SyncRecord`, `(relpath, sha)` key, atomic state, prune refuses modified output, watcher invokes dry-run planner.
- [ ] `docs/developer/mcp-development.md` — tool signatures, stdio rules, schema constraints, real-server tests.
- [ ] `docs/developer/serve-development.md` — FastAPI parity with `search()`.
- [ ] `docs/developer/testing-guide.md` — unit / contract / parser / routing / CLI / MCP stdio / packaging.
- [ ] `docs/developer/ci-and-packaging.md` — `uv sync --locked --python 3.13`, Windows CRLF, system-tool installation, doctor gate.
- [ ] `docs/developer/debugging-guide.md`.
- [ ] `docs/developer/coding-standards.md` — neon palette, no red/yellow, headcleaner brand mark, doc style for the two audiences.

---

## Stage 8 — Maintainers

- [ ] `docs/maintainers/support-runbook.md`.
- [ ] `docs/maintainers/incident-and-security.md`.
- [ ] `docs/maintainers/versioning-and-compatibility.md`.
- [ ] `docs/maintainers/documentation-style-guide.md` — user language vs developer language, terminology discipline, the "docs that must change for a new tool/engine/config field" rule.
- [ ] `docs/maintainers/adr/` — ADRs for: SQLite FTS5 as local baseline, OKF v0.2 as canonical, human:pending invariant, redacted derivative deferred to Phase 3, cyan/pink/purple palette, locked dependency policy.

---

## Voice discipline (every stage)

- Never lead user pages with internal terms: registry, adapter, routing layer, schema, subprocess boundary, canonical, derivative. Introduce them in the glossary first.
- Never use red or yellow anywhere. Cyan = ok/success, pink = active/warn, purple = info. Match `theme.py`.
- Every list lives inside prose that says what the list means. No bullet-only docs.
- Cross-link every guide; validate local Markdown links at the end of each stage.
- Diagrams: dark SVG (cyan/pink/purple) for user docs, ASCII for developer docs. Hero diagrams per stage.

---

## Per-stage verification gates

For each stage, before marking it done:

1. Focused Markdown link check on the new files.
2. Cross-reference check against existing source (no invented features, no Phase 3/4 scope creep).
3. `git diff --check` clean.
4. Ruff clean on any modified `.py` (this task shouldn't touch `.py` files, but verify).
5. Full test suite still green (`unset PYTHONPATH && uv run --no-sync --python 3.13 pytest -rs --no-header`) — docs must never break the build.
6. The user-facing tests in `tests/test_walk.py` and similar do not regress.

---

## Out of scope (do not touch)

- Source code under `src/headcleaner/`.
- Tests under `tests/`.
- CI workflows under `.github/workflows/`.
- The Phase 2 ledger (`docs/PHASE2_BACKLOG.md` will move to `_archive/`; not deleted).
- The locked dependency set in `pyproject.toml` and `uv.lock` (no new deps).
- The `headcleaner` Next.js dashboard repo under `~/developer/headcleaner/`.

---

## Decision log

- 2026-08-20: Rejected `cathrynlavery/diagram-design` as a runtime dependency. Adopted its editorial-SVG standard and used `archify` instead. Reasoning: the repo is a Claude Code skills plugin, not a library, and adding it would violate the headcleaner-cli locked-deps policy. The visual standard is achievable with the existing `archify` skill plus hand-written SVG.
- 2026-08-20: Phase 2 ledger was archived, not deleted. Its `docs/PHASE2_BACKLOG.md` verification record at the bottom of the file is the authoritative acceptance evidence and must remain intact.