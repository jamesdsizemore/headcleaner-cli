# Phase 3 implementation handoff — 2026-08-20

## Authority and non-negotiables

- Repository: `C:\Users\james\developer\headcleaner-cli`
- Authoritative plan: `docs/_archive/legacy-docs/master-enhancement-development-plan.md`, Phase 3 contracts 3.1–3.8.
- Git isolation: begin by inspecting `main` / `origin/main` at baseline `a1d0cdf`, then create or reuse a dedicated Phase 3 branch in a separate Git worktree. Make every development edit in that dedicated worktree; never edit the `main` worktree. End with Git status/diff/log review of the dedicated worktree.
- Never alter unrelated untracked artifacts: `.hermes/desktop-attachments/DOCUMENTATION_BRIEF.md`, `.hermes/patch_convert_ocr_options.py`, `.hermes/patch_ocr_cli.py`, `.hermes/plans/2026-08-17_192859-release-implementation-plan.md`, or `.ignore`.
- Never modify sibling `C:\Users\james\developer\headcleaner`.
- Required full gates, after final edits:
  ```sh
  unset PYTHONPATH && uv run --no-sync --python 3.13 pytest
  unset PYTHONPATH && uv run --no-sync --python 3.13 pytest -W error
  ```
- Use strict TDD: one focused test must fail for the intended missing behavior before production code changes; then implement minimally and verify green.
- Start and end any work boundary with Git review. Use RTK, Graft, and context-mode commands throughout development as token-saving replacements for broader source/context reads. Preserve the human-review trust boundary: generated output stays `unverified` until an explicit human decision.

## Current pause boundary

- No running process; no commit/push occurred.
- `git diff --check` passed at pause.
- Last focused evidence:
  - `tests/test_attest.py`: **24 passed in 0.24s**.
  - `tests/test_inspect.py`: **4 passed in 0.10s**.
  - `tests/test_run.py`: **24 passed in 2.34s**.
- The full project gates have **not** been rerun since all final Contract 3.4/3.5 changes.
- `docs/development/ACTIVE_PHASE.md` still says `phase-2`; do not change it until a valid Phase 3 documentation-audit transition exists.

## Delivered Phase 3 work (uncommitted)

### Contract 3.1 — evidence workbench (implemented; final governance/integration pending)

- `src/headcleaner/review_workbench.py`: read-only review evidence packets and offline JSON/HTML rendering.
- `src/headcleaner/review.py`: legacy decisions retain reviewer/reason/audit metadata; it remains the sole mutable decision authority.
- CLI: `headcleaner review-workbench BUNDLE CONCEPT --format json|html`.
- Focused compatibility evidence retained earlier: **33 passed**.

### Contract 3.2 — versioned policy packs (implemented; final governance/integration pending)

- `src/headcleaner/policy_packs.py`: deterministic, local-only TOML packs, inheritance/validation, ordered results, safe registered conditions, and stable serialization.
- CLI: `headcleaner policy test BUNDLE --pack PACK [--json]`; `headcleaner policy explain --pack PACK --rule RULE`.
- Example packs: `docs/policies/{research,publication,pii-safe,rag-ready,legal-hold}.toml`.
- Docs: `docs/developer/configuration-development.md`.
- Focused evidence retained earlier: **20 passed**.

### Contract 3.3 — redaction derivatives (implemented; final integration/governance pending)

- `src/headcleaner/redact.py`: deterministic secret proposals, safe value digests only, auditable suppression, and opt-in `_redacted/` derivatives.
- CLI: `headcleaner redact BUNDLE [--write-derivative] [--json]`.
- Schema: `docs/schemas/redaction.schema.json`.
- Safety docs updated: `docs/safety/permissions.md`, `docs/safety/privacy-and-data-handling.md`.
- Guarantees: canonical concepts are never mutated; raw secret values are not persisted.

### Contract 3.4 — hostile-file inspection/quarantine (core implementation complete; final acceptance/governance pending)

- `src/headcleaner/inspect.py`: bounded inspection without extraction/execution.
  - Quarantines ZIP traversal, encryption, macro indicators, malformed archives, and recognized type mismatch.
  - Recognizes valid Office Open XML ZIP containers as their declared logical type after ZIP inventory, preventing `.docx/.xlsx/.pptx` false positives.
- `src/headcleaner/run.py`: inspection runs before adapter routing in **both** `_process_sequential` and `_process_parallel`.
- A conversion with inspected hostile input emits a skipped `INSPECTION_QUARANTINED` result and safe, atomic `<output>/quarantine.json`; the manifest records its path/count.
- CLI: `headcleaner inspect INPUT [--json]`, read-only; exit 1 for quarantine.
- Docs: `docs/reference/cli-reference.md`, `docs/safety/permissions.md`.
- Tests cover traversal, PDF-as-DOCX mismatch, encrypted ZIP flag, macro-name indicator, sequential/parallel pre-routing, and quarantine record.

### Contract 3.5 — attestations (partial; next active work)

- Existing RFC 9162 odd-leaf behavior was corrected earlier using split-point roots/proofs.
- `src/headcleaner/attest.py` now:
  - sources attestation version from `headcleaner.__version__` rather than stale `0.7.0`;
  - provides `canonical_json_bytes()` (sorted keys, UTF-8, compact JSON);
  - signs/verifies canonical bytes rather than whitespace-dependent JSON;
  - exposes `build_in_toto_statement(attestation, config=None, lock_path=None)` as a deterministic unsigned statement projection;
  - records `predicate.config_sha256` from explicit normalized config;
  - records `predicate.lock_sha256` from raw lock-file bytes without emitting the lock path;
  - emits no review/approval claim.
- `tests/test_attest.py` has **24 passing tests** at pause.

## Immediate next slice: Contract 3.5

Use a narrow RED→GREEN vertical slice for **source/output evidence sets** in the in-toto predicate. Do not invent source provenance: inspect existing OKF frontmatter/manifest contracts first, then choose a deterministic bundle-relative representation. Requirements from plan:

- predicate must ultimately include source/output SHA sets, engine capability/version records, explicit timestamp/schema version, and no absolute paths/hostnames/usernames;
- add `docs/schemas/attestation.schema.json` and `tests/test_attestation_schema.py`;
- add CLI `headcleaner attest BUNDLE [--key PATH] [--in-toto PATH] [--verify]` with no-write verification semantics;
- add `in-toto==3.1.0` only with concrete export/schema/CLI tests, regenerate `uv.lock`, and do not commit key material;
- test signed/unsigned, changed source/output/config/lock, schema failure, and version sourcing;
- do not state that content was human-reviewed.

## Later remaining contracts

- **3.6:** create explainable `review_queue.py`; evidence-only factors and deterministic ordering; no queue action may mutate trust state.
- **3.7:** create `readiness.py` and schema; grades must be evidence-based and never overwrite `verified`.
- **3.8:** render deterministic public-only benchmark dashboard with attribution validation; no network/private fixture exposure.
- **Final governance:** update all required development ledgers, complete phase audit for every active doc, then run normal + `-W error` full gates, use final RTK/Graft/context review, and finish with a Git boundary review.

## Known tool quirks/errors to avoid repeating

- `rtk read` is unavailable (`read` is not on PATH); use `read_file` for exact reads.
- Graft no-symbol lookup is not an implementation result; query an existing exact symbol after `graft build`/auto-refresh.
- A prior attempt to use `git diff --check --stdin` was invalid; use plain `git diff --check`.
- Terminal rendering may collapse successful output to `ok`; native piped pytest output or temporary JUnit counters provide exact count evidence.
- Keep plan artifacts in `docs/plans/`; no Desktop output.
