Continue the authorized Phase 3 program in `C:\Users\james\developer\headcleaner-cli` from the safe pause boundary. Read `docs/plans/PHASE_3_HANDOFF.md` first; it is the current factual handoff.

User requirements: start with Git by inspecting `main` / `origin/main` and creating or reusing a dedicated Phase 3 branch in a separate Git worktree; make every development edit in that worktree, never in the `main` worktree; end with Git status/diff/log review of the dedicated worktree. Deeply align each Phase 3 contract with the archived authority and completed Phase 2; use strict TDD; scope each vertical slice tightly; use RTK, Graft, and context-mode commands throughout development as token-saving replacements for broader source/context reads; update docs/governance records; preserve unrelated local work.

Mandatory constraints:
- Work only in `C:\Users\james\developer\headcleaner-cli`; never modify sibling `C:\Users\james\developer\headcleaner`.
- Preserve listed untracked `.hermes/` files and `.ignore`.
- Use the exact required tests: `unset PYTHONPATH && uv run --no-sync --python 3.13 pytest ...`; final gates are normal pytest and `pytest -W error`.
- Auto-conversion/redaction/attestation/queue/readiness must never claim human review or change `verified` without explicit human review operations.
- Do not advance `docs/development/ACTIVE_PHASE.md` from phase 2 until Phase 3 documentation-audit coverage is valid.

Start with Contract 3.5’s next minimal tracer: inspect existing manifest/OKF source provenance and write a focused RED test for deterministic bundle-relative source/output SHA sets in the in-toto predicate. Observe the intended RED failure, implement only the required behavior, run focused green tests, then continue with the remaining Contract 3.5 schema/CLI/dependency work. Do not stop at a progress report: continue through dependency-safe Phase 3 contracts unless externally blocked. At the true end, conduct the required documentation audit, full normal and warning-as-error test gates, and final Git review.
