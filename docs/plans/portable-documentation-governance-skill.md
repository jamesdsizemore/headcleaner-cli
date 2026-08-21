# Portable documentation-governance kit

**Status:** in progress  
**Scope:** a self-contained, project-agnostic agent skill/plugin kit. It is versioned in this repository only as a distributable artifact; it must not refer to HeadCleaner, its paths, commands, source, or policies.

## Acceptance checklist

- [x] Agent-neutral `SKILL.md` with clear triggers, workflow, stop conditions, and completion gates.
- [x] `assets/` contains reusable templates, audit format/schema, enforcement scripts, hook source, bootstrap script, and platform adapters.
- [x] Native integration instructions for Hermes, Claude Code, Codex, and AGY, distinguished from shared Git enforcement.
- [x] The core validator checks active Markdown paths, anchors, exhaustive audit coverage, required development records, and staged-commit evidence.
- [x] Bootstrap creates a usable repository setup without overwriting existing files by default.
- [x] Generic fixture tests exercise validator success/failure, audit template creation, bootstrap, and hook installation behavior.
- [x] AGY plugin metadata is validated with the installed `agy plugin validate` command; platform limitations are documented rather than guessed.
- [x] Kit lint/syntax checks pass and the distribution README includes installation, customization, rollback, and verification instructions.

## Design decisions

- The canonical enforcement is Git-native: an executable pre-commit hook invokes a Python standard-library verifier. Agent instructions reinforce the gate but cannot replace it.
- The verifier is configurable by CLI options and has no project-specific defaults beyond conventional names (`README.md`, `docs/`, `.plans/`).
- `AGENTS.md` is the shared instruction surface; `CLAUDE.md` is an additional Claude Code surface. Hermes and Codex both recognize the shared file according to their documented discovery conventions.
- AGY plugin packaging will be emitted only after its installed validator accepts the manifest; otherwise the kit will supply a validated instruction adapter and explicitly classify native plugin packaging as unsupported by available evidence.
- Bootstrap is additive by default. Existing repository files are never overwritten without an explicit `--overwrite` flag.

## Verification record — 2026-08-20

- `python agent-kits/documentation-governance/assets/tests/test_governance.py`: **4 passed**. The suite covers successful complete-audit validation, bad anchor/evidence rejection, bootstrap + a real temporary Git commit invoking the installed hook, and non-overwrite protection for existing `AGENTS.md`/`CLAUDE.md`.
- `agy plugin validate agent-kits/documentation-governance/assets/platforms/agy/plugin`: valid, with one discovered skill.
- `claude plugin validate agent-kits/documentation-governance/assets/platforms/claude/plugin`: valid.
- `python -m py_compile ...`, `git diff --check -- agent-kits/documentation-governance`, and the portability/skill/schema scan: passed.
