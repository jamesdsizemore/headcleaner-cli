#!/usr/bin/env bash
# headcleaner installer for macOS / Linux / WSL
# Usage:   curl -fsSL https://...install.sh | bash
#   or:    bash install.sh [--version X.Y.Z] [--from-source] [--no-officecli]

set -euo pipefail

# ---- Defaults ----
VERSION="${HEADCLEANER_VERSION:-latest}"
FROM_SOURCE=0
INSTALL_OFFICECLI=1
PYTHON_BIN="${PYTHON_BIN:-python3}"

# ---- Parse flags ----
while [ $# -gt 0 ]; do
    case "$1" in
        --version)        VERSION="$2"; shift 2 ;;
        --from-source)    FROM_SOURCE=1; shift ;;
        --no-officecli)   INSTALL_OFFICECLI=0; shift ;;
        --python)         PYTHON_BIN="$2"; shift 2 ;;
        -h|--help)
            cat <<EOF
headcleaner installer

USAGE:
    bash install.sh [OPTIONS]

OPTIONS:
    --version X.Y.Z     Install a specific version (default: latest)
    --from-source       Install from the current directory (no network)
    --no-officecli      Skip the OfficeCLI engine install
    --python <bin>      Use this Python binary (default: python3)
    -h, --help          Show this help

ENV VARS:
    HEADCLEANER_VERSION   Override the version to install
EOF
            exit 0
            ;;
        *) echo "unknown flag: $1" >&2; exit 2 ;;
    esac
done

# ---- Pretty output ----
bold()  { printf "\033[1m%s\033[0m\n" "$*"; }
cyan()  { printf "\033[1;36m%s\033[0m\n" "$*"; }
pink()  { printf "\033[1;35m%s\033[0m\n" "$*"; }
gray()  { printf "\033[90m%s\033[0m\n" "$*"; }
fail()  { printf "\033[1;31mfail:\033[0m %s\n" "$*" >&2; exit 1; }

bold "  ⚡ headcleaner installer"
gray "  ──────────────────────────"

# ---- Check Python ----
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    fail "Python not found. Install Python 3.12+ or pass --python /path/to/python"
fi

PY_VERSION=$("$PYTHON_BIN" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PY_MAJOR=$(echo "$PY_VERSION" | cut -d. -f1)
PY_MINOR=$(echo "$PY_VERSION" | cut -d. -f2)

if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 12 ]; }; then
    fail "Python $PY_VERSION found; headcleaner needs 3.12+"
fi

cyan "  ✓ Python $PY_VERSION"

# ---- Install uv ----
if ! command -v uv >/dev/null 2>&1; then
    gray "  · installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh >/dev/null 2>&1
    # shellcheck disable=SC1091
    if [ -f "$HOME/.local/bin/env" ]; then . "$HOME/.local/bin/env"; fi
    if [ -f "$HOME/.cargo/env" ]; then . "$HOME/.cargo/env"; fi
    export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
fi

if ! command -v uv >/dev/null 2>&1; then
    fail "uv installation failed. Install manually: https://docs.astral.sh/uv/"
fi

cyan "  ✓ uv $(uv --version | awk '{print $2}')"

# ---- Install headcleaner ----
if [ "$FROM_SOURCE" -eq 1 ]; then
    gray "  · installing from source..."
    uv tool install .
else
    if [ "$VERSION" = "latest" ]; then
        gray "  · installing headcleaner (latest)..."
        uv tool install headcleaner
    else
        gray "  · installing headcleaner==$VERSION..."
        uv tool install "headcleaner==$VERSION"
    fi
fi

cyan "  ✓ headcleaner installed"

# ---- Install OfficeCLI ----
if [ "$INSTALL_OFFICECLI" -eq 1 ]; then
    if command -v npm >/dev/null 2>&1; then
        gray "  · installing OfficeCLI engine..."
        if npm install -g @officecli/officecli >/dev/null 2>&1; then
            cyan "  ✓ OfficeCLI installed"
        else
            pink "  ⚠ OfficeCLI install failed — DOCX/XLSX/PPTX files will be skipped"
            pink "    Re-run with:  npm install -g @officecli/officecli"
        fi
    else
        pink "  ⚠ npm not found — OfficeCLI not installed"
        pink "    DOCX/XLSX/PPTX files will be skipped"
        pink "    Install Node.js + npm, then:  npm install -g @officecli/officecli"
    fi
fi

# ---- Verify ----
if command -v headcleaner >/dev/null 2>&1; then
    HC_VERSION=$(headcleaner --version 2>/dev/null || echo "unknown")
    cyan "  ✓ headcleaner $HC_VERSION on PATH"
else
    pink "  ⚠ headcleaner not on PATH yet. Restart your shell or run:"
    pink "    export PATH=\"\$HOME/.local/bin:\$PATH\""
fi

echo
bold "  Installation complete. Try:"
echo "    headcleaner --help"
echo "    headcleaner agents"
echo "    headcleaner convert ./inbox --format both --output ./out"
echo
