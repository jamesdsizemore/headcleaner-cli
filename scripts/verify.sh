#!/usr/bin/env bash
# headcleaner verify — sanity-check the install.
# Runs after install.sh / install.ps1 to confirm everything works end-to-end.
#
# Usage:
#     bash scripts/verify.sh
#     bash scripts/verify.sh --strict   # exit 1 on any warning

set -euo pipefail

STRICT=0
while [ $# -gt 0 ]; do
    case "$1" in
        --strict) STRICT=1; shift ;;
        *) echo "unknown flag: $1" >&2; exit 2 ;;
    esac
done

bold()  { printf "\033[1m%s\033[0m\n" "$*"; }
cyan()  { printf "\033[1;36m%s\033[0m\n" "$*"; }
pink()  { printf "\033[1;35m%s\033[0m\n" "$*"; }
gray()  { printf "\033[90m%s\033[0m\n" "$*"; }
fail()  { printf "\033[1;31mfail:\033[0m %s\n" "$*" >&2; exit 1; }

FAILURES=0
WARNINGS=0

bold "  ⚡ headcleaner verify"
gray "  ────────────────────"

# 1. headcleaner on PATH
if command -v headcleaner >/dev/null 2>&1; then
    cyan "  ✓ headcleaner on PATH"
    HC_VERSION=$(headcleaner --version 2>/dev/null || echo "unknown")
    gray "    version: $HC_VERSION"
else
    fail "headcleaner not on PATH"
fi

# 2. OfficeCLI
if command -v officecli >/dev/null 2>&1; then
    OC_VERSION=$(officecli --version 2>/dev/null || echo "unknown")
    cyan "  ✓ officecli on PATH (version $OC_VERSION)"
else
    pink "  ⚠ officecli not on PATH — DOCX/XLSX/PPTX files will be skipped"
    WARNINGS=$((WARNINGS + 1))
fi

# 3. Convert smoke test (in-memory, no files written)
TMPDIR=$(mktemp -d)
mkdir -p "$TMPDIR/inbox"
echo "hello world" > "$TMPDIR/inbox/note.txt"
echo "# Hello" > "$TMPDIR/inbox/page.md"

gray "  · running smoke convert on $TMPDIR/inbox..."
if headcleaner convert --no-tui "$TMPDIR/inbox" --format both --output "$TMPDIR/out" >/dev/null 2>&1; then
    cyan "  ✓ convert smoke test passed"
    MD_FILES=$(find "$TMPDIR/out/_md" -name "*.md" 2>/dev/null | wc -l)
    OKF_FILES=$(find "$TMPDIR/out/okf" -name "*.md" ! -name "index.md" 2>/dev/null | wc -l)
    gray "    produced $MD_FILES MD files + $OKF_FILES OKF concepts"
else
    fail "convert smoke test failed"
fi

# 4. Linter smoke test
if headcleaner lint "$TMPDIR/out" --no-color >/dev/null 2>&1; then
    cyan "  ✓ linter smoke test passed"
else
    pink "  ⚠ linter found issues in smoke output"
    WARNINGS=$((WARNINGS + 1))
fi

# 5. Templates subcommand
if headcleaner templates 2>&1 | grep -q "\.docx"; then
    cyan "  ✓ templates lists .docx"
else
    fail "templates subcommand broken"
fi

# 6. Agents subcommand
if headcleaner agents 2>&1 | grep -q "officecli"; then
    cyan "  ✓ agents reports officecli status"
else
    fail "agents subcommand broken"
fi

# 7. Python version
PY_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || echo "missing")
if [ "$PY_VERSION" != "missing" ]; then
    gray "  · Python $PY_VERSION"
fi

# Cleanup
rm -rf "$TMPDIR"

echo
if [ "$FAILURES" -gt 0 ]; then
    pink "  ✗ $FAILURES failure(s), $WARNINGS warning(s)"
    exit 1
fi
if [ "$WARNINGS" -gt 0 ] && [ "$STRICT" -eq 1 ]; then
    pink "  ⚠ $WARNINGS warning(s) — --strict mode failing"
    exit 1
fi
bold "  ✓ All checks passed"
echo
