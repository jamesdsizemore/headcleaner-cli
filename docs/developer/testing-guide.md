# Testing guide

This page documents headcleaner's test layers, the fixtures they share, and the conventions for writing new tests.

## The test layers

Headcleaner's tests are organized into layers. Each layer has a focused responsibility and a small set of dependencies on the layers below it.

### Unit tests

Unit tests cover individual functions and dataclasses in isolation. They use no real external services and no real adapters; the dependencies they need are passed in or mocked.

The unit test files are named after the module they test: `tests/test_normalize.py` for `src/headcleaner/normalize.py`, `tests/test_chunking.py` for `src/headcleaner/chunking.py`, and so on.

### Contract tests

Contract tests cover the data shapes and invariants defined by the master plan's per-contract sections. They are stricter than unit tests: they assert the exact field names, the exact kinds, and the exact trust-state defaults.

The contract test files include `tests/test_chunking.py` (Contract 2.1), `tests/test_index.py` (Contract 2.2), `tests/test_search.py` (Contract 2.2 API/MCP reuse), `tests/test_embeddings.py` (Contract 2.3), `tests/test_graph.py` (Contract 2.4), `tests/test_dedupe.py` (Contract 2.5), `tests/test_diff.py` (Contract 2.6), `tests/test_claims.py` (Contract 2.7), and `tests/test_sync.py` (Contract 2.8).

### CLI tests

CLI tests drive the Click commands through the `CliRunner` and assert on stdout, stderr, and exit codes. They exercise the full argument-parsing path, including flag validation and help-text generation.

The CLI tests live alongside the contract tests in the same files.

### MCP stdio tests

MCP stdio tests spawn the MCP server in-process and connect a real MCP client. They exercise the full request/response cycle, including JSON-RPC framing. The tests live in `tests/test_mcp.py`.

### Schema tests

Schema tests validate headcleaner's JSON Schemas against canonical data and against the schemas themselves. The schema files are in `docs/schemas/`; the tests are in `tests/test_okf_schema.py`.

### Integration tests

Integration tests are gated on optional tools. They are skipped when the optional tool is not installed (e.g. LibreOffice for `tests/test_legacy_office.py`, the zsv binary for `tests/test_zsv_adapter.py`). Skipped tests report the reason so you can see what is missing.

The integration tests cover real-world conversion paths with real optional tools. They are the most expensive tests in the suite and are the ones most likely to skip on a developer's machine.

## The fixtures

Headcleaner shares fixtures through `tests/conftest.py`. The most commonly used fixtures:

- `tmp_path` — pytest's built-in per-test temporary directory. Used for everything that needs a writable filesystem location.
- `bundle` — a fixture that builds an OKF bundle with a small set of concepts, ready for chunking, indexing, and search.
- `_bundle(tmp_path)` — a helper function used by individual tests to construct a bundle from scratch.

When a test needs a specific kind of source file (a DOCX with embedded images, a PDF with tables, an email with attachments), the test creates the source file in `tmp_path` rather than relying on a checked-in fixture. This keeps the test self-contained and avoids the maintenance burden of large fixture files.

## Writing a new test

The recipe for writing a new test:

1. Identify the file the test belongs in. If it covers a specific module, the file is `tests/test_<module>.py`. If it covers a CLI command, it goes in the file that already tests that command.
2. Decide whether the test is a unit test, contract test, CLI test, or integration test. The choice determines the fixture set and the assertion style.
3. Write the test. Use descriptive names (`test_<thing>_<condition>_<expected_outcome>`) and assert on the smallest set of fields that prove the contract holds.
4. Run the focused test before opening a pull request. The command is `unset PYTHONPATH && uv run --no-sync --python 3.13 pytest tests/test_<file>.py -rs --no-header`.

## The RED/GREEN cycle

For Phase 2 and later work, every contract amendment starts with a RED test that fails for the documented reason. The test is committed before the implementation; the commit history records the cycle.

The recipe:

1. Write the failing test in the appropriate file. The test should fail with a clear error message that names the missing functionality.
2. Run the focused test and confirm the RED. The exit code is non-zero and the failure reason is what you expect.
3. Make the smallest change that makes the test pass. Do not refactor; do not add features; do not change unrelated code.
4. Run the focused test and confirm the GREEN. The exit code is zero and the assertions pass.
5. Run the full test suite to confirm no regressions. The exit code is zero and the count of passing tests is the previous count plus one.

## The per-stage gate

The master plan defines per-stage verification gates. The Phase 2 gate is:

```bash
unset PYTHONPATH
uv sync --locked --python 3.13
uv run --no-sync --python 3.13 pytest tests/test_chunking.py tests/test_index.py tests/test_search.py tests/test_dedupe.py tests/test_diff.py tests/test_claims.py tests/test_sync.py tests/test_embeddings.py tests/test_graph.py -rs --no-header
```

The first command refreshes the locked environment; the second runs the focused Phase 2 tests. A green run on the focused tests is the signal that the implementation is complete for the stage.

## What to read next

The [contributor onboarding guide](contributor-onboarding.md) covers the platform-specific setup. The [architecture developer guide](architecture.md) explains how the modules fit together. The [CI and packaging guide](ci-and-packaging.md) covers the CI workflow.