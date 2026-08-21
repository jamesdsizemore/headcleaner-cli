# Phase 2 documentation-governance delivery plan

**Status:** in progress  
**Scope:** Build an enforceable documentation gate before closing the current Phase 2 work. No commit, merge, or push is authorized.

## Goal

Every development phase and every commit must carry a complete, explicit documentation-impact audit. The audit covers every active Markdown document—not just the file being edited—and records whether each document was updated, reviewed unchanged, or is not applicable with a concrete reason. The gate must also validate local Markdown links and heading fragments.

## Delivery stages

1. **Design and inventory** — Define active-doc scope, audit record schema, root development records, and commit gate. **Status:** complete.
2. **RED validator tests** — Add focused tests for complete/incomplete audit records, local targets, and heading anchors. **Status:** complete (three tests green).
3. **Implementation and hooks** — Create `scripts/verify_docs.py`, versioned `.githooks/pre-commit`, hook installer, and active-phase record. **Status:** in progress.
4. **Development records** — Create and populate `BACKLOG.md`, `ISSUES.md`, `MEMORY.md`, `DEVELOPMENT_HISTORY.md`, `DEPENDENCIES.md`, and `PINS.md`. **Status:** pending.
5. **Instructions and audit** — Update `AGENTS.md`, create `CLAUDE.md`, create the documentation-governance pages, and complete the current Phase 2 documentation audit. **Status:** pending.
6. **Verification** — Run focused governance tests, hook validation, active-doc validator, required index tests/Ruff, full suite, and compact RTK/Graft/context-mode review. **Status:** pending.

## Enforcement contract

- Active docs are `README.md` plus every Markdown file under `docs/`, excluding `docs/_archive/`.
- Every phase has a tracked JSON audit under `docs/development/phase-audits/` with one decision/evidence record per active document.
- A phase can be marked complete only when the audit exactly matches the active-doc inventory, has no pending entries, and passes link/anchor validation.
- A staged implementation commit must stage an update to the current phase audit and `DEVELOPMENT_HISTORY.md`; the versioned pre-commit hook invokes the same validator.
- Local plans live under `.plans/`, are intentionally ignored, and are referenced by `AGENTS.md`/`CLAUDE.md`; they are not proof of delivery.

## Non-goals

- No automatic claim that a document is accurate merely because a link resolves.
- No rewriting of archived historical documentation.
- No commits, pushes, merges, dependency changes, or unrelated source cleanup.

## Errors encountered

| Event | Resolution |
|---|---|
| `rtk read` resolves to a missing shell command on this host. | Use RTK Git/diff evidence, Graft symbols/callers, and context-mode contracts; use bounded native reads only where RTK's wrapper is unavailable. |
| Initial Markdown anchor checker was run through a generic shell wrapper. | Replaced it with a direct, deterministic Python validation pass; it found and the work repaired four owned active-doc failures. |
| Initial validator RED run had a fixture `FileExistsError`. | Made the test helper's audit-directory creation idempotent; the remaining failures now represent the absent validator only. |

## Next step

Create the tracked development records and hook assets, then generate and complete the current phase audit.
