# Hermes adapter

Install the kit’s `SKILL.md` and `assets/` directory together under `$HERMES_HOME/skills/documentation-governance/` (or the active profile’s `skills/` directory). Start a new Hermes session after installation so discovery refreshes.

Merge `assets/templates/instructions/AGENTS.md.fragment` into the target repository’s root `AGENTS.md`. Hermes reads the root-cwd `AGENTS.md` as portable project context; `.hermes.md` may supplement it for Hermes-only inherited rules.

The Git hook remains the required enforcement mechanism. Do not rely on a skill prompt to enforce commits.
