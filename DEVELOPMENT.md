# Development workflow

This file is the entry point for implementation work in this repository. It makes documentation a delivery requirement rather than an afterthought.

## Required workflow

1. Create or update a local plan under `.plans/` before a multi-step change. Plans are intentionally ignored; they are working context, not delivery evidence.
2. Update the applicable root records: [BACKLOG.md](BACKLOG.md), [ISSUES.md](ISSUES.md), [MEMORY.md](MEMORY.md), [DEVELOPMENT_HISTORY.md](DEVELOPMENT_HISTORY.md), [DEPENDENCIES.md](DEPENDENCIES.md), and [PINS.md](PINS.md).
3. Audit **every active documentation page** for the current phase. Record one evidenced decision per page in `docs/development/phase-audits/<phase>.json`.
4. Run the required focused tests and `uv run --no-sync --python 3.13 python scripts/verify_docs.py --phase <phase>`.
5. Before every commit, update the current phase audit and `DEVELOPMENT_HISTORY.md`; the versioned pre-commit hook verifies both along with links and anchors.
6. A phase is not complete until its full documentation audit, functional verification, and final Git review pass.

See [documentation governance](docs/development/DOCUMENTATION_GOVERNANCE.md) for the audit schema and enforcement details.
