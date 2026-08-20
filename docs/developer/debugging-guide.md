# Debugging guide

This page documents the debugging techniques that are most useful when working on headcleaner. It assumes you have read the [contributor onboarding guide](contributor-onboarding.md) and have a working development environment.

## Running focused tests with verbose output

The most common debugging technique is running a single test with full output. The command:

```bash
unset PYTHONPATH
uv run --no-sync --python 3.13 pytest tests/test_<file>.py::test_<name> -rs --no-header -vv
```

The `-vv` flag tells pytest to print the full diff for assertion failures. Combined with `--tb=long`, it gives you the complete traceback for any failure:

```bash
unset PYTHONPATH
uv run --no-sync --python 3.13 pytest tests/test_<file>.py::test_<name> -rs --no-header --tb=long
```

## Running tests with print output

If you need to see `print` output from inside a test (or from the code under test), pass `-s` to pytest:

```bash
unset PYTHONPATH
uv run --no-sync --python 3.13 pytest tests/test_<file>.py::test_<name> -rs --no-header -s
```

The `-s` flag disables pytest's stdout capture. Be careful: print output interleaves with pytest's own output, which can be hard to read. For more structured debugging, use the `logging` module instead.

## Running headcleaner with debug logging

Headcleaner's logging level is controlled by the standard `logging` module. To enable DEBUG-level logging:

```bash
unset PYTHONPATH
uv run --no-sync --python 3.13 python -c "
import logging
logging.basicConfig(level=logging.DEBUG)
from headcleaner.cli import main
main(['convert', './in', './out'])
"
```

The DEBUG output is verbose; you usually want to focus on one module. The most common targets are `headcleaner.router`, `headcleaner.run`, `headcleaner.chunking`, and `headcleaner.index`.

## Inspecting the manifest

When a conversion produces unexpected output, the first place to look is the manifest. The manifest is the canonical record of what happened. Open `<output>/manifest.json` and look at the per-file result entries:

- `engine`: which adapter handled the file.
- `status`: `ok`, `warn`, `failed`, `error`, or `skipped`.
- `error`: the error message for `failed`/`error`/`skipped`.
- `diagnostics`: the structured diagnostic list.

The manifest is also a good way to verify that the run configuration matches your expectations: the `options` object at the top records the flags you passed.

## Inspecting chunks

When the search index returns unexpected results, the next place to look is the chunk derivative. Open `<bundle>/okf/chunks.jsonl` and look at the entries:

- `concept_id`: which concept the chunk belongs to.
- `source_sha256`: the source file's hash.
- `heading_path`: the heading path the chunk inherited.
- `text`: the chunk body.
- `citation`: the source citation.

If a chunk you expected is missing, the chunking algorithm may have produced a different chunk for your input. If a chunk is present but not in the search index, the rebuild may have failed; check `INDEX_BUILD_FAILED` in the manifest.

## Inspecting the graph

When the graph returns unexpected results, the next place to look is the graph derivative. Open `<bundle>/okf/graph.jsonl` and look at the node and edge lines:

- Each node has `id`, `kind`, `label`, `source_refs`, and `attributes`.
- Each edge has `id`, `kind`, `from_id`, `to_id`, `evidence_chunk_ids`, `method`, and `status`.

If an edge you expected is missing, the policy may be excluding it. If a node has an unexpected kind, the bounded vocabulary may have rejected a value you did not realize was unsupported.

## Using a debugger

Python's built-in debugger (`pdb`) works with pytest. To drop into `pdb` on a test failure, pass `--pdb`:

```bash
unset PYTHONPATH
uv run --no-sync --python 3.13 pytest tests/test_<file>.py::test_<name> -rs --no-header --pdb
```

For breakpoints at specific lines, use `breakpoint()` (Python 3.7+) or `pdb.set_trace()`:

```python
def my_function(...):
    breakpoint()
    # rest of the function
```

The `--pdb` flag and `breakpoint()` calls work together. The debugger starts at the first breakpoint and lets you inspect the local state.

## Common failure modes

The failure modes most contributors hit:

- **Lockfile drift.** `uv sync --locked` fails because `uv.lock` is out of date. Fix: pull the latest changes, re-run `uv sync --locked`.
- **Wrong Python.** `uv run` uses a Python version that is not 3.13. Fix: pass `--python 3.13` explicitly.
- **Missing optional tool.** A test that depends on LibreOffice or Tesseract skips with a clear message. Fix: install the optional tool, or skip the test.
- **Stale `.venv`.** The virtual environment has accumulated cruft from previous experiments. Fix: `rm -rf .venv` and re-run `uv sync --locked --python 3.13`.
- **Source-of-truth confusion.** A test reads from `<bundle>` but the bundle was not built. Fix: run the conversion first, or use the `bundle` fixture.

## What to read next

The [contributor onboarding guide](contributor-onboarding.md) covers the platform-specific setup. The [testing guide](testing-guide.md) covers the test layers and the RED/GREEN cycle. The [architecture developer guide](architecture.md) explains how the modules fit together.