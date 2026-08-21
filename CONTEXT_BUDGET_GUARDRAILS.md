# Context-budget guardrails

**Status:** remediation draft — uncommitted
**Owner:** repository delivery process
**Created:** 2026-08-21

## Why this exists

The Phase 3 review and documentation recovery consumed excessive agent context by loading full procedural skills, broad source dumps, and raw tool output. That degraded the quality of the actual contract audit: important source and documentation discrepancies were discovered late, and some audit claims were not grounded in the committed docs.

This document defines the repository-facing guardrails for future agent-assisted work. It is intentionally visible at the repository root so a reviewer can inspect it before accepting a phase or release.

## Non-negotiable rules

### 1. Load only the narrowest useful instruction

Do not load a full large skill, full transcript, full source tree, or entire plan when a bounded section answers the question.

- Prefer a specific linked reference over a full skill body.
- Prefer a named contract section over the entire master plan.
- Prefer a symbol, function, test, or line range over a full source file.
- Do not inject raw web pages, browser dumps, or terminal transcripts into the review context.

**Evidence requirement:** every source read must state the exact question it answers.

### 2. Run the token-saving tools as actual commands

**RTK, Graft, and context-mode are required executable tools/plugins/MCPs.** They are not a “bounded contract workflow,” not a disposition, and not proof that a contract is met. Their purpose is to reduce token use while obtaining the exact information needed for the current seam.

Run their actual commands before broad source exploration or an edit boundary:

1. **RTK command** — compact Git status/diff, exact grep/read anchor, or the repository's mandated test command.
2. **Graft command/plugin** — symbol, caller, callee, file, or wiring discovery. If its graph is unavailable, report that concrete tool limitation; do not pretend it supplied evidence.
3. **context-mode command/plugin** — targeted semantic retrieval over the already-discovered plan/source/test seam. If it is not indexed or unavailable, report that fact and use only targeted RTK/Graft plus the authoritative contract.

Use the commands because they keep exploration compact. The authoritative contract, source, tests, and staged diff remain the acceptance evidence.

### 3. Context is a release resource

Reserve context for the work that determines acceptance:

- authoritative contract language,
- implementation symbols,
- relevant tests,
- staged diff,
- final gate output,
- unresolved findings.

Do not spend it on repeated status summaries, duplicate full-suite runs, generic reassurance, or skill text that is not needed for the current seam.

### 4. Audit claims require mechanical evidence

An audit cannot claim `updated` merely because an entry says so.

For every documentation entry:

| Disposition | Required evidence |
|---|---|
| `updated` | Staged diff contains the file; staged file contains declared current-phase terms/anchors; audit names the contract and code/test evidence. |
| `reviewed` | Audit names an exact current-phase contract, symbol, CLI command, schema, or test and states why the existing doc remains correct. |
| `not-applicable` | Audit names the authoritative contract that excludes the doc and explains why no user/developer/maintainer impact exists. |

A generic verifier must validate these fields against **staged Git content**, not the arbitrary working tree.

### 5. Documentation is implementation work

When a contract adds a user-facing command, schema, artifact, safety boundary, dependency, or CI behavior, the relevant docs must be updated in the same scoped change.

Minimum documentation surfaces:

- CLI command → `docs/reference/cli-reference.md`
- schema → `docs/schemas/README.md`
- trust/safety behavior → `docs/safety/permissions.md`, `docs/safety/privacy-and-data-handling.md`, and/or `docs/safety/security-model.md`
- user workflow → relevant `docs/user-guide/` page
- CI artifact / workflow → `docs/integrations/ci-overview.md` and workflow file
- dependency → `DEPENDENCIES.md`, `PINS.md`, compatibility/developer docs
- phase status → `BACKLOG.md`, `ISSUES.md`, `DEVELOPMENT_HISTORY.md`, active phase audit

If a required doc is intentionally not changed, record that as `reviewed` with an exact explanation; do not call it `updated`.

### 6. No phase completion from tests alone

A green test suite proves exercised behavior did not regress. It does not prove the contract was delivered.

Before a phase is called complete, a contract ledger must show for each contract:

- authoritative requirement,
- implementation symbol/file,
- CLI/API evidence,
- positive and negative test evidence,
- safety/trust evidence,
- documentation evidence,
- status: `met`, `gap`, or `deferred`.

Any `gap` or unapproved `deferred` item blocks phase completion.

## Required final gate

Run the following against a clean, staged release candidate:

```bash
unset PYTHONPATH
uv run --no-sync --python 3.13 pytest

unset PYTHONPATH
uv run --no-sync --python 3.13 pytest -W error

uv run --no-sync --python 3.13 ruff check src tests
uv run --no-sync --python 3.13 ruff format --check src tests
uv lock --check
git diff --cached --check
```

The documentation verifier must consume staged paths/content and validate every audit disposition using the evidence rules above. It must not discover arbitrary untracked Markdown through `Path.rglob()` and mistake local research notes for release documentation.

## Phase 3 remediation implications

This document does not certify Phase 3. The published Phase 3 audit must be replaced only after:

1. the underlying product/contract gaps are fixed or explicitly accepted as deferred;
2. the root ledgers are reconciled with the actual commit and push state;
3. documentation claims are validated against real staged documentation changes;
4. the full test, lint, format, dependency, documentation, and Git gates pass.

## Reviewer checklist

Before accepting an agent-assisted commit, verify:

- [ ] No oversized skill/transcript/source dump was used where a bounded read sufficed.
- [ ] Every `updated` documentation entry has a staged diff and real current-phase content.
- [ ] Every `reviewed` entry names concrete code/test/contract evidence.
- [ ] Every advertised CLI command has an end-to-end CLI regression test.
- [ ] Every required CI artifact is generated and uploaded by the actual workflow, not merely documented.
- [ ] Root ledgers, active phase, audit, and Git history tell the same story.
- [ ] No uncommitted recovery work is being counted as delivered.
