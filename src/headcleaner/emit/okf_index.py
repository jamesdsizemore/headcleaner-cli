"""OKF v0.2 directory-index generator (§8 of the OKF spec).

For every directory under the OKF bundle that contains ≥2 concepts
(or where the source had ≥2 files), we generate an `index.md` listing
the concepts it contains. This enables progressive disclosure: a
consumer can `cat index.md` to see what's available without loading
every concept.

The index is generated after all concepts are written, by walking
the bundle root and inspecting the frontmatter of each concept.
"""
from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

import yaml


_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def _read_frontmatter(path: Path) -> dict | None:
    """Parse YAML frontmatter; return None if the file isn't a concept."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return None
    try:
        return yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        return None


def _index_md(directory_name: str, concepts: list[tuple[Path, dict]]) -> str:
    """Build an index.md body for one directory."""
    # Use a clean heading: "." → "Documents"; nested paths keep their segments
    if directory_name in {"", "."}:
        title = "# Documents"
    else:
        title = f"# {directory_name}"
    bullets = []
    for concept_path, fm in sorted(concepts, key=lambda t: t[0].name):
        rel_link = concept_path.name
        ctype = fm.get("type", "?")
        ctitle = fm.get("title") or concept_path.stem
        cstatus = fm.get("status", "")
        suffix = f" — {cstatus}" if cstatus else ""
        bullets.append(f"- [{ctitle}]({rel_link}) — `{ctype}`{suffix}")

    body = "\n".join(bullets) if bullets else "_No concepts in this directory._"
    return f"{title}\n\n## Concepts\n\n{body}\n"


def generate(bundle_root: Path) -> int:
    """Walk a freshly-written OKF bundle and emit index.md in each subdir.

    Returns the number of index.md files written.
    """
    if not bundle_root.is_dir():
        return 0

    # Collect concepts grouped by parent directory
    by_dir: dict[Path, list[tuple[Path, dict]]] = defaultdict(list)
    for md_path in bundle_root.rglob("*.md"):
        # Skip existing index.md (in case this is re-run)
        if md_path.name == "index.md":
            continue
        fm = _read_frontmatter(md_path)
        if fm is None or "type" not in fm:
            continue
        by_dir[md_path.parent].append((md_path, fm))

    written = 0
    for directory, concepts in by_dir.items():
        if len(concepts) < 1:
            continue
        index_path = directory / "index.md"
        directory_name = directory.relative_to(bundle_root).as_posix() or directory.name
        index_path.write_text(_index_md(directory_name, concepts), encoding="utf-8")
        written += 1

    # Also write a top-level index if we have anything
    if bundle_root in by_dir and (bundle_root / "index.md") not in [p for p, _ in by_dir[bundle_root] if p.name == "index.md"]:
        pass  # already handled by the loop above

    return written
