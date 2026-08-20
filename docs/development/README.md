# Development records

This directory contains the tracked evidence for how the repository is developed. It complements the root records: [DEVELOPMENT.md](../../DEVELOPMENT.md), [BACKLOG.md](../../BACKLOG.md), [ISSUES.md](../../ISSUES.md), [MEMORY.md](../../MEMORY.md), [DEVELOPMENT_HISTORY.md](../../DEVELOPMENT_HISTORY.md), [DEPENDENCIES.md](../../DEPENDENCIES.md), and [PINS.md](../../PINS.md).

The active phase is stored in [ACTIVE_PHASE.md](ACTIVE_PHASE.md). The human-readable [documentation inventory](DOCUMENTATION_INVENTORY.md) groups the active surface by audience and owner. Each phase has an audit JSON file under `phase-audits/`; it names every active Markdown document and records an evidenced disposition. A completed audit is executable evidence only after `scripts/verify_docs.py --phase <phase>` passes.

Local plans belong in the ignored `.plans/` directory. They maintain working continuity but are not substitutes for these tracked delivery records.
