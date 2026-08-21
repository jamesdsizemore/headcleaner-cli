# Phase 3 — Human-governed safety, review, and provenance

**Status:** alignment audit in progress  
**Authority:** `docs/_archive/legacy-docs/master-enhancement-development-plan.md`, Phase 3 contracts 3.1–3.8  
**Goal:** Deliver every Phase 3 contract through TDD, preserving the Phase 2 trust boundary: generated content remains `unverified` until an explicit, evidenced human decision.

## Git boundary and protected paths

- Start commit: `a1d0cdf` on `main`, synchronized with `origin/main`.
- Start worktree: no tracked changes; preserve untracked `.hermes/desktop-attachments/DOCUMENTATION_BRIEF.md`, `.hermes/patch_convert_ocr_options.py`, `.hermes/patch_ocr_cli.py`, `.hermes/plans/2026-08-17_192859-release-implementation-plan.md`, and `.ignore`.
- Do not stage or alter protected paths.
- No commit, merge, or push has been authorized for Phase 3.

## Contract ledger

| Contract | Scope | Status | Alignment / acceptance evidence |
|---|---|---|---|
| 3.1 | Evidence-first review workbench | audited | `review.py` currently mutates only frontmatter via `approve`/`reject`; `cli.review` is the public entry and `build_report` is additive. Implement a backward-compatible `review_audit` append record and a projection-only `ReviewPacket`; never let browse/render paths mutate trust state. |
| 3.2 | Versioned policy packs | audited | Existing `Policy`/`PolicyFinding` drive conversion, attachments, graph, claims, and MCP. Add a pack adapter without breaking legacy fields or finding shape. |
| 3.3 | Proposed redaction derivatives | audited | Phase 2 has cited chunks/indexes but no redacted view. Create derivative-only output and select its index view explicitly; do not expose raw match text. |
| 3.4 | Hostile input inspection/quarantine | audited | Existing bounded attachment quarantine runs inside the pipeline. Add a top-level inspection gate before routing/OCR and delegate archive-member safeguards to the existing implementation. |
| 3.5 | Reproducible attestations | in progress | Existing attestation claims RFC 9162 but duplicated odd leaves. RFC 9162 split-point roots/proofs are now TDD-corrected; schema, metadata, and optional in-toto output remain. |
| 3.6 | Explainable review queues | pending | Base inputs exclusively on evidenced diagnostics, policy, freshness, OCR/fallback, and redaction state. |
| 3.7 | Evidence-based readiness | pending | Consume Phase 2/3 evidence without mutating `verified`. |
| 3.8 | Public benchmark transparency | audited | Existing baseline/runner are present, but public-fixture attribution and dashboard artifact are absent. Use active contributor docs rather than stale legacy paths. |

## TDD record

Each behavior slice must record:

1. Exact test written first and expected RED failure.
2. Minimal production implementation and GREEN result.
3. Focused regression, relevant caller integration, and documentation update.

Required test launcher:

```sh
unset PYTHONPATH && uv run --no-sync --python 3.13 pytest <target>
```

## Compact discovery record

- Opening Git/RTK review: `main` at `a1d0cdf`, upstream `origin/main`, tracked diff clean.
- Graft map: 138 files, 1,280 symbols, 3,270 edges; `run_pipeline`, `build_report`, `rebuild_index`, and `build_attestation` are established hubs/seams.
- context-mode: indexed the Phase 3 source contract under `phase-3-alignment`; retrieved the Phase 3 purpose, exit gate, and Contract 3.8 public-artifact boundary.
- RTK recovery: an initial directory-form `rtk grep` delegated to native grep and did not search directories. Recovered by reading `rtk grep --help`; future searches use file glob/path arguments or `rtk rg` after its help is checked.

## Errors / recovery

| Event | Recovery |
|---|---|
| `rtk grep <pattern> src/headcleaner tests` rejected directory arguments through native grep. | Read `rtk grep --help`; use file glob/path arguments or `rtk rg` for recursive source discovery. No command is repeated unchanged. |
| `rtk diff src/headcleaner/attest.py tests/test_attest.py` compared file inputs rather than providing a bounded Git review and exited non-zero. | Use `rtk git diff --stat` plus native `git diff -- <paths>` for scoped worktree review; do not reuse the wrong two-file form. |
| Three independent Phase 3 audit workers exhausted retries on a model API connection failure and returned no repository findings. | Do not retry the same unavailable delegation. Complete the alignment audit directly with RTK/Graft/context-mode and bounded source/test reads; record this reviewer limitation in the final Phase 3 review. |

