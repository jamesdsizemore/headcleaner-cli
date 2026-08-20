# CI overview

Headcleaner fits into continuous integration pipelines as a deterministic document conversion step. This page explains the design considerations for CI integration, the typical workflow shape, and how to keep the pipeline honest about what it actually verifies.

## Why headcleaner in CI

The reason to put headcleaner in CI is the same reason to put any other quality check in CI: catch regressions early, give reviewers a stable artifact, and make the run visible to the team. Headcleaner specifically gives you:

- A canonical Markdown/OKF output that can be diffed between runs.
- A manifest with per-file status, source hashes, and engine attribution.
- A run report in human-readable form that surfaces in the CI UI.
- A local search index that can be queried from downstream tools.
- A policy test command that fails the build on configured violations.

These together let a CI pipeline answer "did our document conversion get worse?" with structured data, not subjective review.

## The shape of a CI workflow

A typical CI workflow has these stages:

1. **Setup.** Check out the repository, install the locked Python environment with `uv sync --locked --python 3.13`, install any optional tools the documents require.
2. **Convert.** Run `headcleaner convert` with the flags appropriate for the corpus. Capture the run artifacts.
3. **Index.** Run `headcleaner index rebuild` to build the search index over the chunks. This is optional but catches chunking regressions.
4. **Policy.** Run `headcleaner policy test` against the bundle with a policy pack that defines the rules your team cares about.
5. **Upload.** Upload the manifest, the report, and the diff against the previous run as artifacts.
6. **Summarize.** Write a summary into the CI UI so reviewers see the result inline.

The [tutorial on CI integration](../tutorials/ci-integration.md) walks through this shape for GitHub Actions specifically. The general shape is the same for any CI system.

## What to install on the CI runner

The default answer is: install the smallest set of optional tools that lets the corpus convert correctly. The CI runner does not need OfficeCLI if the corpus has no Office documents; it does not need Tesseract if the corpus has no scanned PDFs.

The principle is: install what you need to verify, not what you might use. A larger install is more attack surface and more time, with no benefit unless the documents require it.

## What to fail on

The CI workflow should fail the build on policy violations and on conversion failures, but not on warnings. The semantics are:

- `ok` and `warn` results do not fail the build. They are informational.
- `failed` and `error` results fail the build with a non-zero exit code.
- Policy error findings fail the build.
- Policy warning findings do not fail the build unless `--strict` is set.

This shape keeps the build stable while still catching real problems.

## Diffing between runs

To catch quality regressions, capture the output of each run and diff it against the previous run. The cleanest way is to capture the manifest as a CI artifact, then on each subsequent run diff the new manifest against the stored one. Unexpected changes in:

- `totals.ok` count — a drop may mean a conversion is failing.
- `engines` keys — a new engine or a missing engine may indicate a configuration change.
- `results[*].engine` — a file being routed to a different engine may indicate a routing regression.

A reasonable threshold is "any unexpected change fails the build"; a stricter policy is to fail only on `totals.ok` decreases. Pick the one that matches your team's tolerance for churn.

## Capturing structured events

Passing `--json` to `convert` produces a stream of structured events that downstream tools can consume. The stream format is stable across versions; a downstream dashboard can track per-file status over time without parsing the human-readable report.

The stream's `events validate` subcommand checks the stream against the schema. Use it in CI as a guard against silent format drift.

## Common pitfalls

The most common CI pitfalls are:

- **Installing every optional tool.** Pick the ones you need.
- **Failing on warnings.** Warnings are signals, not errors. Treat them as such.
- **Comparing manifests as strings.** Manifests include timestamps and run metadata that change every run. Compare specific fields, not the whole file.
- **Not capturing artifacts.** If you do not capture the run report, a failed build has nothing for the developer to read. Always upload the report and manifest.
- **Running without the lockfile.** `uv run` without `--no-sync` will check the lockfile on every command. Use `--no-sync` for CI to keep runs fast and deterministic.

## Where to read next

The [tutorial on CI integration](../tutorials/ci-integration.md) has the full GitHub Actions walkthrough. The [configuration reference](../reference/configuration-reference.md) documents the policy file format. The [result reference](../reference/result-reference.md) explains every field of the manifest.