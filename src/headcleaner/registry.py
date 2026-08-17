"""Persistent bundle registry for headcleaner MCP (v0.13.0).

Maps human-friendly `@slug` aliases to bundle paths on disk, so users can
write `@docs/readme` or `@myarchive/foo` instead of absolute paths.

Format: a TOML file at `$HEADCLEANER_REGISTRY` (default
`~/.config/headcleaner/registry.toml`). TOML was chosen over JSON because
comments and aliases like `my-org/knowledge-base` are valid TOML but ugly
JSON, and pyyaml is already a dep but TOML is stdlib on 3.11+.

Example::

    # registry.toml
    [bundles]
    docs = "C:/Users/me/Documents/okf"
    archive = "/mnt/old-archive"
    "my-org/kb" = "C:/work/kb-v2"

Then in MCP::

    okf_get_concept(target="@docs/readme")
    okf_registry_list()
    okf_registry_resolve("@archive/...")
"""
from __future__ import annotations

import os
import tomllib
import tomli_w
from pathlib import Path
from typing import Optional

DEFAULT_PATH = Path.home() / ".config" / "headcleaner" / "registry.toml"

REGISTRY_ENV = "HEADCLEANER_REGISTRY"


def registry_path() -> Path:
    """Return the path to the registry file, honoring $HEADCLEANER_REGISTRY."""
    env = os.environ.get(REGISTRY_ENV)
    if env:
        return Path(env).expanduser().resolve()
    return DEFAULT_PATH


def load_registry(path: Optional[Path] = None) -> dict[str, Path]:
    """Load the registry. Returns {slug: resolved_path}."""
    p = path or registry_path()
    if not p.exists():
        return {}
    data = tomllib.loads(p.read_text(encoding="utf-8"))
    bundles = data.get("bundles", {})
    return {slug: Path(raw).expanduser().resolve() for slug, raw in bundles.items()}


def save_registry(mapping: dict[str, Path], path: Optional[Path] = None) -> None:
    """Persist the registry. Creates parent dirs as needed."""
    p = path or registry_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    serializable = {slug: str(p) for slug, p in mapping.items()}
    p.write_text(
        tomli_w.dumps({"bundles": serializable}),
        encoding="utf-8",
    )


def add_slug(slug: str, bundle_path: Path | str, path: Optional[Path] = None) -> dict[str, Path]:
    """Register a slug → bundle path. Returns the updated registry."""
    if not slug or "@" in slug or " " in slug:
        raise ValueError(f"invalid slug {slug!r}: must not be empty, contain '@' or spaces")
    mapping = load_registry(path)
    mapping[slug] = Path(bundle_path).expanduser().resolve()
    save_registry(mapping, path)
    return mapping


def remove_slug(slug: str, path: Optional[Path] = None) -> dict[str, Path]:
    """Remove a slug. Returns the updated registry. No-op if absent."""
    mapping = load_registry(path)
    mapping.pop(slug, None)
    save_registry(mapping, path)
    return mapping


def resolve_slug(target: str, path: Optional[Path] = None) -> tuple[Optional[str], Optional[Path]]:
    """Resolve `@slug` or `@slug/concept-id` to (slug, bundle_path).

    Returns (None, None) if the target doesn't start with `@` or the slug
    is not registered. Bare `@` (empty slug) is rejected.
    """
    if not target or not target.startswith("@"):
        return None, None
    rest = target[1:]
    if not rest:
        return None, None
    # Take the first path segment as the slug
    parts = rest.split("/", 1)
    slug = parts[0]
    mapping = load_registry(path)
    if slug not in mapping:
        return slug, None
    return slug, mapping[slug]