# Documentation inventory

This page is the human-readable inventory for the active documentation surface. The machine-readable, exhaustive matrix is the current phase audit at [`phase-audits/phase-2.json`](phase-audits/phase-2.json); it carries one evidence-backed disposition for every individual page.

## Scope

The active surface is the root [`README.md`](../../README.md) plus Markdown under `docs/`. Historical material under `docs/_archive/` is retained for provenance and deliberately excluded from current-phase coverage.

## Current active families

| Family | Active pages | Primary audience / responsibility |
|---|---:|---|
| Root README | 1 | Product entry point and contributor navigation |
| Rewrite tracker | 1 | Historical rewrite scope and decisions |
| `developer/` | 18 | Contributors and implementation contracts |
| `development/` | 4 | Phase records, governance, inventory, and audit evidence |
| `diagrams/` | 1 | Diagram asset guidance |
| `getting-started/` | 3 | Installation and first-run onboarding |
| `integrations/` | 5 | MCP, serve, CI, and automation users |
| `maintainers/` | 13 | Support, compatibility, incident, and ADR records |
| `reference/` | 9 | Command, result, configuration, and API lookup |
| `safety/` | 4 | Trust, permissions, privacy, and security boundaries |
| `schemas/` | 1 | Authoritative test-dependent schema contracts |
| `tutorials/` | 8 | Guided user workflows |
| `user-guide/` | 9 | Task-oriented end-user documentation |
| **Total** | **77** | **Complete active Markdown surface** |

## Audit matrix rules

1. The active-phase audit must list every individual path in this inventory exactly once.
2. Each entry must use `updated`, `reviewed`, or `not-applicable` and include concrete evidence.
3. The validator owns the computed count and link/anchor checks; do not hand-edit a count to claim completion.
4. Before a commit, stage both the phase audit and [`DEVELOPMENT_HISTORY.md`](../../DEVELOPMENT_HISTORY.md); the versioned hook enforces that rule.

Run the source-of-truth check with:

```bash
unset PYTHONPATH && uv run --no-sync --python 3.13 python scripts/verify_docs.py --phase phase-2
```
