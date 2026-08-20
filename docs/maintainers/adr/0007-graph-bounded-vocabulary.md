# 0007 — Bounded node and edge kinds in the knowledge graph

**Status:** Accepted
**Date:** 2026-08-20
**Context:** The knowledge graph is consumed by tools that classify its content. Unbounded node and edge kinds would let future callers silently introduce factual-looking relationships into a graph whose contract is "suggestions are unverified." That would erode the safety property that graph edges are never treated as facts.

**Decision:** Node kinds are exactly `concept | chunk | entity | topic`. Edge kinds are exactly `contains | cites | mentions | related_to | duplicate_candidate | conflicts_candidate`. Every edge requires one or more evidence chunk IDs except `contains`. Edge status is exactly `explicit | unverified`; generated edges are always `unverified`.

**Consequences:**

- The vocabulary is enforced at construction; any other kind is rejected with `ValueError`.
- Adding a new kind is a deliberate change: it requires updating the constructor validator, the policy allowlist, and the documentation.
- The bounded vocabulary prevents the graph from drifting toward factual assertions; suggestions remain suggestions.
- Tools that consume the graph can switch on `kind` and `status` exhaustively.

## Supersedes

None.