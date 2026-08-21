# Compatibility

This page documents the platforms and Python versions headcleaner supports, the optional tools it knows how to detect, and the known limitations on each platform. It is the place to look when you are setting up headcleaner on a new platform or debugging a platform-specific issue.

## Supported platforms

Headcleaner supports the following platforms. Each platform has been tested with the full test suite.

### Windows

- **Supported versions:** Windows 10 (build 19041 or later) and Windows 11.
- **Python:** 3.12 and 3.13. Python 3.13 is the recommended version.
- **Package manager:** `uv` is the recommended way to install Python and headcleaner. The Microsoft Store Python alias can interact poorly with `uv run`; if you have both installed, prefer `uv`-managed Python.
- **Line endings:** the lockfile is checked out with CRLF on Windows. This is a Windows convention; headcleaner handles it transparently.
- **System tools:** OfficeCLI via npm, LibreOffice via the official installer, Tesseract via the official installer, `readpst` via MSYS2. Each has a known installation path; `headcleaner doctor` reports which tools it can see.
- **Known limitations:** `readpst` ships only with MSYS2; users on pure Windows installs may need to install MSYS2 first. The Tesseract installer places the binary in a non-default location; `headcleaner doctor` will tell you the expected path.

### macOS

- **Supported versions:** macOS 12 (Monterey) and later, on both Intel and Apple Silicon.
- **Python:** 3.12 and 3.13. Python 3.13 is the recommended version.
- **Package manager:** `uv` is the recommended way to install Python and headcleaner. Homebrew works but `uv` is faster and more reproducible.
- **System tools:** OfficeCLI via npm (`npm install -g @officecli/officecli`), LibreOffice via Homebrew Cask (`brew install --cask libreoffice`), Tesseract via Homebrew (`brew install tesseract`), `readpst` via Homebrew.
- **Known limitations:** Apple Silicon users should ensure their Node.js and Python installations are arm64 native, not x86_64 under Rosetta. `headcleaner doctor` reports the architecture.

### Linux

- **Supported distributions:** Ubuntu 22.04 LTS and later, Debian 12 and later, and Arch Linux. Other distributions are likely to work but are not formally tested.
- **Python:** 3.12 and 3.13. Python 3.13 is the recommended version.
- **Package manager:** `uv` is the recommended way to install Python and headcleaner.
- **System tools:** OfficeCLI via npm, LibreOffice via `apt install libreoffice` (Debian/Ubuntu) or the distribution's package manager, Tesseract via `apt install tesseract-ocr`, `readpst` via `apt install pst-utils`.
- **Known limitations:** headless servers without `libreoffice` may have issues with `.doc` and `.xls` files. The Tesseract language packs beyond English must be installed separately.

## Python versions

Headcleaner requires Python 3.12 or 3.13. Earlier Python versions are not supported. The lockfile is built against 3.13; using 3.12 requires `uv sync` to resolve a separate lockfile or to relax the lockfile constraint, which the project does not support.

If `uv sync --locked --python 3.13` fails on your machine, the most common reason is that `uv` is using a system Python that is older than 3.13. The fix is to let `uv` download and manage Python 3.13 itself, which is what `--python 3.13` tells it to do.

## Optional tool detection

`headcleaner doctor` reports which optional tools are installed and reachable. The detection logic:

- **OfficeCLI:** the `officecli` binary must be on `PATH`. The doctor reports the resolved path and the version.
- **LibreOffice:** the `libreoffice` binary must be on `PATH` (macOS/Linux) or installed at the standard Windows path. The doctor reports the resolved path and the version.
- **Tesseract:** the `tesseract` binary must be on `PATH`. The doctor reports the resolved path, version, and installed language codes.
- **`readpst`:** the `readpst` binary must be on `PATH`. The doctor reports the resolved path.
- **`uv`:** used by the project itself, not optional. The doctor reports the version.

If a tool is reported as missing even though you have installed it, the most common reason is that the install location is not on your `PATH`. The doctor will show the path it is checking; either add that path to `PATH` or move the binary to a directory that is already on `PATH`.

## Lockfile and reproducibility

The lockfile (`uv.lock`) is the authoritative record of headcleaner's dependencies. Every implementation environment must use:

```bash
unset PYTHONPATH
uv sync --locked --python 3.13
uv run --no-sync --python 3.13 pytest -rs --no-header
```

The `--locked` flag tells `uv` to refuse any deviation from the lockfile. If the lockfile drifts from the project's intended dependency set, `uv` exits non-zero with a clear message. The fix is to pull the latest changes from the project and re-run, not to relax the lockfile constraint.

The `--no-sync` flag tells `uv run` not to check the lockfile before each command. This is important because it makes test runs deterministic and fast.

## Known limitations

These are the limitations headcleaner acknowledges as of this writing. Each one has either a workaround or a planned resolution.

- **OCR is slow.** Running Tesseract on a scanned PDF takes seconds per page. For a large corpus, the OCR step may take hours. The `fast` profile trades accuracy for speed; the `archival` profile trades speed for accuracy.
- **Embedding providers are explicit.** Headcleaner does not download embedding models implicitly. You must point it at a local model path or configure an HTTP provider.
- **Qdrant is the only supported remote vector database.** Other vector databases are not supported. Adding support for another database requires writing an adapter; the [embeddings and vectors developer guide](../developer/embeddings-and-vectors.md) describes the adapter contract.
- **Redacted indexing is delivered as a parallel derivative, not in-place mutation.** Phase 3 Contract 3.3 implements `headcleaner redact BUNDLE --write-derivative` which writes a separate `<bundle>/_redacted/` derivative that links back to canonical concepts. The canonical bundle is never mutated, and a downstream index can consume the derivative. In-place redaction rewriting of canonical output is explicitly out of scope.

## Phase 3 dependencies

Phase 3 adds one Python dependency: `in-toto==3.1.0`, used by the `attest --in-toto` path to wrap the canonical statement in a DSSE envelope. It transitively pulls `securesystemslib`, `iso8601`, `pathspec`, and `python-dateutil`. The lockfile is the authoritative source; if `uv lock --check` fails, the right move is to pull and re-sync, not to relax the constraint.

## Phase 3 CLI compatibility

- `headcleaner attest` (Contract 3.5) — adds `--key`, `--in-toto`, `--verify`, `--public-key`. The legacy `--private-key` is retained as a deprecated alias.
- `headcleaner verify` — retained as a backwards-compatible alias for `headcleaner attest --verify`.

No Phase 1 or Phase 2 command was renamed or had its exit-code semantics changed.

## Where to read next

The [installation guide](../getting-started/installation.md) covers the platform-specific install steps. The [engine directory](engine-directory.md) documents the per-engine behavior and which optional tools each engine needs. The [contributor onboarding developer guide](../developer/contributor-onboarding.md) covers platform-specific issues that contributors hit.