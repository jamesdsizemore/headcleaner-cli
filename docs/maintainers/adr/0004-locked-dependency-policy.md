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

## Supersedes

None.