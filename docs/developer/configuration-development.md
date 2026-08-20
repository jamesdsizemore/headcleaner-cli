# Configuration development

This page explains how headcleaner accepts configuration. It is the developer reference for the policy file format, the discovery rules, and the integration points with the rest of the pipeline.

## The policy file format

Policy files are TOML. They declare rules for the trust family, claim analysis, graph edge filtering, and attachment safety limits. The full reference is in the [configuration reference](../reference/configuration-reference.md); this page covers how the format is parsed and applied.

The top-level sections are `[policy]`, `[claims]`, `[graph]`, and `[attachments]`. The sections are independent; you can omit any section you do not need. A policy file with only a `[policy]` section is valid.

## Discovery

Policy files are discovered in two ways:

- **Explicit:** pass `--policy PATH` to any command that supports it. The path must point to a readable TOML file.
- **Bundle-local:** headcleaner looks in `<bundle>/.headcleaner/policies/` for files matching `*.toml`. The first file in lexical order is loaded; later files are ignored.

If neither an explicit path nor a bundle-local file is found, the default policy is used. The default policy accepts anything (`require_type = "*"`, etc.) and uses the default claim and graph settings.

## Parsing

The `Policy.load` classmethod in `src/headcleaner/policy.py` parses the file. It validates:

- The `[policy]` section types (strings, lists, booleans).
- The `[claims]` section types (suppression table with non-empty reasons, scope enum).
- The `[graph]` section types (edge kinds against the allowlist).
- The `[attachments]` section types (positive integers, total >= member).

A failure in any of these validations raises `ValueError` with a descriptive message. The CLI converts the error to a `ClickException` with exit code 2.

## Evaluation

The `evaluate` function walks every concept in the bundle and checks it against the policy. Findings are recorded with severity `info`, `warning`, or `error`. The function is pure and deterministic: given the same bundle and policy, it returns the same findings.

```python
def evaluate(policy: Policy, bundle_root: Path) -> list[PolicyFinding]: ...
```

The CLI command `headcleaner policy test BUNDLE --pack PACK` calls this function and maps findings to exit codes:

- 0 — no error findings
- 1 — at least one error finding
- 2 — invalid pack

## Integration with the pipeline

The conversion pipeline does not evaluate policy. Policy is a separate command and a separate file. This is intentional: policy evaluation is a CI-side concern, and a run should not fail because of a policy violation in development.

The conversion pipeline does, however, carry selected policy settings through to the claims analysis. The `RunOptions` include `claim_suppressions` and `claim_scope`, which the pipeline passes to `claims.analyze_claims`. This means a policy that suppresses `owner` claims in CI also suppresses them when the pipeline emits the claim-review derivative.

## Extension points

The policy format is intentionally small. There is no general-purpose expression language; rules are limited to:

- Field equality checks against allowlists.
- Required-vs-present checks on `sources[]`, `sha256`, and similar shape fields.
- Stale-date comparison against today's date.

If you want a new rule kind, file an issue. The extension is done by adding a new validator to `Policy.load`, a new rule kind to the evaluator, and a test that covers the new rule.

## Adding a new policy field

If you want to add a new field to an existing section, the steps are:

1. Add the field to the dataclass in `src/headcleaner/policy.py`.
2. Add parsing in `Policy.load`.
3. Add validation if the field has constraints (e.g. enum values, ranges).
4. Add the field to the [configuration reference](../reference/configuration-reference.md).
5. Add a test in `tests/test_policy.py`.

For a new section, the steps are the same plus updating the `Policy` dataclass and the evaluator.

## What to read next

The [configuration reference](../reference/configuration-reference.md) is the field-by-field documentation. The [tool and engine development guide](tool-and-engine-development.md) covers adapter development. The [chunking and indexing developer guide](chunking-and-indexing.md) covers the search index, which is configured separately from the policy file.