## Alignment findings

### Contract 3.1 — review workbench

- Current authority is `src/headcleaner/review.py`: `approve` and `reject` change frontmatter directly and are invoked only by its Textual/REPL paths. Existing tests assert only the legacy field flips.
- There is no structured decision/audit-evidence model. The plan's claim that an existing review-state model can preserve evidence is incomplete; Phase 3 must add an append-only `review_audit` record while retaining all legacy fields and call shapes.
- `src/headcleaner/emit/report.py:build_report` is already derivative-oriented and its callers treat optional sections additively. A review packet/report summary can follow that optional-argument pattern without changing conversion output.
- `viewer.py` is a separate static HTML renderer, not the review authority. Workbench static HTML/JSON must be an offline projection, and opening it must never call approval/rejection.

### Contract 3.2 — policy packs

- `Policy` is a legacy trust-policy data model shared by conversion, attachments, claims, graph filtering, and MCP. Its current finding type is `PolicyFinding(file, severity, rule, message)`, so the plan's new `rule_id`/`concept_ref` fields require an additive pack-finding adapter rather than a breaking rename.
- Existing conversion supports a user-supplied policy path and evaluates it after conversion. Pack resolution must be a separate safe resolver that retains legacy file-policy behavior, prohibits traversal/URI/escaping symlink input before any read, and cannot imply human review.

### Contracts 3.3–3.4 — redaction and inspection

- Phase 2 created cited chunks/indexes and explicitly deferred redacted indexing. No redaction module or index-view selector exists. Redaction must therefore be a derivative pipeline with explicit view selection; it cannot retrofit or mutate canonical concepts, chunks, manifests, or source files.
- The existing attachment layer already enforces bounded member streaming and records quarantine diagnostics. A new top-level inspector must run before router/adapter/OCR selection, then reuse—not bypass or duplicate—the existing archive-member safety controls.
- `run_pipeline` has many callers (CLI, TUI, watch, benchmark, and focused tests). Inspection must be represented as an explicit defaulted option/result so existing callers remain compatible and rejected files cannot invoke adapters.

### Contract 3.5 — attestations

- `attest.py` described an RFC 9162 tree while its implementation and regression used duplicate-last-leaf padding. This directly contradicted the Phase 3 amendment.
- **TDD slice:** changed the odd-count test first; the required Python 3.13 command failed because three leaves and duplicate-last leaves produced the same root. Replaced root/proof/proof-validation padding with shared RFC 9162 split-point helpers. `tests/test_attest.py` then passed (18 tests), and Graft rebuilt/checked the changed wiring graph successfully.
- Remaining contract work is intentionally open: version/config/engine/lock provenance, attestation JSON Schema, canonical signed predicate, optional in-toto emission, CLI compatibility, and their focused tests.

### Contracts 3.6–3.8 — queues, readiness, and transparency

- `review_queue.py` and `readiness.py` do not exist; their initial data models must be additive derivatives over existing diagnostics, review state, chunk/manifest evidence, policy findings, and redaction proposals. Neither command may change `verified`.
- The current benchmark runner and `tests/quality/baseline.json` exist, but `tests/quality/ATTRIBUTION.md`, the dashboard renderer, dashboard tests, and `docs/QUALITY.md` do not. Public-only input validation and deterministic output are therefore new requirements, not a rename of existing benchmark behavior.
- The Phase 3 plan names obsolete/missing `docs/SCHEMA.md` and `docs/CONTRIBUTING.md`; the active contributor surface is `docs/developer/contributor-onboarding.md`. Documentation updates must use active paths and the repository's phase audit rather than recreate legacy paths.
- `pyproject.toml` does not pin the plan-required `in-toto==3.1.0`. Add it only with its schema/CLI tests and regenerate `uv.lock`; restore the required Python 3.13 environment before accepting verification evidence.

## Next step

Implement Contract 3.1 with a test-first, additive review packet and explicit audited decision API. Preserve existing `headcleaner review` behavior while adding offline static rendering and evidence-required decisions; then integrate the compatible Contract 3.2 pack evaluator.
