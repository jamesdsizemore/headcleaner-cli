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


# ---------------------------------------------------------------------------
# Batch 4 / Eng #37: log.md (OKF §9) generation + #38 enriched index.md
# ---------------------------------------------------------------------------


def _first_sentence(body_md: str) -> str:
    """Extract a short one-line description from a Markdown body.

    Looks for the first non-heading, non-blockquote line. Trims to ~120
    chars with ellipsis. Used by #38 to enrich index.md.
    """
    for line in body_md.splitlines():
        s = line.strip()
        if not s or s.startswith(("#", "```", ">")):
            continue
        if len(s) > 120:
            s = s[:117] + "..."
        return s
    return ""


def _word_count(text: str) -> int:
    """Cheap whitespace-based word counter."""
    return len(text.split())


def _enriched_index_md(directory_name: str, concepts: list[tuple[Path, dict]]) -> str:
    """Like `_index_md` but each entry shows description + word count.

    Used when the `enriched` flag is set on `okf_index.generate()`.
    """
    title = "# Documents" if directory_name in {"", "."} else f"# {directory_name}"
    bullets = []
    for concept_path, fm in sorted(concepts, key=lambda t: t[0].name):
        rel_link = concept_path.name
        ctype = fm.get("type", "?")
        ctitle = fm.get("title") or concept_path.stem
        cstatus = fm.get("status", "")
        status_suffix = f" — {cstatus}" if cstatus else ""
        # New (Eng #38): show description + word count
        desc = fm.get("description", "")
        # Word count from the body (strip frontmatter first)
        body_text = concept_path.read_text(encoding="utf-8")
        m = _FRONTMATTER_RE.match(body_text)
        if m:
            body_text = body_text[m.end() :]
        wc = _word_count(body_text)
        desc_text = f" — {desc}" if desc else ""
        bullets.append(
            f"- [{ctitle}]({rel_link}) — `{ctype}`{status_suffix}{desc_text} _(~{wc} words)_"
        )
    body = "\n".join(bullets) if bullets else "_No concepts in this directory._"
    return f"{title}\n\n## Concepts\n\n{body}\n"


def append_log_entry(bundle_root: Path, record) -> None:
    """Append a dated entry to `<bundle_root>/log.md` (OKF §9).

    Format: a single section per run with timestamp + per-format counts +
    error summary. Idempotent on file existence — existing entries are
    preserved, the new one is appended.

    Args:
        bundle_root: the OKF bundle root (where log.md should live).
        record: a RunRecord from the pipeline.
    """
    log_path = bundle_root / "log.md"
    ts = record.finished_at or "1970-01-01T00:00:00Z"

    by_engine: dict[str, dict[str, int]] = {}
    errors: list[str] = []
    for r in record.results:
        e = r.engine or "no-adapter"
        s = r.status or "unknown"
        by_engine.setdefault(e, {}).setdefault(s, 0)
        by_engine[e][s] += 1
        if r.status == "failed" and r.error:
            errors.append(f"  - {r.relpath}: {r.error}")

    summary = []
    for engine, statuses in sorted(by_engine.items()):
        bits = ", ".join(f"{n} {s}" for s, n in sorted(statuses.items()))
        summary.append(f"  - `{engine}`: {bits}")

    entry = (
        f"\n## {ts} — headcleaner {record.version}\n\n"
        f"- Format: `{record.format}`\n"
        f"- Total: {len(record.results)} files\n\n"
        + ("### Per-engine\n\n" + "\n".join(summary) + "\n" if summary else "")
        + ("\n### Errors\n\n" + "\n".join(errors) + "\n" if errors else "")
    )

    # Append; create file if missing.
    if log_path.exists():
        existing = log_path.read_text(encoding="utf-8")
    else:
        existing = "# Bundle history\n\nThis file records every `headcleaner convert` run against this bundle. Newest entries appear at the bottom.\n"  # noqa: E501
    log_path.write_text(existing + entry, encoding="utf-8")


def generate(
    bundle_root: Path,
    *,
    enriched: bool = False,
    write_log: bool = False,
    record=None,
) -> int:
    """Generate index.md files, optionally enriched (Eng #38) + log.md (Eng #37).

    Backwards-compatible signature: returns the number of index.md files
    written. When `write_log=True`, also appends to log.md (record must be
    supplied).
    """
    if not bundle_root.is_dir():
        return 0

    # Discover concepts
    from collections import defaultdict

    by_dir: dict[Path, list[tuple[Path, dict]]] = defaultdict(list)
    for md_path in sorted(bundle_root.rglob("*.md")):
        if md_path.name == "index.md":
            continue
        fm = _read_frontmatter(md_path)
        if fm is None or "type" not in fm:
            continue
        by_dir[md_path.parent].append((md_path, fm))

    written = 0
    for directory, concepts in by_dir.items():
        if not concepts:
            continue
        index_path = directory / "index.md"
        directory_name = directory.relative_to(bundle_root).as_posix() or directory.name
        body = (_enriched_index_md if enriched else _index_md)(directory_name, concepts)
        index_path.write_text(body, encoding="utf-8")
        written += 1

    # OKF §9 log.md
    if write_log and record is not None:
        append_log_entry(bundle_root, record)

    return written
