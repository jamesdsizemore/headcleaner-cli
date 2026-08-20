# AGY adapter

The `plugin/` directory includes the manifest required by AGY’s plugin validator. Validate it before installation:

```bash
agy plugin validate <kit>/assets/platforms/agy/plugin
```

If validation passes, import/install it with the installed AGY version’s plugin workflow, then retain the shared `AGENTS.md` fragment and `.githooks/pre-commit` setup in the target repository. AGY plugin behavior changes independently of Git; the Git hook is the non-bypassable local enforcement boundary.

If your AGY version rejects the adapter, do not force-install it. Keep the agent-neutral skill, `AGENTS.md`, `CLAUDE.md`, verifier, and hook, and record the validation output as a platform compatibility issue.
