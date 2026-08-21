# 0004 — Locked dependency policy with exact pins

**Status:** Accepted
**Date:** 2026-08-20
**Context:** Reproducible installs require locked dependencies. Different `pip` resolution strategies can produce different transitive dependency sets for the same top-level pins. Options considered: exact pins with a committed lockfile, version ranges with no lockfile, version ranges with a lockfile.

**Decision:** Every direct dependency is exact-pinned in `pyproject.toml`. `uv.lock` is the authoritative record of the transitive resolution; it is regenerated with `uv lock` and committed. Every implementation environment uses `uv sync --locked`; the `--locked` flag refuses any deviation from the lockfile.

**Consequences:**

- Every environment (developer, CI, release) installs the same dependency set.
- Adding a new direct dependency is a deliberate change; it requires updating both `pyproject.toml` and `uv.lock`.
- The lockfile is large but provides strong reproducibility guarantees.
- The policy prohibits `optional-dependencies` tables in `pyproject.toml`; all required dependencies are pinned directly.
- Phase 3 adds `in-toto==3.1.0` to the locked dependency set (Contract 3.5). It transitively pulls `securesystemslib`, `iso8601`, `pathspec`, and `python-dateutil`. The dependency is consumed only by the `attest --in-toto` code path; the rest of the attestation surface continues to use the existing `cryptography==50.0.0` plus stdlib. The lockfile is the authoritative source; `uv lock --check` must pass before any Phase 3 commit.

## Supersedes

None.