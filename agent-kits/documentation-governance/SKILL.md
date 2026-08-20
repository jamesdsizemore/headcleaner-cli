---
name: documentation-governance
description: Use when establishing or enforcing exhaustive docs gates. Creates portable documentation governance with auditable phase and commit enforcement.
version: 1.0.0
author: Project-agnostic distribution
license: MIT
metadata:
  hermes:
    tags: [documentation, governance, git-hooks, audits, multi-agent]
    related_skills: []
---

# Documentation governance

## When to use

- A repository needs documentation to be a verifiable deliverable, not a promise.
- You are starting or closing an implementation phase, preparing a commit, or repairing documentation drift.
- You need the same policy to work for Hermes, Claude Code, Codex, and AGY.

Do not use this as permission to generate boilerplate edits. The audit records an evidence-backed decision for every active document: `updated`, `reviewed`, or `not-applicable`.

## Delivery workflow

1. **Discover before edits.** Identify the repository root, test/lint commands, docs roots, archive/research exclusions, existing agent instructions, and Git hooks. Create a local ignored plan first. Completion: scope and non-goals are recorded.
2. **Bootstrap safely.** Run `python <kit>/assets/scripts/bootstrap.py <repo> --phase <phase>`. If instructions already exist, inspect and merge deliberately or use `--append-instructions`; never overwrite repository guidance silently. Completion: root records, hook source, verifier, and an `in_progress` audit exist.
3. **Audit every active page.** Run `python scripts/verify_docs.py --write-audit-template <phase>` only if no audit exists. For every `README.md`/`docs/**/*.md` page, record a concrete disposition and evidence. Treat archives separately; do not falsify history to make the audit green. Completion: each active page has exactly one supported decision.
4. **Implement and document together.** Update the pertinent product, user, developer, operational, API/configuration, safety, troubleshooting, test, and decision records. Maintain backlog/issues/memory/history/dependencies/pins as facts change. Completion: no pertinent family is omitted without evidence.
5. **Verify phase completion.** Run `python scripts/verify_docs.py --phase <phase>` plus the repository’s focused and full checks. Do not claim completion on a partial audit, a broken anchor, or unverified test output. Completion: all gates are real and retained.
6. **Commit gate.** Install `.githooks/pre-commit` via `sh scripts/install-git-hooks.sh`. Before every commit stage the active audit and `DEVELOPMENT_HISTORY.md`; the hook validates staged evidence. Do not bypass it. Completion: `git config --get core.hooksPath` returns `.githooks` and the hook passes.

## Evidence quality

`updated` evidence names the behavior/contract changed and the verification. `reviewed` evidence states why the page remains accurate. `not-applicable` evidence states why the change cannot affect that page. “No change” alone is not evidence.

## Platform adapters

- **Hermes:** install this folder as a skill under `$HERMES_HOME/skills/documentation-governance/`; use the shared `AGENTS.md` fragment because Hermes reads it from the working directory.
- **Claude Code:** install the Claude plugin adapter or copy the `CLAUDE.md` fragment and `skills/documentation-governance/`. Project hooks remain the enforcement authority.
- **Codex:** copy/merge the shared `AGENTS.md` fragment. Codex discovers `AGENTS.md` from the project root to the current working directory.
- **AGY:** import/validate the included adapter only with the supplied install guide; retain `AGENTS.md` and Git hook enforcement even where agent plugin behavior varies by installed version.

## Non-negotiable boundaries

- Git hooks enforce commits; an agent instruction alone does not.
- Never overwrite an existing instruction, policy, history, or audit without explicit replacement intent.
- Do not include secrets in development records or audit evidence.
- Do not declare a phase complete while its audit remains `in_progress`.

## Verification checklist

- [ ] `python scripts/verify_docs.py --phase <phase>` reports all active docs and a complete audit.
- [ ] `git config --get core.hooksPath` is `.githooks`.
- [ ] A staged dry-run passes `python scripts/verify_docs.py --staged`.
- [ ] Root development records exist and current phase evidence is appended to history.
- [ ] Agent instructions have the documentation governance section, not a stale duplicate.
