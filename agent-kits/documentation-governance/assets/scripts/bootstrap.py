#!/usr/bin/env python3
"""Install the documentation-governance kit into a repository without silent overwrites."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ASSETS = Path(__file__).resolve().parent.parent
TEMPLATES = ASSETS / "templates"


def write_if_absent(destination: Path, content: str, overwrite: bool, skipped: list[Path]) -> None:
    if destination.exists() and not overwrite:
        skipped.append(destination)
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(content, encoding="utf-8")


def copy_if_absent(source: Path, destination: Path, overwrite: bool, skipped: list[Path]) -> None:
    if destination.exists() and not overwrite:
        skipped.append(destination)
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def active_docs(root: Path) -> list[Path]:
    result = [root / "README.md"] if (root / "README.md").is_file() else []
    docs = root / "docs"
    if docs.is_dir():
        result.extend(path for path in docs.rglob("*.md") if "_archive" not in path.parts)
    return sorted(result)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", type=Path, help="existing repository root")
    parser.add_argument("--phase", default="phase-1")
    parser.add_argument("--overwrite", action="store_true", help="replace kit-managed files only")
    parser.add_argument("--append-instructions", action="store_true", help="append fragments to existing AGENTS.md/CLAUDE.md")
    parser.add_argument("--install-hook", action="store_true", help="configure this repository's core.hooksPath")
    args = parser.parse_args(argv)
    root = args.target.resolve()
    if not (root / ".git").exists():
        parser.error("target must be a Git repository")
    skipped: list[Path] = []
    for name in ("BACKLOG.md", "ISSUES.md", "MEMORY.md", "DEVELOPMENT_HISTORY.md", "DEPENDENCIES.md", "PINS.md"):
        copy_if_absent(TEMPLATES / "records" / name, root / name, args.overwrite, skipped)
    for name in ("README.md", "DOCUMENTATION_GOVERNANCE.md"):
        copy_if_absent(TEMPLATES / "development" / name, root / "docs/development" / name, args.overwrite, skipped)
    write_if_absent(root / "docs/development/ACTIVE_PHASE", args.phase + "\n", args.overwrite, skipped)
    for source, target in (("verify_docs.py", "scripts/verify_docs.py"), ("install-git-hooks.sh", "scripts/install-git-hooks.sh"), ("pre-commit", ".githooks/pre-commit")):
        copy_if_absent(ASSETS / "scripts" / source, root / target, args.overwrite, skipped)
    gitignore = root / ".gitignore"
    plan_rule = "\n# Local implementation plans; durable working context, never release artifacts.\n.plans/\n"
    existing = gitignore.read_text(encoding="utf-8") if gitignore.exists() else ""
    if ".plans/" not in existing:
        write_if_absent(gitignore, existing.rstrip() + plan_rule, True, skipped)
    for filename in ("AGENTS.md", "CLAUDE.md"):
        fragment = (TEMPLATES / "instructions" / f"{filename}.fragment").read_text(encoding="utf-8")
        target = root / filename
        if not target.exists():
            write_if_absent(target, fragment, False, skipped)
        elif args.append_instructions and "Documentation governance" not in target.read_text(encoding="utf-8"):
            target.write_text(target.read_text(encoding="utf-8").rstrip() + "\n\n" + fragment, encoding="utf-8")
        elif "Documentation governance" not in target.read_text(encoding="utf-8"):
            skipped.append(target)
    audit = root / "docs/development/phase-audits" / f"{args.phase}.json"
    if not audit.exists() or args.overwrite:
        payload = {"schema_version": 1, "phase": args.phase, "status": "in_progress", "documents": [{"path": item.relative_to(root).as_posix(), "disposition": "pending", "evidence": ""} for item in active_docs(root)]}
        audit.parent.mkdir(parents=True, exist_ok=True)
        audit.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    if args.install_hook:
        subprocess.run(["git", "config", "core.hooksPath", ".githooks"], cwd=root, check=True)
    for path in skipped:
        print(f"SKIPPED_EXISTING={path.relative_to(root)}", file=sys.stderr)
    if any(path.name in {"AGENTS.md", "CLAUDE.md"} for path in skipped) and not args.append_instructions:
        print("ERROR: merge instruction fragments or rerun with --append-instructions", file=sys.stderr)
        return 2
    print(f"BOOTSTRAPPED={root}")
    print(f"AUDIT={audit.relative_to(root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
