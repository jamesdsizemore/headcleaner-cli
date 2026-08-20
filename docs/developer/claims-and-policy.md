# Claims and policy

This page documents headcleaner's claim extraction, stale lifecycle detection, and conflict pairing. It covers the data model, the detection rules, the policy integration, and the lifecycle of the claim-review derivative.

## The claims module

The claims module lives in `src/headcleaner/claims.py`. The entry point is `analyze_claims`, which takes the canonical chunks plus policy settings and returns claim candidates and findings.

## Claim kinds

The initial claim kinds are:

- `date` — ISO 8601 dates extracted from chunk text.
- `amount` — monetary amounts (with currency when detectable).
- `owner` — named owners (people, teams, or organizations).
- `status_label` — explicit status assertions like "approved," "rejected," "in review."

Other kinds are rejected at extraction time. The kind enum is part of the data contract; adding a new kind requires updating the `Policy` validators in `src/headcleaner/policy.py` and the documentation in the [configuration reference](../reference/configuration-reference.md).

## Detection rules

Claims are extracted using deterministic patterns. There is no LLM, no semantic classification, and no model invocation. The patterns are documented in the implementation:

- Dates: `\b\d{4}-\d{2}-\d{2}\b` and a few common variations.
- Amounts: `\$?\d+(\.\d+)?\s?(USD|EUR|GBP|JPY|CAD|AUD)?`.
- Owners: capitalized-name detection, conservative.
- Status labels: a curated set of explicit phrases.

A claim candidate has a `source_chunk_id`, a `citation` block, an `extraction_rule` (the pattern identifier), and a `status` (initially `unverified`).

## The cap

At most 5,000 claim candidates are extracted per run. Above that cap, the analyzer emits a `CLAIMS_TOO_MANY` diagnostic and skips pairwise comparison. The cap is centrally configured; changing it requires updating both the implementation and the documentation.

The cap is a safety boundary, not a performance optimization. An unbounded pairwise comparison over millions of claim candidates would produce unbounded findings, and the bounded output is what makes the conflict report trustworthy.

## Conflict pairing

Conflict findings require two claim candidates of the same kind with unequal values and compatible scope. The scope is selected by an explicit policy rule:

- `scope = "bundle"` (default): claims from any source are compared against each other.
- `scope = "source"`: claims are grouped by source SHA before comparison; only claims that share a source are paired.

The conflict finding's `rule_id` includes the scope, e.g. `claims/date/unequal/bundle` or `claims/date/unequal/source`. The `type` is exactly `potential_conflict`; headcleaner never labels a finding `false` or `contradiction` because the analyzer does not assert factual truth.

## Suppression

Policy may declare claim suppressions. The TOML section is:

```toml
[claims.suppressions]
owner = "policy/privacy/owner-pii"
status_label = "policy/review/status-pending"
```

Suppressed claims retain `status: suppressed` with the given `suppression_reason`. They appear in the claim candidates list (so the audit trail is complete) but are excluded from conflict pairing. The suppression is policy-recorded, not erased.

## Stale lifecycle

Stale findings derive from `stale_after` and `generated`/`reviewed` dates. There are two modes:

- **Per-source lifecycle.** Pass a `stale_after_by_source` map of `source_sha256 -> ISO date`. For each source whose `stale_after` is earlier than today, a stale finding is emitted with the source citation preserved.
- **Global lifecycle.** Pass a single `stale_after` date. For each chunk whose citation's `stale_after` is earlier than today, a stale finding is emitted. This is the legacy behavior, retained for compatibility.

The per-source mode is preferred because it ties the finding back to the specific source. The rule ID for both is `lifecycle/stale_after`.

## Pipeline integration

The conversion pipeline calls `analyze_claims` after `rebuild_chunks` and before `build_graph`. The pipeline carries `claim_suppressions` and `claim_scope` from `RunOptions` into the call. The claim-review derivative is written atomically to `okf/claim-review.json`, and the manifest records the candidate and finding counts.

After claim-review is written, the graph is rebuilt with claim linkage. The rebuild links unverified claim candidates to topic nodes as `related_to` edges, then writes the final `graph.jsonl`. The two-step sequence ensures the graph's claim edges reflect the same claims that appear in the claim-review derivative.

## What to read next

The [canonical model developer guide](canonical-model.md) documents the `ClaimCandidate` and `Finding` dataclasses. The [configuration reference](../reference/configuration-reference.md) documents the policy file format including claim suppressions and scope. The [graph development developer guide](graph-development.md) covers the claim-to-graph linkage in detail.