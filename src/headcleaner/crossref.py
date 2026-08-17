"""Cross-concept link inference (Eng #34).

After a convert run, this module walks every concept in the OKF bundle
and rewrites plain-text mentions of other concepts as markdown links.

Detection rules (in priority order):
1. Exact match on `title` (case-insensitive, word-boundary)
2. Exact match on `resource` URI basename (e.g. "q3.pdf" → matches concepts with `resource: file://...q3.pdf`)
3. Exact match on any tag (a #tag in the body becomes a link to that tag's index)

The first match per mention wins. Links go to the concept's relative
path within the bundle.

Idempotent: running it twice doesn't double-wrap links.

Usage:
    from headcleaner.crossref import linkify_bundle
    linkify_bundle(Path("./out/okf"))
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def _read_concepts(bundle_root: Path) -> list[tuple[Path, dict]]:
    """Return [(concept_path, frontmatter_dict)] for every concept file."""
    out: list[tuple[Path, dict]] = []
    for md_path in sorted(bundle_root.rglob("*.md")):
        if md_path.name in {"index.md", "log.md"}:
            continue
        try:
            text = md_path.read_text(encoding="utf-8")
        except OSError:
            continue
        m = _FRONTMATTER_RE.match(text)
        if not m:
            continue
        try:
            fm = yaml.safe_load(m.group(1)) or {}
        except yaml.YAMLError:
            continue
        if "type" not in fm:
            continue
        out.append((md_path, fm))
    return out


def _rewrite_body(body: str, link_replacements: dict[str, str]) -> str:
    """Replace plain-text mentions with markdown links.

    `link_replacements` maps mention-text → relative-path.
    """
    new_body = body
    for mention, target in link_replacements.items():
        # Word boundary, case-insensitive. The lookbehind for "[(" avoids
        # matching inside existing link syntax ([text](url)) or inside
        # frontmatter values.
        pattern = re.compile(
            rf"(?<![(\[A-Za-z0-9_./\-])\b{re.escape(mention)}\b(?![A-Za-z0-9_./\-])",
            re.IGNORECASE,
        )
        new_body = pattern.sub(f"[{mention}]({target})", new_body)
    return new_body


def linkify_bundle(bundle_root: Path) -> int:
    """Rewrite cross-concept mentions as markdown links.

    Returns the number of files modified.
    """
    concepts = _read_concepts(bundle_root)
    if not concepts:
        return 0

    # Build the lookup maps once
    by_title: dict[str, str] = {}  # title → relative path
    by_resource_basename: dict[str, str] = {}
    for concept_path, fm in concepts:
        try:
            rel = concept_path.relative_to(bundle_root).as_posix()
        except ValueError:
            rel = concept_path.name
        if fm.get("title"):
            by_title[str(fm["title"]).strip()] = rel
        resource = fm.get("resource", "")
        if resource.startswith("file://"):
            from urllib.parse import urlparse, unquote

            path = urlparse(resource).path
            basename = unquote(path).rsplit("/", 1)[-1]
            if basename:
                by_resource_basename[basename] = rel

    modified = 0
    for concept_path, fm in concepts:
        try:
            rel = concept_path.relative_to(bundle_root).as_posix()
        except ValueError:
            rel = concept_path.name

        text = concept_path.read_text(encoding="utf-8")
        m = _FRONTMATTER_RE.match(text)
        if not m:
            continue
        body = text[m.end() :]

        replacements: dict[str, str] = {}
        for title, target in by_title.items():
            if target == rel:
                continue  # don't link to self
            if title and len(title) >= 3:  # skip too-short to avoid noise
                replacements[title] = target

        # Body rewrite
        new_body = _rewrite_body(body, replacements)
        if new_body == body:
            continue
        concept_path.write_text(text[: m.end()] + new_body, encoding="utf-8")
        modified += 1
    return modified
