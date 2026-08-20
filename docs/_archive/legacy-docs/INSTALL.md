# Install headcleaner

There are several ways to install `headcleaner`. Pick the one that matches
your platform and comfort level.

## TL;DR

```bash
# macOS / Linux / WSL — one line
curl -fsSL https://raw.githubusercontent.com/local/headcleaner-cli/main/install.sh | bash

# Windows PowerShell
irm https://raw.githubusercontent.com/local/headcleaner-cli/main/install.ps1 | iex
```

Both scripts:
1. Check for `python3` (3.12+) and `uv`. Install `uv` if missing.
2. Run `uv tool install headcleaner` (or `pip install headcleaner` as fallback).
3. Verify with `headcleaner --version`.

---

## Option 1 — `uv tool install` (recommended for Python users)

`uv` is Astral's Python package manager. It's fast, isolated, and doesn't
need a virtualenv ceremony for CLI tools.

```bash
# Install uv (if you don't have it)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install headcleaner as a global tool
uv tool install headcleaner

# Verify
headcleaner --version
```

To upgrade later:

```bash
uv tool upgrade headcleaner
```

To uninstall:

```bash
uv tool uninstall headcleaner
```

---

## Option 2 — `pipx install` (alternative for Python users)

`pipx` is similar to `uv tool` but uses `pip` under the hood.

```bash
pipx install headcleaner
```

---

## Option 3 — `pip install --user`

The classic approach. Installs into your user site-packages.

```bash
pip install --user headcleaner
```

Make sure `~/.local/bin` (Linux/macOS) or `%APPDATA%\Python\Scripts`
(Windows) is on your `PATH`.

---

## Option 4 — From source

For contributors and tinkerers.

```bash
git clone https://github.com/local/headcleaner-cli
cd headcleaner-cli
uv sync
uv run headcleaner --help
```

If you want the CLI globally installed from this checkout:

```bash
uv tool install .
```

---

## Option 5 — Homebrew (macOS / Linuxbrew)

```bash
brew install headcleaner
# (Formula PR pending — see ENHANCEMENTS.md #17)
```

---

## Office engine dependency

`headcleaner` shells out to [OfficeCLI](https://github.com/iOfficeAI/OfficeCLI)
for DOCX/XLSX/PPTX conversion. Install it once:

```bash
npm install -g @officecli/officecli
```

Verify:

```bash
officecli --version   # should print 1.0.x or newer
```

If `officecli` is missing, `headcleaner` will skip Office files with a warning
instead of failing. Run `headcleaner agents` to see engine install status.

---

## PDF OCR (optional)

If you want OCR for scanned PDFs, install:

```bash
# Tesseract binary
# macOS
brew install tesseract
# Debian / Ubuntu
sudo apt-get install tesseract-ocr
# Windows (Chocolatey)
choco install tesseract
# Windows (Scoop)
scoop install tesseract

# Python wrapper (uv tool env)
uv tool install --with pytesseract --with Pillow headcleaner
```

Then run with `--ocr`.

---

## Verifying the install

```bash
# Version
headcleaner --version
# 0.1.0

# Help
headcleaner --help

# Engines
headcleaner agents
#   ✓ installed  officecli   Office (DOCX/XLSX/PPTX) — npm i -g @officecli/officecli
#     ✗ missing  tesseract   OCR — choco install tesseract / brew install tesseract
#     ✗ missing  readpst     PST (optional) — install libpst

# Smoke test
mkdir -p /tmp/inbox && echo "hello" > /tmp/inbox/note.txt
headcleaner /tmp/inbox --format both --output /tmp/out
ls /tmp/out
# _md/  manifest.json  okf/
```

---

## Uninstall

```bash
# uv
uv tool uninstall headcleaner

# pipx
pipx uninstall headcleaner

# pip
pip uninstall headcleaner
```

---

## Troubleshooting

**`headcleaner: command not found`** after install — your shell hasn't reloaded
`PATH`. On Linux/macOS run `hash -r` or open a new terminal. On Windows, open
a new PowerShell window.

**`uv: command not found`** — install uv first (see Option 1).

**`ModuleNotFoundError: No module named 'headcleaner'`** after `pip install` —
`pip` installed into a different Python than your `headcleaner` script uses.
Use `python -m headcleaner` to invoke it explicitly, or install with `uv`/`pipx`
which manage the venv for you.

**Office files silently skipped** — `officecli` is not on PATH. Install it:
`npm install -g @officecli/officecli`. Run `headcleaner agents` to verify.
