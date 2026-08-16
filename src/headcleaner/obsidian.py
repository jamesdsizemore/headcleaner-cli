"""Obsidian vault sync utilities.

Obsidian reads YAML frontmatter as note properties. The default OKF v0.2
frontmatter (`type`, `title`, `tags`, `sources[{uri, sha256}]`, etc.) is
valid YAML and Obsidian parses it without complaint, but:

- `sources` shows as a nested array, which Obsidian renders awkwardly
- `stale_after` shows as a date string, not a date property
- `generated` and `verified` use colon syntax (`human:user@host`) which
  Obsidian can confuse with nested keys

The `--obsidian-compat` flag in `cli.py` rewrites these fields for
cleaner Obsidian display while preserving the full OKF contract in the
body of the file.

Usage (programmatic):
    from headcleaner.obsidian import obsidian_compat
    obsidian_compat(canonical_doc)  # mutates doc in-place
"""
from __future__ import annotations

from typing import Any

from .normalize import CanonicalDoc


def obsidian_compat(doc: CanonicalDoc) -> None:
    """Mutate `doc` in place to make its OKF frontmatter Obsidian-friendly.

    Changes:
    - `tags` → always a flat list of lowercase strings (Obsidian renders
      them as clickable #tags)
    - `source` → add a flat string field with the first source URI
      (Obsidian renders as a clickable link)
    - `sha256` → add a flat string field (first source's SHA-256)
    - `generated_by` → rename `generated` (no colon in the value)
    - `verified_by` → rename `verified`
    - `stale_on` → rename `stale_after` (date-only string)

    The original OKF fields stay intact in the body for round-trip.
    """
    # tags: ensure list[str]
    tags = doc._tags()  # noqa: SLF001 — internal call by design
    doc.metadata["tags"] = tags

    # Derive flat fields for Obsidian
    fm = doc.to_okf_frontmatter()
    sources = fm.get("sources") or []
    if sources and isinstance(sources[0], dict):
        if sources[0].get("uri"):
            doc.metadata["source"] = sources[0]["uri"]
        if sources[0].get("sha256"):
            doc.metadata["sha256"] = sources[0]["sha256"]

    if fm.get("generated"):
        doc.metadata["generated_by"] = fm["generated"].replace(":", "_")
    if fm.get("verified"):
        doc.metadata["verified_by"] = fm["verified"].replace(":", "_")
    if fm.get("stale_after"):
        doc.metadata["stale_on"] = fm["stale_after"]


def render_okf_with_obsidian_metadata(doc: CanonicalDoc) -> str:
    """Render the OKF concept with the Obsidian-friendly fields added.

    Used when `--obsidian-compat` is set. Emits the same body but with
    extra flat fields in the frontmatter so Obsidian shows them as
    clickable properties.
    """
    fm = doc.to_okf_frontmatter()
    # Merge in the Obsidian flat fields
    sources = fm.get("sources") or []
    if sources and isinstance(sources[0], dict):
        if sources[0].get("uri"):
            fm["source"] = sources[0]["uri"]
        if sources[0].get("sha256"):
            fm["sha256"] = sources[0]["sha256"]
    if fm.get("generated"):
        fm["generated_by"] = fm["generated"].replace(":", "_")
    if fm.get("verified"):
        fm["verified_by"] = fm["verified"].replace(":", "_")
    if fm.get("stale_after"):
        fm["stale_on"] = fm["stale_after"]

    import yaml  # local import to avoid hard dep at module import
    yaml_block = yaml.safe_dump(fm, sort_keys=False, allow_unicode=True).strip()
    body = doc.body_md.rstrip() + "\n"
    return f"---\n{yaml_block}\n---\n\n{body}"
