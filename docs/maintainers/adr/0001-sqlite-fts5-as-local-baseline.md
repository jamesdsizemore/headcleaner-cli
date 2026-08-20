# 0001 — SQLite FTS5 as the local search baseline

**Status:** Accepted
**Date:** 2026-08-20
**Context:** Phase 2 requires a local search index for cited chunks. The index must be deterministic, rebuildable, and free of network dependencies. Options considered: SQLite FTS5, whoosh, tantivy bindings, a hand-rolled inverted index.

**Decision:** Use SQLite FTS5 as the baseline. The Python standard library ships SQLite; FTS5 is built into recent Python distributions. No new dependencies are required, the storage format is portable across platforms, and the query language supports the keyword search and filter intersection that Phase 2 requires.

**Consequences:**

- Search is local by default; no separate service to install.
- The index file is a single SQLite database per bundle, portable and copyable.
- Vector search and remote embedding are layered on top via the embedding provider; they are not part of the baseline.
- The query language is limited to FTS5 syntax (no regex, no wildcard prefix matching across all terms).
- The connection lifecycle requires `contextlib.closing` on Windows because the SQLite context manager commits but does not close.

## Supersedes

None.