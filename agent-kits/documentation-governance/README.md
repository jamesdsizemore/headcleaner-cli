# Portable documentation-governance kit

A self-contained, project-neutral skill and enforcement kit for making documentation a required part of every development phase and every Git commit.

## What it installs

- A standard-library `verify_docs.py` that checks active Markdown links, heading anchors, complete phase-audit coverage, required development records, and staged-commit evidence.
- A versioned `.githooks/pre-commit` hook and installer; Git—not an LLM prompt—is the commit enforcement point.
- Root development records: backlog, issues, repository memory, development history, dependency register, and compatibility pins.
- A Git-ignored `.plans/` workspace, active-phase marker, exhaustive audit format, and documentation policy.
- Agent-specific adapters for Hermes, Claude Code, Codex, and AGY, all backed by the same Git enforcement core.

## Quick start

From a clone of this kit, run:

```bash
python agent-kits/documentation-governance/assets/scripts/bootstrap.py /path/to/repository --phase phase-1 --install-hook
```

If the target already has `AGENTS.md` or `CLAUDE.md`, the bootstrapper refuses to overwrite it. Review the fragments in `assets/templates/instructions/`, merge them manually, or explicitly add `--append-instructions`.

Then populate `docs/development/phase-audits/phase-1.json`, change its status to `complete`, and verify:

```bash
python scripts/verify_docs.py --phase phase-1
```

## Distribution layout

- `SKILL.md` — portable agent-skill instruction core.
- `assets/scripts/` — bootstrap, verifier, hook installer, and pre-commit source.
- `assets/templates/` — development-record, governance, and agent-instruction templates.
- `assets/formats/` — audit schema and evidence rubric.
- `assets/platforms/` — Hermes, Claude Code, Codex, and AGY installation adapters.
- `assets/tests/` — generic fixture tests; run before distributing changes.

See `assets/README.md` for installation, customization, rollback, and platform details.
