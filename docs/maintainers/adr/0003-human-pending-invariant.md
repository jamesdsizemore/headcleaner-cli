# 0003 — Auto-conversion never promotes `verified` to reviewed

**Status:** Accepted
**Date:** 2026-08-20
**Context:** Downstream systems that consume headcleaner output (regulatory archives, publication pipelines, legal-hold systems) treat `verified: human:reviewed` as evidence that a human has reviewed the content. If headcleaner silently promoted files from `human:pending` to `human:reviewed`, those downstream systems would treat auto-converted content as reviewed. That would be unsafe.

**Decision:** Headcleaner always emits `verified: human:pending` on auto-converted files. The field is set in code; no code path changes it during a run. Changing the field requires a manual edit by a human reviewer; headcleaner provides no command that performs the transition.

**Consequences:**

- Downstream systems that require human review can safely consume headcleaner output as `human:pending`.
- The transition to `human:reviewed` is part of the human review workflow, not the conversion workflow.
- A reviewer who marks a file as reviewed is asserting "I read this and it is correct." No programmatic interface can know whether the assertion is true.
- Phase 3 adds `headcleaner review-queue` and `headcleaner readiness` as evidence-driven read-only signals. Both are explicitly forbidden from mutating `verified:` — the queue writes only an audit sidecar at `<bundle>/.headcleaner/queue-audit.json`, and the readiness report is computed without ever touching concept frontmatter. Verified by `tests/test_review_queue.py::test_queue_commands_never_change_verified_in_frontmatter` and `tests/test_readiness.py::test_build_report_does_not_modify_concept_frontmatter`.
- Phase 3 `headcleaner attest` carries the trust state through the OKF `verified` field but does not change it; the attestation payload is a signed snapshot of what was, not an authorisation of what should be.

## Supersedes

None.