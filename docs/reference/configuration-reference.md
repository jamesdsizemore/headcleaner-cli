# Configuration reference

This page documents every field headcleaner accepts in its policy files. Policy files are TOML documents that describe the rules you want headcleaner to enforce during a run. A policy file can be passed explicitly via `--policy`, or it can be discovered from `<bundle>/.headcleaner/policies/`.

The reference below is organized into sections that match the sections of a policy file. Each field documents what it does, what values it accepts, and what the default is when you do not set it.

## `[policy]` section

The `[policy]` section defines the trust family fields a concept must have. A concept is any Markdown file in the bundle with the OKF frontmatter shape. If a concept violates a rule in this section, the policy evaluation emits an error finding.

### `require_type`

What it does: declares what value the concept's `type` field must have.

Values: a string (e.g. `"Document"`) or `"*"` (any non-empty string).

Default: `"*"` — any non-empty type is accepted.

Example:

```toml
[policy]
require_type = "Document"
```

With this rule, every concept in the bundle must have `type: Document`. Concepts with `type: Note` or no `type` at all will produce an error finding.

### `require_status`

What it does: declares what value or values the concept's `status` field is allowed to have.

Values: a list of strings, or a single string, or `"*"` (any non-empty string).

Default: `["*"]` — any non-empty status is accepted.

Example:

```toml
[policy]
require_status = ["unverified", "human:reviewed"]
```

With this rule, every concept's `status` must be either `unverified` or `human:reviewed`. Concepts with `status: stale` or no `status` will produce an error finding.

### `require_verified`

What it does: declares what value or values the concept's `verified` field is allowed to have.

Values: a list of strings, or a single string, or `"*"` (any non-empty string).

Default: `["*"]` — any non-empty value is accepted.

Example:

```toml
[policy]
require_verified = ["human:pending", "human:reviewed"]
```

With this rule, every concept's `verified` field must be one of these values. The recommended pattern is to require `human:pending` so that auto-converted files are explicitly marked as awaiting human review.

### `require_sources`

What it does: declares whether every concept must have a non-empty `sources[]` array.

Values: `true` or `false`.

Default: `false`.

Example:

```toml
[policy]
require_sources = true
```

With this rule, every concept must have at least one source citation. Concepts without `sources[]` will produce an error finding.

### `require_sha256`

What it does: declares whether every entry in `sources[]` must include a valid SHA-256 hash.

Values: `true` or `false`.

Default: `false`.

Example:

```toml
[policy]
require_sha256 = true
```

With this rule, every entry in `sources[]` must include a `sha256` field that is exactly 64 lowercase hex characters. Concepts with malformed source citations will produce an error finding.

## `[claims]` section

The `[claims]` section controls the behavior of the claims analysis. It applies to both the `claims` command and the conversion pipeline when claim analysis is enabled.

### `claims.suppressions`

What it does: declares which claim kinds to suppress during claim extraction, with the reason for each suppression. Suppressed claims are still extracted (so the audit trail is complete) but they are excluded from conflict pairing.

Values: a TOML table mapping claim kind (`date`, `amount`, `owner`, `status_label`) to a non-empty string explaining the reason.

Default: empty table — no suppressions.

Example:

```toml
[claims.suppressions]
owner = "policy/privacy/owner-pii"
status_label = "policy/review/status-pending"
```

With this rule, owner and status_label claims are marked as `status: suppressed` with the given reason. They appear in the claim candidates list but never participate in conflict pairing.

### `claims.scope`

What it does: declares the scope used to compare claims for conflict detection. The scope determines which claims are considered for pairing against each other.

Values: `"bundle"` (compare claims from anywhere in the bundle against each other) or `"source"` (only compare claims that share a source SHA-256).

Default: `"bundle"`.

Example:

```toml
[claims]
scope = "source"
```

With this rule, two claims of the same kind with unequal values only produce a `potential_conflict` finding if they share a source. This is the right scope for a single-document corpus or a corpus where each document is authoritative for its own claims.

## `[graph]` section

The `[graph]` section controls the behavior of graph generation and querying.

### `graph.exclude_edge_kinds`

What it does: declares which edge kinds should be excluded from the generated graph and from graph queries. Excluded edges are removed before the graph is written or queried; they are not represented in the output.

Values: a list of edge kind strings. Allowed values are `contains`, `cites`, `mentions`, `related_to`, `duplicate_candidate`, `conflicts_candidate`.

Default: empty list — no exclusions.

Example:

```toml
[graph]
exclude_edge_kinds = ["mentions", "duplicate_candidate"]
```

With this rule, the generated graph does not include mention edges or duplicate-candidate edges. The graph is rebuilt from canonical chunks with these kinds filtered out; the underlying chunks are unchanged.

## `[attachments]` section

The `[attachments]` section configures the attachment recursion safety limits. The defaults are conservative; tighten them for safety, loosen them for completeness.

### `attachments.max_depth`

What it does: the maximum recursion depth for nested archives.

Values: a positive integer.

Default: `2`.

### `attachments.max_members`

What it does: the maximum number of members allowed per archive.

Values: a positive integer.

Default: `100`.

### `attachments.max_member_bytes`

What it does: the maximum size of a single archive member in bytes.

Values: a positive integer.

Default: `26214400` (25 MB).

### `attachments.max_total_bytes`

What it does: the maximum total extracted bytes for a single archive.

Values: a positive integer greater than or equal to `max_member_bytes`.

Default: `104857600` (100 MB).

Example:

```toml
[attachments]
max_depth = 3
max_members = 50
max_member_bytes = 10485760
max_total_bytes = 52428800
```

## Reading order in a policy file

The `[policy]`, `[claims]`, `[graph]`, and `[attachments]` sections are independent. They can appear in any order in a policy file, and you can omit any section you do not need. A policy file with only a `[policy]` section is valid and means "apply trust-family rules, use defaults for everything else."

## What to read next

The [CLI reference](cli-reference.md) shows how to pass a policy file to each command. The [result reference](result-reference.md) documents how policy findings appear in the manifest and report. The [configuration cookbook](../_archive/legacy-docs/CONTRIBUTING.md) (archived, retained for reference) shows end-to-end examples of policy files for common use cases.