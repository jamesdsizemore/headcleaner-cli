# Installation

This page walks you through installing headcleaner on Windows, macOS, and Linux. It is written for someone who has never installed a Python command-line tool before, so every term is explained in plain English before it is used. If you already have `uv` and a working Python environment, you can skip to the [three-line install](#the-three-line-install) at the bottom.

## What you need before you start

Headcleaner is a Python application, which means it runs on top of a Python interpreter. You do not need to understand Python to use headcleaner, but you do need a working Python installation. There are two clean ways to get one: install Python directly, or use a small tool called `uv` that handles Python installation for you.

`uv` is a Python package manager written in Rust. It is fast, it manages its own Python versions, and it installs headcleaner and its dependencies into an isolated environment so nothing on your system gets clobbered. Headcleaner's official installation path uses `uv` because it produces reproducible results across Windows, macOS, and Linux without you having to wrestle with system Python.

If you already have Python 3.12 or 3.13 installed on your machine and you are comfortable using `pip` directly, headcleaner also installs through `pip`. The `uv` path is recommended because it does the same thing with fewer steps and fewer ways for things to go wrong.

## Installing uv

The single command below installs `uv` on any platform. It does not require administrator privileges.

### On macOS or Linux

Open a terminal and run:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

The installer writes `uv` into `~/.local/bin` and prints a one-line message telling you to either restart your terminal or add that directory to your `PATH`. If you are using a fresh terminal session, you can confirm the install worked by running `uv --version`.

### On Windows

Open PowerShell and run:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

The installer puts `uv` into `%USERPROFILE%\.local\bin` and prints a message about adding it to your `PATH`. After the installer finishes, close the current PowerShell window and open a new one so the updated `PATH` takes effect. Confirm with `uv --version`.

If you are using Git Bash on Windows, the macOS/Linux command works the same way.

## The three-line install

Once `uv` is installed, headcleaner takes three commands. They work identically on every supported platform.

### Step 1 — Clone or download the headcleaner source

If you want the development version with the latest changes:

```bash
git clone https://github.com/your-org/headcleaner-cli.git
cd headcleaner-cli
```

If you have a packaged wheel from your team, navigate to the folder that contains it instead.

### Step 2 — Install headcleaner and its dependencies

From inside the headcleaner folder, run:

```bash
uv sync --locked --python 3.13
```

This command downloads Python 3.13 if you do not already have it, creates an isolated virtual environment in `.venv/`, and installs every package headcleaner needs at the exact versions tested by the maintainers. The `--locked` flag tells `uv` to fail loudly if the lockfile drifts from what the project intends; this is a safety feature, not a bug.

### Step 3 — Verify the install

```bash
uv run --no-sync --python 3.13 headcleaner --help
```

You should see a list of headcleaner's commands. If you do, the install worked. If you get an error about Python not being found or about a missing module, jump to the [troubleshooting section](#something-went-wrong) below.

## Optional tools that make headcleaner more useful

Headcleaner ships with a sensible set of built-in converters, but some file formats need external helpers. These helpers are **optional** — headcleaner tells you when they are missing rather than trying to install them for you. This section lists what is available and how to install each one. Skip any that do not apply to the documents you care about.

### OfficeCLI for Word, Excel, and PowerPoint

OfficeCLI is a single binary that headcleaner uses to extract structured content from `.docx`, `.xlsx`, and `.pptx` files. Install it from npm:

```bash
npm install -g @officecli/officecli
```

Confirm with `officecli --version`. Headcleaner checks for OfficeCLI at startup and tells you if it is missing when you try to convert an Office document.

### LibreOffice for legacy Office formats

If you need to convert `.doc`, `.xls`, or `.ppt` files (the older Office formats that predate the XML-based ones), headcleaner uses LibreOffice headless to upgrade them first. Install LibreOffice from [libreoffice.org](https://www.libreoffice.org/) or through your operating system's package manager. On macOS with Homebrew: `brew install --cask libreoffice`. On Ubuntu: `sudo apt install libreoffice`. On Windows: download the installer from the LibreOffice site.

### Tesseract for scanned PDFs and image-only documents

If you have scanned PDFs or image-only documents that contain no embedded text, headcleaner can run optical character recognition through Tesseract. Install Tesseract from [github.com/tesseract-ocr/tesseract](https://github.com/tesseract-ocr/tesseract) or through your package manager. On macOS with Homebrew: `brew install tesseract`. On Ubuntu: `sudo apt install tesseract-ocr`. On Windows: download the installer from the Tesseract releases page.

### Sentence Transformers and a vector database (only if you want semantic search)

If you want headcleaner to embed your chunks and search them by meaning instead of just by keyword, you need the Sentence Transformers library (already installed by `uv sync`) and a model file on disk. Headcleaner never downloads a model on its own — you point it at a local model path explicitly. See the [Embeddings and vectors developer guide](docs/developer/embeddings-and-vectors.md) for the configuration steps.

If you want to store those embeddings in a remote vector database instead of locally, headcleaner can talk to Qdrant. That connection is configured per-run with `--qdrant-endpoint` and is **off by default**. See the [Embeddings and vectors developer guide](docs/developer/embeddings-and-vectors.md) for the configuration steps.

## Verifying your installation

Run the built-in diagnostic command to confirm headcleaner can see its environment:

```bash
uv run --no-sync --python 3.13 headcleaner doctor
```

The doctor command prints a checklist of the tools it can find — Python version, `uv`, OfficeCLI if you installed it, LibreOffice if you installed it, Tesseract if you installed it — and ends with a `GO` or `NO-GO` verdict. A `NO-GO` does not mean headcleaner is broken; it usually means an optional tool is missing for a file format you do not need.

## Something went wrong

If `uv sync` fails with a Python version error, confirm that you passed `--python 3.13` exactly. Headcleaner requires Python 3.12 or 3.13 and the lockfile is built against 3.13.

If `headcleaner` is not found after installation, your shell's `PATH` is not picking up the `uv`-managed virtual environment. The reliable fix is to always invoke headcleaner through `uv run --no-sync --python 3.13 headcleaner …` rather than expecting `headcleaner` to be on your `PATH` directly.

If a specific conversion fails with "engine not found" or "required tool unavailable," the relevant optional tool is missing. Re-run `headcleaner doctor` to see which one and consult [the optional tools section](#optional-tools-that-make-headcleaner-more-useful) above.

For deeper troubleshooting, see the [user troubleshooting guide](docs/user-guide/troubleshooting.md). For Windows-specific environment issues, see the [contributor onboarding guide](docs/developer/contributor-onboarding.md).