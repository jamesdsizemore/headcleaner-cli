# CLAUDE.md

## Repository discipline

- Work only inside this repository. Do not commit, push, merge, reset, or rewrite history unless the user explicitly asks.
- Preserve existing user work. Inspect Git status before edits; change only the requested scope.
- Use RTK for bounded Git/diff evidence, Graft for symbol/caller tracing, and context-mode for plans, contracts, and documentation seams before edits and at final review.
- The mandatory test command is `unset PYTHONPATH && uv run --no-sync --python 3.13 pytest`. Focused runs may append test paths or pytest flags.
- Never auto-claim human review of converted output. Preserve `status: unverified` and `verified: human:pending` defaults.

## Required development records

For every multi-step task, create or update a local plan under `.plans/` before implementation. `.plans/` is ignored and contains working context only.

Keep these tracked records current during development:

- `BACKLOG.md` — scoped work, acceptance evidence, documentation impact, and non-goals.
- `ISSUES.md` — real defects and recoveries; archive, do not delete.
- `MEMORY.md` — stable repository conventions only; never secrets or transient output.
- `DEVELOPMENT_HISTORY.md` — phase and commit evidence.
- `DEPENDENCIES.md` and `PINS.md` — dependency intent, compatibility pins, and lock verification.

## Non-negotiable documentation gate

“Docs updated” means the entire active documentation surface was considered: root `README.md` plus every Markdown page under `docs/`, excluding `docs/_archive/`.

For every phase:

1. Create an exhaustive audit with `uv run --no-sync --python 3.13 python scripts/verify_docs.py --write-audit-template <phase>`.
2. Update every pertinent page. For every remaining page, record `reviewed` or `not-applicable` with a concrete evidence statement in `docs/development/phase-audits/<phase>.json`.
3. Run `uv run --no-sync --python 3.13 python scripts/verify_docs.py --phase <phase>`.
4. Do not state that the phase is complete until the audit, links/anchors, focused tests, full suite, and final Git review pass.

For every commit:

1. Update and stage `DEVELOPMENT_HISTORY.md` and the active phase audit.
2. Install and retain the versioned hook with `sh scripts/install-git-hooks.sh`.
3. Let `.githooks/pre-commit` run `verify_docs.py --staged`; do not bypass it.

See `DEVELOPMENT.md` and `docs/development/DOCUMENTATION_GOVERNANCE.md` for the full workflow.
