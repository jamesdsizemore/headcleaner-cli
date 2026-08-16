"""Git-backed bundle (Eng #32) — auto-commit after a successful convert.

After `headcleaner convert --git-commit [MSG]`, the CLI:
  1. Runs the normal pipeline.
  2. If exit 0, runs `git add <output_root> && git commit -m MSG`
     (in a subprocess; the repo root is the closest enclosing .git).

Safe defaults:
  - Skips if the output dir is not inside a git repo
  - Skips if there are no changes to commit
  - Uses `--no-verify` to skip pre-commit hooks (you may want hooks to
    run; configure via `--git-commit-verify`)
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def find_repo_root(start: Path) -> Path | None:
    """Walk up from `start` looking for a `.git` dir or file. None if not found."""
    cur = start.resolve()
    for parent in [cur, *cur.parents]:
        if (parent / ".git").exists():
            return parent
    return None


def git_commit(
    output_root: Path,
    *,
    message: str = "headcleaner: convert run",
    verify: bool = False,
) -> tuple[int, str]:
    """Stage and commit everything under `output_root` inside its git repo.

    Returns (exit_code, stderr/stdout combined). 0 = success.
    """
    if not shutil.which("git"):
        return 1, "git not found on PATH"

    repo = find_repo_root(output_root)
    if repo is None:
        return 2, f"output dir {output_root} is not inside a git repo"

    try:
        rel = output_root.resolve().relative_to(repo).as_posix() or "."
    except ValueError:
        return 2, f"output dir {output_root} is not inside {repo}"

    # Stage
    add_cmd = ["git", "-C", str(repo), "add", "--", rel]
    r = subprocess.run(add_cmd, capture_output=True, text=True)
    if r.returncode != 0:
        return r.returncode, f"git add failed: {r.stderr}"

    # Check if there's anything to commit
    diff_cmd = ["git", "-C", str(repo), "diff", "--cached", "--quiet"]
    d = subprocess.run(diff_cmd, capture_output=True, text=True)
    if d.returncode == 0:
        # No staged changes
        return 0, "no changes to commit"

    # Commit
    commit_cmd = ["git", "-C", str(repo), "commit"]
    if not verify:
        commit_cmd.append("--no-verify")
    commit_cmd += ["-m", message]
    c = subprocess.run(commit_cmd, capture_output=True, text=True)
    if c.returncode != 0:
        return c.returncode, f"git commit failed: {c.stderr}"

    sha_cmd = ["git", "-C", str(repo), "rev-parse", "HEAD"]
    s = subprocess.run(sha_cmd, capture_output=True, text=True)
    sha = s.stdout.strip() if s.returncode == 0 else "?"
    return 0, f"committed as {sha[:12]}: {message}"
