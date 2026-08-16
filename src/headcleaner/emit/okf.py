"""OKF v0.2 emitter — write one concept per CanonicalDoc.

Output layout: <output_root>/<mirrored-source-relpath-without-ext>/<basename>.md

Concept frontmatter includes the full OKF v0.2 trust family:
  type, title, description, resource, tags, status, stale_after,
  sources[{uri, kind, sha256}], generated, verified.

See docs/OKF_NOTES.md for the contract and the honesty policy
(we never auto-set verified to anything stronger than 'human:pending').
"""
from __future__ import annotations

from pathlib import Path

import yaml

from ..normalize import CanonicalDoc


def render(doc: CanonicalDoc, *, obsidian_compat: bool = False) -> str:
    """Return the full OKF concept (.md) contents.

    When `obsidian_compat` is True, additional flat properties are added
    (`source`, `sha256`, `generated_by`, `verified_by`, `stale_on`) that
    Obsidian renders as clickable note properties.
    """
    fm = doc.to_okf_frontmatter(obsidian_compat=obsidian_compat)
    yaml_block = yaml.safe_dump(fm, sort_keys=False, allow_unicode=True).strip()
    body = doc.body_md.rstrip() + "\n"
    return f"---\n{yaml_block}\n---\n\n{body}"


def okf_relpath_for(doc: CanonicalDoc) -> Path:
    """Path relative to the OKF bundle root.

    Mirrors the source layout (inbox/q3.pdf → inbox/q3.md).
    The .md suffix replaces the source extension so the concept name
    doesn't carry the format.
    """
    rel = doc.source_relpath
    # Replace source extension with .md
    base = rel.with_suffix(".md")
    return base


def write(doc: CanonicalDoc, output_root: Path, *, obsidian_compat: bool = False) -> Path:
    """Write the OKF concept file. Returns the absolute path."""
    rel = okf_relpath_for(doc)
    out_path = output_root / rel
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(render(doc, obsidian_compat=obsidian_compat), encoding="utf-8")
    return out_path
