# Architecture Decision Records

This directory holds Architecture Decision Records (ADRs) for headcleaner's design choices. Each ADR captures a significant decision: the context, the options considered, the decision made, and the consequences.

ADRs are immutable once accepted. If a decision changes, write a new ADR that supersedes the old one; do not edit the old one in place. The superseded ADR keeps its original content with a note at the top pointing at the replacement.

## Index

| ADR | Title | Status |
|---|---|---|
| [0001](0001-sqlite-fts5-as-local-baseline.md) | SQLite FTS5 as the local search baseline | Accepted |
| [0002](0002-okf-v0.2-as-canonical-format.md) | OKF v0.2 as the canonical knowledge format | Accepted |
| [0003](0003-human-pending-invariant.md) | Auto-conversion never promotes `verified` to reviewed | Accepted |
| [0004](0004-locked-dependency-policy.md) | Locked dependency policy with exact pins | Accepted |
| [0005](0005-neon-palette-discipline.md) | Neon cyan/pink/purple palette, no red or yellow | Accepted |
| [0006](0006-redacted-derivative-deferred.md) | Redacted indexing deferred to Phase 3 | Accepted |
| [0007](0007-graph-bounded-vocabulary.md) | Bounded node and edge kinds in the knowledge graph | Accepted |

## How to write an ADR

The template:

```markdown
# NNNN — Title

**Status:** Proposed | Accepted | Superseded by NNNN
**Date:** YYYY-MM-DD
**Context:** What is the situation that requires a decision?
**Decision:** What did we decide?
**Consequences:** What becomes easier? What becomes harder? What new constraints do we accept?
```

Keep ADRs short. The point is to capture the decision and its rationale, not to write an essay. Link to relevant code, documentation, or external references for context.

## When to write an ADR

Write an ADR when:

- The decision affects a public surface (CLI, API, schema).
- The decision constrains future design choices.
- The decision is non-obvious and would surprise a future reader.
- The decision was reached after weighing alternatives, and the alternatives should be recorded.

Do not write an ADR for:

- Implementation details that can change freely.
- Bug fixes.
- Routine refactoring.
- Decisions that affect only one file or module.