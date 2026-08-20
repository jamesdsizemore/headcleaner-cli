# Repository memory

This is durable project context for future contributors. It records stable facts and conventions, not secrets, personal data, or temporary task output.

## Stable conventions

- The required verification command is `unset PYTHONPATH && uv run --no-sync --python 3.13 pytest`.
- Use RTK for bounded Git/diff evidence, Graft for symbols and callers, and context-mode for contracts and documentation seams before edits and at final review.
- Auto-conversion is never human review. Keep the OKF trust defaults `status: unverified` and `verified: human:pending` unless a human performs the explicit review action.
- Historical documentation belongs under `docs/_archive/`; archive rather than delete it. JSON schemas under `docs/schemas/` are authoritative and test-dependent.
- UI palette: cyan for success, pink for active/warn/failure, purple for information, muted grey for skipped. Do not add red or yellow.
- Every phase and commit requires the active-document audit described in `docs/development/DOCUMENTATION_GOVERNANCE.md`.
