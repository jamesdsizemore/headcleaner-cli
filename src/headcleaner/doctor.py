"""Diagnostic checks for headcleaner.

`headcleaner doctor` answers the question "why isn't this working?" in one
go. Each check returns a `CheckResult` with a status (ok / warn / fail),
a short label, and a human-readable detail line. The CLI prints a plain-text
table and exits non-zero if any required check is `fail`.

Checks performed:

1. Python version      (must be >= 3.12 for headcleaner)
2. PATH environment    (must be present and non-empty)
3. OfficeCLI on PATH   (required for DOCX/XLSX/PPTX)
4. Tesseract on PATH   (optional, for `--ocr`)
5. readpst / libpst    (optional, for PST extraction)
6. Output directory    (writable; create if missing)
7. Registry file       (parses as TOML; `$HEADCLEANER_REGISTRY` honored)
8. Loaded bundles      (informational MCP-server state hint)
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
import tomllib
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

# ---------------------------------------------------------------------------
# CheckResult
# ---------------------------------------------------------------------------

STATUS_OK = "ok"
STATUS_WARN = "warn"
STATUS_FAIL = "fail"


@dataclass
class CheckResult:
    name: str
    status: str  # one of STATUS_OK / STATUS_WARN / STATUS_FAIL
    detail: str
    fix: str | None = None  # optional one-line remediation hint


def _run_check(name: str, fn: Callable[[], CheckResult]) -> CheckResult:
    """Run a check, wrapping any exception as a fail."""
    try:
        return fn()
    except Exception as e:
        return CheckResult(name=name, status=STATUS_FAIL, detail=f"{type(e).__name__}: {e}")


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------

MIN_PY = (3, 12)


def check_python() -> CheckResult:
    v = sys.version_info
    if (v.major, v.minor) >= MIN_PY:
        return CheckResult(
            name="python-version",
            status=STATUS_OK,
            detail=f"Python {v.major}.{v.minor}.{v.micro}",
        )
    return CheckResult(
        name="python-version",
        status=STATUS_FAIL,
        detail=f"Python {v.major}.{v.minor}.{v.micro} (need >= {'.'.join(map(str, MIN_PY))})",
        fix="Install Python 3.12+ and use `uv python install 3.12`.",
    )


def check_path() -> CheckResult:
    """Verify that command discovery has a usable PATH environment."""
    raw = os.environ.get("PATH", "")
    entries = [entry for entry in raw.split(os.pathsep) if entry]
    if entries:
        return CheckResult(
            name="path",
            status=STATUS_OK,
            detail=f"PATH has {len(entries)} non-empty entries",
        )
    return CheckResult(
        name="path",
        status=STATUS_FAIL,
        detail="PATH is missing or empty",
        fix="Set PATH so headcleaner can discover OfficeCLI and optional engines.",
    )


def check_officecli() -> CheckResult:
    """OfficeCLI is shipped via npm and required for Office formats."""
    path = shutil.which("officecli")
    if path:
        return CheckResult(
            name="officecli",
            status=STATUS_OK,
            detail=f"installed at {path}",
        )
    return CheckResult(
        name="officecli",
        status=STATUS_FAIL,
        detail="not found on PATH",
        fix="npm i -g @officecli/officecli (https://github.com/iOfficeAI/OfficeCLI)",
    )


def check_tesseract() -> CheckResult:
    path = shutil.which("tesseract")
    if path:
        return CheckResult(
            name="tesseract",
            status=STATUS_OK,
            detail=f"installed at {path}",
        )
    return CheckResult(
        name="tesseract",
        status=STATUS_WARN,
        detail="not found on PATH (optional — needed for `--ocr`)",
        fix="choco install tesseract  /  brew install tesseract",
    )


def check_readpst() -> CheckResult:
    # readpst is the CLI tool that libpff-python wraps; detecting the lib
    # is sufficient for our purposes (the Python lib is already optional).
    path = shutil.which("readpst")
    if path:
        return CheckResult(
            name="readpst",
            status=STATUS_OK,
            detail=f"installed at {path}",
        )
    return CheckResult(
        name="readpst",
        status=STATUS_WARN,
        detail="not found on PATH (optional — needed for PST extraction)",
        fix="choco install libpst  /  brew install libpst",
    )


def check_output_dir(path: Path | None) -> CheckResult:
    """Verify the output directory is writable (or create a temp one)."""
    target = path or Path(tempfile.gettempdir()) / "headcleaner-doctor-test"
    try:
        target.mkdir(parents=True, exist_ok=True)
        # Try to write and remove a probe file
        probe = target / ".headcleaner-doctor-probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
    except PermissionError as e:
        return CheckResult(
            name="output-dir",
            status=STATUS_FAIL,
            detail=f"not writable: {target} ({e})",
            fix="chmod +w the directory, or pass --output-dir to a writable path.",
        )
    except OSError as e:
        return CheckResult(
            name="output-dir",
            status=STATUS_FAIL,
            detail=f"cannot create {target}: {e}",
        )
    return CheckResult(
        name="output-dir",
        status=STATUS_OK,
        detail=f"writable: {target}",
    )


def check_registry() -> CheckResult:
    """Validate the @slug registry TOML file (or report absence)."""
    from . import registry as _reg

    rp = _reg.registry_path()
    if not rp.exists():
        return CheckResult(
            name="registry",
            status=STATUS_OK,
            detail=f"no registry at {rp} (ok — `@slug` references will be ignored)",
        )
    try:
        data = tomllib.loads(rp.read_text(encoding="utf-8"))
        bundles = data.get("bundles", {})
        if not isinstance(bundles, dict):
            return CheckResult(
                name="registry",
                status=STATUS_FAIL,
                detail="the TOML [bundles] value must be a table",
                fix="Replace it with a [bundles] table of slug = path entries.",
            )
        # Sanity check: every value is a string path
        bad = [s for s, p in bundles.items() if not isinstance(p, str)]
        if bad:
            return CheckResult(
                name="registry",
                status=STATUS_FAIL,
                detail=f"{len(bad)} slug(s) with non-string paths: {bad[:3]}",
            )
        return CheckResult(
            name="registry",
            status=STATUS_OK,
            detail=f"{len(bundles)} slug(s) at {rp}",
        )
    except tomllib.TOMLDecodeError as e:
        return CheckResult(
            name="registry",
            status=STATUS_FAIL,
            detail=f"{rp} is not valid TOML: {e}",
            fix="Fix or delete the registry file, or override with $HEADCLEANER_REGISTRY.",
        )


def check_loaded_bundles() -> CheckResult:
    """If the MCP registry has bundles loaded, list them (informational)."""
    # This check is informational only. We don't have access to the MCP
    # registry from this CLI invocation (the MCP server has its own state).
    # Report based on env var presence to give a hint.
    if os.environ.get("HEADCLEANER_MCP_LOADED"):
        return CheckResult(
            name="loaded-bundles",
            status=STATUS_OK,
            detail=os.environ["HEADCLEANER_MCP_LOADED"],
        )
    return CheckResult(
        name="loaded-bundles",
        status=STATUS_OK,
        detail="(no MCP server in this process; run `headcleaner mcp` separately)",
    )


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

ALL_CHECKS: list[tuple[str, Callable[[], CheckResult]]] = [
    ("Python version", check_python),
    ("PATH environment", check_path),
    ("OfficeCLI on PATH", check_officecli),
    ("Tesseract on PATH", check_tesseract),
    ("readpst on PATH", check_readpst),
    ("Output directory", check_output_dir),
    ("Bundle registry", check_registry),
    ("Loaded bundles", check_loaded_bundles),
]


def run_all(output_dir: Path | None = None) -> list[CheckResult]:
    """Run every check. `output_dir` is passed through to check_output_dir."""
    results: list[CheckResult] = []
    for label, fn in ALL_CHECKS:
        if fn is check_output_dir:
            r = _run_check(label, lambda fn=fn: fn(output_dir))
        else:
            r = _run_check(label, fn)
        results.append(r)
    return results


def render_text(results: list[CheckResult]) -> str:
    """Plain-text rendering (CI/SSH safe; no ANSI)."""
    status_glyph = {
        STATUS_OK: "[OK]",
        STATUS_WARN: "[WARN]",
        STATUS_FAIL: "[FAIL]",
    }
    lines = ["headcleaner doctor", "=" * 40]
    for r in results:
        glyph = status_glyph.get(r.status, "[????]")
        lines.append(f"  {glyph:6} {r.name:24}  {r.detail}")
        if r.fix and r.status != STATUS_OK:
            lines.append(f"         {'fix:':24}  {r.fix}")
    fails = sum(1 for r in results if r.status == STATUS_FAIL)
    warns = sum(1 for r in results if r.status == STATUS_WARN)
    lines.append("")
    lines.append(f"  {fails} fail(s), {warns} warn(s), {len(results) - fails - warns} ok")
    lines.append(f"  Verdict: {'NO-GO' if fails else 'GO'}")
    return "\n".join(lines)


def exit_code(results: list[CheckResult]) -> int:
    return 1 if any(r.status == STATUS_FAIL for r in results) else 0
