# Development history

This is the append-only record of implemented work and its verification. Before every commit, add or update the current commit-audit entry and the current phase audit. Never record secrets.

## Phase 2 — complete (2026-08-20)

- **Scope:** cited/searchable knowledge derivatives, transactional hash-differential `index update`, repository-wide documentation governance, and warning remediation.
- **Documentation gate:** `docs/development/phase-audits/phase-2.json` covers all 77 active documents; `uv run --no-sync --python 3.13 python scripts/verify_docs.py --phase phase-2` passes.
- **Index evidence:** focused index/search regressions cover unchanged row preservation, changed/deleted chunk reconciliation, and in-place trust-state refresh.
- **Warning evidence:** clean-process MCP import and ASGI serve regressions pass with warning handling promoted to errors.
- **Final verification:**
  - `uv run --no-sync --python 3.13 pytest -W error`: 521 passed, 10 skipped.
  - Required baseline `uv run --no-sync --python 3.13 pytest`: 521 passed, 10 skipped.
  - Ruff check and format check: all 34 changed Python files passed.
  - `uv lock --check` and `git diff --check`: passed.
- **Portable-kit evidence:** governance-kit tests, Python compilation, and AGY/Claude plugin-manifest validation passed.
- **Publication:** `bed7648` (`feat(phase2): add cited knowledge workflows and governance`) was pushed to `origin/main`; local and remote SHA parity was verified.

## Commit audit template

- **Commit:** pending (record the SHA after commit)
- **Scope:**
- **Documentation impact:** updated / reviewed unchanged / not applicable, with audit evidence
- **Verification:**
- **Known limitations:**

## Phase 3 — in progress (2026-08-21)

### Contract 3.6 — Explainable risk-based review queues (complete)

- **Commit:** pending
- **Scope:**
  - `src/headcleaner/review_queue.py`: `QueueState` enum (`pending|claimed|decided|suppressed`), `FactorSpec`, `QueueItem`, `FACTOR_REGISTRY` (six allow-listed factor functions: `diagnostic_severity`, `ocr_fallback_state`, `sensitivity_findings`, `policy_errors`, `stale_state`, `age`), `register_factor`, `build_queue(bundle_root, *, pack_weights=None)`, `claim_item`, `decide_item`, `suppress_item`, `explain_item`. Ordering: `(-priority, source_sha256, concept_ref)` — fully deterministic.
  - CLI: `headcleaner review-queue BUNDLE [--pack ID] [--limit N] [--json]` and `headcleaner review-claim BUNDLE CONCEPT_REF --reviewer ID`. Claim audit sidecar at `<bundle>/.headcleaner/queue-audit.json`; persistent audit-aware claim race rejection (a second reviewer claiming an already-claimed item is refused).
  - Queue commands never mutate concept `verified:` frontmatter.
- **Documentation impact:** CLI reference update pending.
- **Verification:**
  - `tests/test_review_queue.py`: **17 passed** (data model, deterministic ordering, tie-break by source_sha256, factor allow-list, missing-evidence-→-zero, pack-weights override, claim idempotency per reviewer, claim race rejection, decide requires claimed, suppress requires reason, explain_item, no-trust-mutation).
  - CLI smoke: build queue, JSON output, claim by alice (exit 0), claim race by bob (exit 1, audit-aware), claim-by-same-reviewer idempotent (exit 0).
- **Known limitations:** Policy-pack-driven `queue_weights` TOML `[queue_weights]` table is reserved but the current `load_pack` parser does not surface it; pack-driven weights via the CLI take effect only when TOML exposes the field.
