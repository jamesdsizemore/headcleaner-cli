"""Markdown emitter — write one .md file per CanonicalDoc.

Output: <output>/<mirrored-source-relpath-as-flat-name>.md
The Markdown frontmatter is a small, human-readable subset; the OKF emitter
adds the full v0.2 trust family on top.
"""
from __future__ import annotations

from pathlib import Path

import yaml

from ..normalize import CanonicalDoc


def render(doc: CanonicalDoc) -> str:
    """Return the full .md contents (frontmatter + body) for this doc."""
    fm = doc.to_md_frontmatter()
    yaml_block = yaml.safe_dump(fm, sort_keys=False, allow_unicode=True).strip()
    body = doc.body_md.rstrip() + "\n"
    return f"---\n{yaml_block}\n---\n\n{body}"


def md_filename_for(doc: CanonicalDoc) -> str:
    """Build a deterministic .md filename for this doc.

    Mirrors the source path layout under the output root, but with .md suffix.
    e.g. source 'inbox/finance/q3.pdf' → 'inbox/finance/q3.pdf.md'
    """
    rel = doc.source_relpath
    # Append .md without clobbering an existing .md suffix
    name = rel.name + ".md" if not rel.suffix else rel.name + ".md"
    return str(rel.parent / name) if rel.parent != Path(".") else name


def write(doc: CanonicalDoc, output_root: Path) -> Path:
    """Write the Markdown file and return the absolute output path."""
    rel = md_filename_for(doc)
    out_path = output_root / rel
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(render(doc), encoding="utf-8")
    return out_path
