# Troubleshooting

Step-by-step fixes for the common errors you'll hit. If your error isn't
here, see `docs/FAQ.md` or open an issue.

## "officecli: command not found"

`officecli` is the binary that handles DOCX/XLSX/PPTX. It installs
via npm:

```bash
npm install -g @officecli/officecli
officecli --version   # should print 1.0.x or newer
```

If npm is missing:
- macOS: `brew install node`
- Debian/Ubuntu: `sudo apt install nodejs npm`
- Windows: install Node.js from nodejs.org or `winget install OpenJS.NodeJS`

After install, restart your shell so `PATH` updates.

## "LibreOffice is required to convert .doc/.xls/.ppt"

Legacy Office formats are converted automatically through LibreOffice before
HeadCleaner sends their DOCX/XLSX/PPTX result to the configured modern Office
engine. Install LibreOffice and make `soffice` or `libreoffice` discoverable on
`PATH`; then rerun the original command. `headcleaner doctor` reports the
modern engine status. If conversion fails, HeadCleaner includes LibreOffice's
stderr in its error message.

## "readpst" is missing or PST output has metadata only

Full PST body and attachment extraction requires `readpst`. Install the native
backend and rerun:

```bash
# Debian / Ubuntu
sudo apt install pst-utils

# macOS
brew install libpst

# Windows: from an MSYS2 UCRT64 shell
pacman -S mingw-w64-ucrt-x86_64-libpst
```

On Windows, `C:\\msys64\\ucrt64\\bin\\readpst.exe` is discovered automatically.
For a nonstandard install, set `HEADCLEANER_READPST` to the full executable
path before invoking HeadCleaner. Without it, the optional libpff fallback can
only produce metadata summaries; `headcleaner doctor` reports this as a warning.

## "officecli timed out after 60s"

Some very large Office files (200+ page PowerPoint decks, 50MB+ Excel
workbooks) can take longer than the default 60s timeout. The timeout is
configurable via:

```bash
# v0.2 — not yet exposed via CLI; patch src/headcleaner/engines/officecli.py
# for now. Tracked in ENHANCEMENTS.md #14.
```

## "Cannot find file specified" when running OfficeCLI on Windows

If `officecli` works at the shell but headcleaner fails with this error,
it's likely a `.cmd` wrapper issue. Headcleaner detects Windows `.cmd`
shims automatically and uses `shell=True`. If you're running headcleaner
from a non-interactive context (CI, task scheduler) where the shell may
not be initialized, run from PowerShell or cmd.exe directly.

## PDF has no extractable text

Your PDF is image-only (a scan, or an exported-as-images PDF). Use OCR:

```bash
headcleaner file.pdf --ocr --output out
```

Requires:
- Tesseract on PATH (`brew install tesseract`, `choco install tesseract`)
- `pytesseract` in the Python env (install with `uv tool install --with pytesseract headcleaner`)

## "PDF is encrypted"

`pdfplumber` can't open encrypted PDFs in v0.1. Decrypt with qpdf first:

```bash
qpdf --decrypt encrypted.pdf decrypted.pdf
headcleaner decrypted.pdf --output out
```

Tracked in ENHANCEMENTS.md #13.

## "no adapter" warnings

A file has an extension headcleaner doesn't recognize. Check
`headcleaner templates` for the supported list. To extend, see
`docs/CONTRIBUTING.md` → "Adding a new file format".

## Linter says "okf/type-required"

Every OKF concept MUST have a `type` field (OKF v0.2 §4.1). If you hand-
authored a concept without one, the linter will flag it. Fix:

```yaml
---
type: Document    # ← add this
title: ...
---
```

## Linter says "okf/sources-sha256: not a valid SHA-256 hex string"

The `sources[].sha256` value must be a 64-character lowercase hex string.
If you copy/pasted it truncated, fix it. If you don't have a SHA-256,
compute one:

```bash
sha256sum file.pdf
# 8c2f5d6e9a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d
```

## Linter says "md/code-fence-orphan: N fences found; odd count"

A markdown file has an unclosed ``` code fence. Open the file in any
editor and look for ``` lines. They should come in pairs.

## Hidden files skipped

`headcleaner` ignores files starting with `.` (dotfiles). This is
intentional — `.git/`, `.DS_Store`, etc. should not be converted.

To convert a file that happens to start with a dot, rename it.

## Output dir already has files

By default, headcleaner overwrites existing files in the output dir.
This is intentional — running headcleaner twice on the same input
produces the same output.

If you want to preserve the old output, use a different `--output`
directory or back up manually before re-running.

## Permission denied on output

`headcleaner` will fail with a clear error if it can't write to the
output directory. Check:
- The directory exists (or its parent does — headcleaner will
  `mkdir -p` for you, but only if the parent is writable)
- You have write permission
- The disk isn't full

## "ModuleNotFoundError: No module named 'pytesseract'" with --ocr

`pytesseract` is in the optional `ocr` extra. Install with:

```bash
uv tool install --with pytesseract --with Pillow headcleaner
```

## headcleaner command not found after install

Your shell hasn't reloaded PATH. Try:
- `hash -r` (bash/zsh)
- Open a new terminal
- `rehash` (fish)

On Windows, open a new PowerShell window.

## uv: command not found

Install uv: `curl -LsSf https://astral.sh/uv/install.sh | sh` (Unix) or
`irm https://astral.sh/uv/install.ps1 | iex` (Windows).

## Tests fail on a fresh checkout

```bash
# Most common cause: missing officecli
npm install -g @officecli/officecli

# Other causes
uv sync               # reinstall deps
uv run pytest -v      # verbose output
```

If `test_officecli_adapter_*` tests fail with "officecli binary not
installed" — that's the pytest.skip() doing its job. Not a real failure.

## CI says "OfficeCLI installation failed"

The CI workflow installs OfficeCLI via npm. If npm is missing in the
runner image, the install step fails. Open `.github/workflows/test.yml`
and add a `setup-node` step before the `npm install` step.

## I want to debug a single file

```bash
headcleaner convert . --include "*.docx" --no-tui --output out
# Look at out/_md/sample.docx.md and out/okf/sample.md
```

If the output is wrong, file an issue with:
- The input file (or a redacted version)
- The exact headcleaner command
- The expected vs. actual output
