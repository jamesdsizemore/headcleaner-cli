# Codex adapter

Merge `assets/templates/instructions/AGENTS.md.fragment` into the repository root `AGENTS.md`. Codex discovers `AGENTS.md` from the project root down to the current working directory, so add narrower overrides only when necessary.

Run the bootstrapper to install the verifier and versioned Git hook. Codex instructions shape agent behavior; `.githooks/pre-commit` is the enforcement point for any ordinary Git commit.

Validate by running `codex exec -C <repo> "State the documentation governance completion gate without editing files."` and confirm it cites the project `AGENTS.md`, then run the repository verifier.
