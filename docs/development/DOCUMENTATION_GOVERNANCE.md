# Documentation governance

Documentation is a required delivery surface for every implementation phase and every commit. A link-valid page is not automatically accurate; the audit records the human decision and its evidence for every active document.

## Active-document scope

The validator treats `README.md` and every Markdown file under `docs/` as active, excluding `docs/_archive/`. Archived pages retain history and are never rewritten merely to satisfy a current phase gate.

## Phase audit contract

Create `docs/development/phase-audits/<phase>.json` with this shape:

```json
{
  "phase": "phase-2",
  "status": "complete",
  "entries": [
    {
      "path": "docs/user-guide/everyday-workflow.md",
      "disposition": "updated",
      "evidence": "Added the new workflow and verified its CLI command."
    }
  ]
}
```

The audit must contain exactly one entry for every active document. Valid dispositions are `updated`, `reviewed`, and `not-applicable`; every one needs specific evidence. A phase cannot be called complete until this command succeeds:

```bash
uv run --no-sync --python 3.13 python scripts/verify_docs.py --phase phase-2
```

It validates local paths, Markdown fragments, duplicate heading suffixes, URL-encoded fragments, inline HTML ids, reference-style links, and simple HTML `href`/`src` targets.

## Commit gate

Install the versioned hook once per clone:

```bash
sh scripts/install-git-hooks.sh
```

Before every commit, update the active phase audit and [DEVELOPMENT_HISTORY.md](../../DEVELOPMENT_HISTORY.md). The pre-commit hook runs `verify_docs.py --staged`; it rejects a commit if any active-doc audit is incomplete, a local link/anchor fails, or either required record is absent from the staged set.

## Development-time routine

1. Make a local plan under `.plans/`.
2. Record scope and documentation impact in the root development records.
3. Implement with focused tests and the repository’s required verification command.
4. Audit all active docs; update affected pages and record evidenced `reviewed` or `not-applicable` decisions for the rest.
5. Run the phase gate and final Git checks before stating completion.

The instructions in [AGENTS.md](../../AGENTS.md) and [CLAUDE.md](../../CLAUDE.md) repeat this non-negotiable workflow for coding agents.
