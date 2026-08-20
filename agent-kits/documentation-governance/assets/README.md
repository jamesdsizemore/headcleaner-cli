# Documentation governance assets

## Shared enforcement

`assets/scripts/verify_docs.py` is the portable gate. It has no third-party dependencies and accepts a repository root plus conventional paths. `assets/scripts/bootstrap.py` installs a copy into the target repository; it is additive by default.

## Templates

- `templates/records/` creates tracked facts and decision records.
- `templates/development/` defines policy, active-phase marker, and audit storage.
- `templates/instructions/` provides mergeable agent context—not a replacement for existing project rules.

## Audit format

Use `formats/phase-audit.schema.json` as the machine-readable contract and `formats/evidence-rubric.md` as the writing standard. A completed audit must have exactly one evidenced disposition for every active Markdown page.

## Platform adapters

Read the adapter before copying files. The shared Git hook is mandatory in all cases; agent adapters improve behavior during implementation but cannot enforce a normal `git commit` on their own.

## Rollback

Remove `core.hooksPath` with `git config --unset core.hooksPath` only if the repository is intentionally retiring the policy. Keep audits/history as records. To undo a bootstrap before adoption, remove only newly-created kit-managed files after reviewing `git status`; do not delete or overwrite pre-existing project files.
