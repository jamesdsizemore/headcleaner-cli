# Contributor onboarding

This page walks a new contributor through their first passing verification on every supported platform. It covers cloning the repository, setting up the locked Python environment, running the tests, and resolving the platform-specific issues that contributors hit most often.

The page assumes you are comfortable with command-line tools and have a basic understanding of Python packaging. It does not assume you have used `uv` before.

## Outcome

By the end of this page you will have a working copy of headcleaner with a fully provisioned environment, you will have run the test suite successfully, and you will know where to look when something goes wrong.

## Prerequisites

- A supported platform: Windows 10+ (build 19041 or later), macOS 12+, or a current Ubuntu/Debian/Arch Linux distribution.
- A working C toolchain if you intend to build any Rust-backed wheels from source. Most contributors do not need this; `uv` resolves pre-built wheels for the common platforms.
- Permission to install software on your machine.
- A clone of the headcleaner repository.

The rest of this page assumes your working directory is the root of the repository clone.

## Step 1 — Install `uv`

`uv` is the recommended way to manage headcleaner's Python environment. It is fast, it handles Python installation, and it produces reproducible results across platforms.

Install `uv` per the [installation guide](../getting-started/installation.md#installing-uv). Confirm the install with `uv --version`.

## Step 2 — Sync the locked environment

Headcleaner's dependencies are pinned in `uv.lock`. The single command that provisions a reproducible environment is:

```bash
unset PYTHONPATH
uv sync --locked --python 3.13
```

The `--locked` flag tells `uv` to refuse any deviation from the lockfile. If the lockfile drifts from the project's intended dependency set, `uv` exits non-zero with a clear message. The fix is to pull the latest changes from the project and re-run, not to relax the lockfile constraint.

The `--python 3.13` flag tells `uv` to use Python 3.13. If your system has Python 3.13, `uv` uses it directly. If not, `uv` downloads a managed Python 3.13 and uses that. Either way, the resulting environment is the one headcleaner is tested against.

After `uv sync` completes, you have a `.venv/` directory at the repository root with the locked dependencies installed.

## Step 3 — Run the tests

The single command that runs the entire test suite is:

```bash
unset PYTHONPATH
uv run --no-sync --python 3.13 pytest -rs --no-header
```

The `--no-sync` flag tells `uv run` not to check the lockfile before invoking pytest. This is important because pytest may be invoked hundreds of times during development, and re-checking the lockfile each time would noticeably slow down the inner loop.

The `-rs` flag tells pytest to display the reasons for any skipped tests. The reason text is important for diagnosing environment-specific issues; the most common reason is "LibreOffice is not installed; CI runs this in its dedicated integration job" or "zsv binary not on PATH."

A healthy run reports every required test passing. Optional skips can reflect LibreOffice or `zsv` host absences; inspect their reasons and distinguish them from regressions in the files you changed.

## Step 4 — Run the focused tests for the area you will work on

If you intend to work on the search index, run only the search-related tests:

```bash
unset PYTHONPATH
uv run --no-sync --python 3.13 pytest tests/test_index.py tests/test_search.py -rs --no-header
```

If you intend to work on the embeddings module, run only the embeddings tests:

```bash
unset PYTHONPATH
uv run --no-sync --python 3.13 pytest tests/test_embeddings.py -rs --no-header
```

The pattern is the same for every module: each test file is named after the module it tests. Running focused tests before opening a pull request is part of the delivery discipline documented in the master plan.

## Platform-specific troubleshooting

### Windows

The most common Windows-specific issues are:

- **Line endings.** The lockfile (`uv.lock`) is checked out with CRLF on Windows. `uv` handles this transparently, but if you see a diff that shows every line changed, that is the cause. Configure git with `git config core.autocrlf false` for the headcleaner repository to keep the lockfile unchanged.
- **`readpst` is not available.** `readpst` ships with MSYS2 on Windows. If you need to test the `.pst` engine, install MSYS2 and add the MSYS2 `bin` directory to your `PATH`. If you do not need `.pst`, ignore the test.
- **Tesseract is in a non-default location.** The Windows installer places `tesseract.exe` in `C:\Program Files\Tesseract-OCR\` by default. If you installed it elsewhere, add that location to your `PATH` or set the explicit Tesseract path in your policy file.

### macOS

The most common macOS-specific issues are:

- **Apple Silicon under Rosetta.** If you have an Apple Silicon Mac and your `uv` or `node` is x86_64 under Rosetta, headcleaner will work but slowly. Confirm with `arch`: a healthy install prints `arm64`. Reinstall `uv` and `node` natively if you see `i386` or `x86_64`.
- **Homebrew Tesseract is keg-only.** `brew install tesseract` may place the binary in a location that is not on your default `PATH`. Either add the keg bin directory to your `PATH` or use `brew link tesseract` to link it.
- **LibreOffice Cask is large.** The LibreOffice Cask installs the full office suite. If you only need headless conversion, the cask is still the right choice; there is no headless-only package on macOS.

### Linux

The most common Linux-specific issues are:

- **Tesseract language packs.** Default Tesseract installs include only English. To install additional language packs, use your distribution's package manager (e.g. `sudo apt install tesseract-ocr-deu` for German).
- **`readpst` is in `pst-utils`.** On Debian/Ubuntu, `readpst` ships in the `pst-utils` package. On Arch, it ships in `libpst`.
- **No LibreOffice on headless servers.** If you are running on a server without LibreOffice and your corpus contains legacy Office files, those files will be skipped. Install LibreOffice via your package manager.

## Step 5 — Verify Ruff

The project uses Ruff for linting and formatting. The single command that lints everything is:

```bash
uv run --no-sync --python 3.13 ruff check .
```

A healthy run reports "All checks passed!" If Ruff reports violations in files you have not touched, leave them alone — they are pre-existing and out of scope. Focus on violations in files you have changed.

To format your changes:

```bash
uv run --no-sync --python 3.13 ruff format .
```

The formatter is opinionated. Run it before opening a pull request.

## Step 6 — Complete the documentation audit and install the commit gate

Before calling an implementation phase complete, create or update its exhaustive audit record. The record contains one evidenced decision for every active documentation page, not merely the pages you happened to edit.

```bash
uv run --no-sync --python 3.13 python scripts/verify_docs.py --write-audit-template phase-name
# fill in docs/development/phase-audits/phase-name.json
uv run --no-sync --python 3.13 python scripts/verify_docs.py --phase phase-name
sh scripts/install-git-hooks.sh
```

Before every commit, update `DEVELOPMENT_HISTORY.md` and stage the active phase audit. The hook reruns the same verification against staged work. Read the [documentation governance policy](../development/DOCUMENTATION_GOVERNANCE.md) before treating a green test run as delivery.

## Step 7 — Open your first pull request

Once your changes pass the focused tests and the focused Ruff check, you are ready to open a pull request. The repository's PR template (if there is one) will guide you through the rest.

Before opening the PR, run the full test suite one more time:

```bash
unset PYTHONPATH
uv run --no-sync --python 3.13 pytest -rs --no-header
```

A passing full run is the strongest signal that your changes have not regressed anything.

## What to read next

The [architecture developer guide](architecture.md) explains the codebase at the module level. The [tool and engine development guide](tool-and-engine-development.md) walks through adding a new adapter. The [coding standards](coding-standards.md) is the style guide. The [testing guide](testing-guide.md) explains the test layers and the fixtures.