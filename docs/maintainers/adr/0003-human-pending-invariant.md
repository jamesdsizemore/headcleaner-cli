# 0003 — Auto-conversion never promotes `verified` to reviewed

**Status:** Accepted
**Date:** 2026-08-20
**Context:** Downstream systems that consume headcleaner output (regulatory archives, publication pipelines, legal-hold systems) treat `verified: human:reviewed` as evidence that a human has reviewed the content. If headcleaner silently promoted files from `human:pending` to `human:reviewed`, those downstream systems would treat auto-converted content as reviewed. That would be unsafe.

**Decision:** Headcleaner always emits `verified: human:pending` on auto-converted files. The field is set in code; no code path changes it during a run. Changing the field requires a manual edit by a human reviewer; headcleaner provides no command that performs the transition.

**Consequences:**

- Downstream systems that require human review can safely consume headcleaner output as `human:pending`.
- The transition to `human:reviewed` is part of the human review workflow, not the conversion workflow.
- A reviewer who marks a file as reviewed is asserting "I read this and it is correct." No programmatic interface can know whether the assertion is true.

## Supersedes

None.