"""Interactive glob REPL (Eng #44).

When `headcleaner convert --include <glob>` matches zero files, instead
of just printing "0 files matched", launch a Textual mini-REPL that lets
the user refine the glob interactively and see matching files in
real-time.

Usage (planned):
    headcleaner convert IN OUT --include  -> prompts REPL on no-match
    headcleaner glob <DIR>                 -> explicit REPL launch

SKELETON: this stub defines the public API and returns a single glob
match check so headcleaner can call it; full Textual UI lands in v0.6.
"""
from __future__ import annotations

import fnmatch
from pathlib import Path


def count_matches(root: Path, glob: str) -> int:
    """Return the number of files under `root` matching `glob`."""
    if not root.is_dir():
        return 0
    n = 0
    for p in root.rglob("*"):
        if p.is_file() and fnmatch.fnmatch(p.name, glob):
            n += 1
    return n


def launch_repl(root: Path) -> None:
    """Launch the interactive glob REPL.

    SKELETON: prints a hint and exits. The full UI uses Textual's
    Input widget with live file count feedback. Full implementation
    lands in v0.6.
    """
    print(f"[glob-repl] no files matched in {root}")
    print("[glob-repl] try: headcleaner glob <DIR> --inline")
    print("[glob-repl] (interactive Textual UI ships in v0.6)")