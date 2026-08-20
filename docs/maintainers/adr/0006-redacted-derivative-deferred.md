# 0006 — Redacted indexing deferred to Phase 3

**Status:** Accepted
**Date:** 2026-08-20
**Context:** The Phase 2 amendment requires that "when a policy selects redacted indexing, chunk/FTS/vector inputs are the redacted derivative and no suppressed value may enter chunks, FTS excerpts, vectors, MCP, or events." The redacted derivative itself is a Phase 3 deliverable (`redact.py`, Contract 3.3).

**Decision:** Defer the redacted-indexing path until the Phase 3 redacted derivative primitive is implemented. The Phase 2 implementation provides the contract surface (chunking, indexing, vectors, MCP, events) but does not yet consume a redacted source.

**Consequences:**

- Phase 2 acceptance criteria that do not depend on redacted indexing are met.
- Phase 2 acceptance criteria that depend on redacted indexing are documented as "blocked on Phase 3 primitive."
- The Phase 3 work will integrate cleanly because the Phase 2 contract surface is designed to accept a derivative input.
- Downstream tools should not assume Phase 2 headcleaner output is redaction-safe; the contract is that it is unredacted canonical output.

## Supersedes

None.