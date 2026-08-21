# CI and packaging

This page documents the CI workflow, the locked environment, and the system-tool installation contract. It is the developer reference for what makes a headcleaner build pass on every platform.

## The CI workflow

The CI workflow lives at `.github/workflows/test.yml`. It runs on every push and pull request, on Windows, macOS, and Linux runners, against Python 3.12 and 3.13.

The workflow's steps:

1. Check out the repository.
2. Set up Python with the appropriate version.
3. Install `uv` if not already on the runner.
4. Run `unset PYTHONPATH; uv sync --locked --python <version>` to provision the locked environment.
5. Run `uv run --no-sync --python <version> pytest -rs --no-header` to run the full test suite.
6. Upload the test artifacts (manifests, reports, test logs) on failure.

The workflow is expected to take a few minutes per platform per Python version. The slowest jobs are the integration tests that depend on optional tools (LibreOffice for `test_legacy_office.py`, zsv for `test_zsv_adapter.py`); these jobs are expected to install the optional tool before running.

## The locked environment

Headcleaner's dependencies are pinned in `uv.lock`. Every CI run, every developer machine, and every release uses the same locked environment. The single command that provisions a reproducible environment is:

```bash
unset PYTHONPATH
uv sync --locked --python 3.13
```

The `--locked` flag tells `uv` to refuse any deviation from the lockfile. If the lockfile drifts from the project's intended dependency set, `uv` exits non-zero with a clear message. The fix is to pull the latest changes from the project and re-run, not to relax the lockfile constraint.

The `--python 3.13` flag tells `uv` to use Python 3.13. If the runner does not have Python 3.13, `uv` downloads a managed Python 3.13 and uses that.

## System-tool installation

Headcleaner depends on a small set of optional system tools. The CI runners install these tools in their setup steps; the developer machine installs them per the [installation guide](../getting-started/installation.md).

The tools:

- **OfficeCLI** — installed via `npm install -g @officecli/officecli`.
- **LibreOffice** — installed via the platform's package manager.
- **Tesseract** — installed via the platform's package manager.
- **`readpst`** — installed via the platform's package manager.

The exact commands for each platform are documented in the [installation guide](../getting-started/installation.md#optional-tools-that-make-headcleaner-more-useful).

## Doctor as the environment gate

`headcleaner doctor` is the canonical environment check. It reports which tools are present, which are missing, and whether the headcleaner Python environment is correctly provisioned. The CI workflow does not currently call doctor explicitly, but it is the right command to add if you want the CI to fail-fast on a missing optional tool rather than failing the integration tests with a skip message.

## The per-phase merge gate

The master plan defines a per-phase merge gate. The Phase 2 gate is:

```bash
unset PYTHONPATH
uv sync --locked --python 3.13
uv run --no-sync --python 3.13 pytest -rs --no-header
git diff --check
```

The first command refreshes the locked environment; the second runs the full test suite; the third checks for whitespace errors in the diff. A green run on all three is the signal that the phase is complete.

## Adding a new CI job

If you need to add a new CI job (for example, to test a new optional tool), the steps are:

1. Add the job definition to `.github/workflows/test.yml`. Use the existing jobs as templates.
2. Install the optional tool in the job's setup steps. Follow the patterns from the integration tests.
3. Add a focused pytest invocation that covers the new tool. Use `-k` to filter or a separate test file with explicit skip conditions.
4. Update the [compatibility reference](../reference/compatibility.md) to document the new tool and its install instructions.

## Adding a new dependency

If you need to add a new direct dependency:

1. Add the exact-pinned version to `pyproject.toml`. Headcleaner uses exact pins; do not add a version range.
2. Run `uv lock` to regenerate `uv.lock`. Commit the updated lockfile.
3. Add a test that asserts the dependency is importable and the version matches the pin.
4. Update the [compatibility reference](../reference/compatibility.md) if the dependency has platform-specific notes.

## Phase 3 dependencies

Phase 3 added `in-toto==3.1.0` to the locked dependency set, transitively pulling `securesystemslib`, `iso8601`, `pathspec`, and `python-dateutil`. The dependency is consumed only by the `attest --in-toto` code path; the rest of the attestation surface (Merkle tree, ed25519 signing, canonical JSON, source/output SHA sets) uses the existing `cryptography==50.0.0` and stdlib modules. The CI workflow picks the dep up via `uv sync --locked`; no extra install step is required.

## What to read next

The [contributor onboarding guide](contributor-onboarding.md) covers the platform-specific setup. The [compatibility reference](../reference/compatibility.md) is the platform support matrix. The [testing guide](testing-guide.md) covers the test layers and the RED/GREEN cycle.