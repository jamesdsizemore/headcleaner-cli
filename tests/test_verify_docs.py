from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "scripts" / "verify_docs.py"
HOOK = Path(__file__).parents[1] / ".githooks" / "pre-commit"
HOOK_INSTALLER = Path(__file__).parents[1] / "scripts" / "install-git-hooks.sh"


def _write_audit(root: Path, entries: dict[str, str], *, status: str = "complete") -> None:
    audit_dir = root / "docs" / "development" / "phase-audits"
    audit_dir.mkdir(parents=True, exist_ok=True)
    (audit_dir / "phase-test.json").write_text(
        json.dumps(
            {
                "phase": "phase-test",
                "status": status,
                "entries": [
                    {
                        "path": path,
                        "disposition": "reviewed",
                        "evidence": evidence,
                    }
                    for path, evidence in sorted(entries.items())
                ],
            }
        ),
        encoding="utf-8",
    )


def _project(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    (root / "docs" / "development").mkdir(parents=True)
    (root / "README.md").write_text("[guide](docs/guide.md#introduction)\n", encoding="utf-8")
    (root / "docs" / "guide.md").write_text("# Introduction\n", encoding="utf-8")
    (root / "docs" / "development" / "ACTIVE_PHASE.md").write_text("phase-test\n", encoding="utf-8")
    _write_audit(
        root,
        {
            "README.md": "Root readme reviewed.",
            "docs/development/ACTIVE_PHASE.md": "Active phase record reviewed.",
            "docs/guide.md": "Guide reviewed.",
        },
    )
    return root


def _run(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(root), *args],
        check=False,
        capture_output=True,
        text=True,
    )


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )


def _hooked_project(tmp_path: Path) -> Path:
    root = _project(tmp_path)
    (root / "pyproject.toml").write_text(
        "[project]\nname = 'hook-test'\nversion = '0.0.0'\nrequires-python = '>=3.13'\n",
        encoding="utf-8",
    )
    (root / "DEVELOPMENT_HISTORY.md").write_text("# Development history\n", encoding="utf-8")
    (root / "scripts").mkdir()
    (root / ".githooks").mkdir()
    shutil.copy2(SCRIPT, root / "scripts" / "verify_docs.py")
    shutil.copy2(HOOK, root / ".githooks" / "pre-commit")
    shutil.copy2(HOOK_INSTALLER, root / "scripts" / "install-git-hooks.sh")

    assert _git(root, "init").returncode == 0
    assert _git(root, "config", "user.email", "tests@example.invalid").returncode == 0
    assert _git(root, "config", "user.name", "Hook Test").returncode == 0
    installer = subprocess.run(
        ["sh", "scripts/install-git-hooks.sh"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    assert installer.returncode == 0, installer.stdout + installer.stderr
    return root


def test_verify_docs_accepts_complete_audit_and_valid_anchor(tmp_path: Path) -> None:
    result = _run(_project(tmp_path), "--phase", "phase-test")

    assert result.returncode == 0, result.stdout + result.stderr
    assert "ACTIVE_DOCS=3" in result.stdout
    assert "DOCUMENTATION_AUDIT=complete" in result.stdout


def test_verify_docs_rejects_missing_anchor(tmp_path: Path) -> None:
    root = _project(tmp_path)
    (root / "README.md").write_text("[guide](docs/guide.md#missing)\n", encoding="utf-8")

    result = _run(root, "--phase", "phase-test")

    assert result.returncode == 1
    assert "missing anchor" in result.stdout


def test_verify_docs_rejects_incomplete_audit_coverage(tmp_path: Path) -> None:
    root = _project(tmp_path)
    _write_audit(root, {"README.md": "Only the root was reviewed."})

    result = _run(root, "--phase", "phase-test")

    assert result.returncode == 1
    assert "audit coverage missing: docs/guide.md" in result.stdout


def test_verify_docs_writes_a_complete_inventory_template(tmp_path: Path) -> None:
    root = _project(tmp_path)

    result = _run(root, "--write-audit-template", "phase-next")

    assert result.returncode == 0, result.stdout + result.stderr
    audit = json.loads(
        (root / "docs" / "development" / "phase-audits" / "phase-next.json").read_text(
            encoding="utf-8"
        )
    )
    assert audit["phase"] == "phase-next"
    assert audit["status"] == "in_progress"
    assert {entry["path"] for entry in audit["entries"]} == {
        "README.md",
        "docs/development/ACTIVE_PHASE.md",
        "docs/guide.md",
    }
    assert {entry["disposition"] for entry in audit["entries"]} == {"pending"}


def test_installed_hook_rejects_commit_missing_development_history(tmp_path: Path) -> None:
    root = _hooked_project(tmp_path)
    assert (
        _git(root, "add", "README.md", "docs", "scripts", ".githooks", "pyproject.toml").returncode
        == 0
    )

    result = _git(root, "commit", "-m", "test hook rejection")

    assert result.returncode != 0
    assert "DEVELOPMENT_HISTORY.md" in result.stdout + result.stderr


def test_installed_hook_allows_commit_with_complete_required_records(tmp_path: Path) -> None:
    root = _hooked_project(tmp_path)
    assert _git(root, "add", ".").returncode == 0

    result = _git(root, "commit", "-m", "test hook acceptance")

    assert result.returncode == 0, result.stdout + result.stderr
