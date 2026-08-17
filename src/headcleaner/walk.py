"""Folder walker — recursive, extension-aware, hidden-file-aware.

Yields SourceFile records the router can dispatch.
"""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SourceFile:
    path: Path
    relpath: Path  # path relative to root
    size_bytes: int
    sha256: str | None = None  # computed lazily by caller if needed


# Directories we always skip — caches, build artifacts, VCS internals.
_SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    "__pycache__",
    "node_modules",
    ".venv",
    "venv",
    ".mypy_cache",
    ".ruff_cache",
    ".pytest_cache",
    ".DS_Store",
}

# Hidden files on Unix (start with '.'). On Windows, files with hidden attribute
# are also skipped via stat — see below.
_SKIP_FILE_PREFIXES = (".",)


def walk(
    root: Path,
    *,
    include_glob: list[str] | None = None,
    exclude_glob: list[str] | None = None,
    skip_root: Path | None = None,
) -> Iterator[SourceFile]:
    """Recursively yield SourceFile records under `root`.

    Args:
        root: directory to walk (must exist and be a directory).
        include_glob: optional list of fnmatch patterns; if given, only files
            whose basename matches AT LEAST ONE pattern are emitted.
        exclude_glob: optional list of fnmatch patterns; any file matching is
            dropped. exclude_glob runs AFTER include_glob.
        skip_root: optional directory (absolute or relative to root); if a
            directory equals this path, its subtree is skipped. Used by
            headcleaner to avoid re-processing its own output.

    Yields:
        SourceFile records.
    """
    import fnmatch

    root = root.resolve()
    if not root.is_dir():
        raise NotADirectoryError(f"{root} is not a directory")

    skip_root_resolved = skip_root.resolve() if skip_root is not None else None

    include_glob = include_glob or []
    exclude_glob = exclude_glob or []

    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        # Skip directories in-place so os.walk doesn't descend
        new_dirnames = []
        for d in dirnames:
            if d in _SKIP_DIRS or d.startswith("."):
                continue
            full_dir = Path(dirpath) / d
            if skip_root_resolved is not None:
                try:
                    if full_dir.resolve() == skip_root_resolved:
                        continue
                except OSError:
                    pass
            new_dirnames.append(d)
        dirnames[:] = new_dirnames

        for name in filenames:
            if name.startswith(_SKIP_FILE_PREFIXES):
                continue
            full = Path(dirpath) / name
            try:
                # Skip Windows hidden files (e.g. Thumbs.db, desktop.ini)
                if hasattr(os, "stat") and os.name == "nt":
                    attrs = os.stat(full).st_file_attributes  # type: ignore[attr-defined]
                    if attrs & 0x2:  # FILE_ATTRIBUTE_HIDDEN
                        continue
            except (OSError, AttributeError):
                pass

            if include_glob and not any(fnmatch.fnmatch(name, p) for p in include_glob):
                continue
            if exclude_glob and any(fnmatch.fnmatch(name, p) for p in exclude_glob):
                continue

            try:
                size = full.stat().st_size
            except OSError:
                continue

            yield SourceFile(path=full, relpath=full.relative_to(root), size_bytes=size)


def sha256_of(path: Path) -> str:
    """Compute SHA-256 of a file's bytes. Used by walkers and emitters."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def manifest_json(
    root: Path, *, include_glob: list[str] | None = None, exclude_glob: list[str] | None = None
) -> str:
    """Walk `root` and return a JSON string describing every file's routing.

    Output shape:
        {
          "root": "<abs path>",
          "count": N,
          "scanned_at": "<ISO timestamp>",
          "files": [
            {"path": "...", "relpath": "...", "size": N, "sha256": "...",
             "engine": "officecli" | null, "supported": true|false}
          ]
        }
    """
    from .router import get_adapter  # local import to avoid a cycle

    files = []
    for sf in walk(root, include_glob=include_glob, exclude_glob=exclude_glob):
        adapter = get_adapter(sf.path)
        files.append(
            {
                "path": str(sf.path),
                "relpath": str(sf.relpath),
                "size": sf.size_bytes,
                "sha256": sha256_of(sf.path),
                "engine": adapter.name if adapter else None,
                "supported": adapter is not None,
            }
        )

    payload = {
        "root": str(root.resolve()),
        "count": len(files),
        "scanned_at": _utc_now_iso(),
        "files": files,
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)


def _utc_now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
