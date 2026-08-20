# Claude Code adapter

The included plugin directory is designed for `claude --plugin-dir <path>` and contains a skill that delegates enforcement to the repository verifier and Git hook.

1. Bootstrap the target repository.
2. Merge `assets/templates/instructions/CLAUDE.md.fragment` into the target root `CLAUDE.md` and the shared `AGENTS.md` fragment into `AGENTS.md`.
3. Run Claude with `--plugin-dir <kit>/assets/platforms/claude/plugin` or install it through your organization’s approved Claude plugin distribution process.
4. Verify the skill is discoverable in a fresh session and run `python scripts/verify_docs.py --phase <phase>`.

The plugin is an implementation guide; it does not supersede the Git hook.
