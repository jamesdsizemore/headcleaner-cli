"""headcleaner MCP server (v0.11.0).

Exposes OKF bundles produced by ``headcleaner`` as Model Context Protocol
tools, so any MCP-capable agent host (Claude Code, Cursor, custom agents)
can search, read, and analyze them.

Tool verbs and semantics follow ``travisjakel/okf-mcp`` (Apache-2.0) so
the two servers are interchangeable from an agent's perspective. Where
that server uses an okf-ingest DuckDB catalog, we use headcleaner's
in-process ``viewer.build()`` to walk the bundle directory and produce
the same nodes/edges graph — no extra runtime, no separate ingest step.

Tools exposed (10):

- ``okf_list_bundles``  — list bundles the server has loaded
- ``okf_search``        — substring match across title + body
- ``okf_get_concept``   — read one concept (frontmatter + body)
- ``okf_context``       — concept + BFS neighborhood as one markdown blob
- ``okf_related``       — top-k related concepts by link structure
- ``okf_impact``        — outbound + inbound + transitive links
- ``okf_doctor``        — health score + per-rule findings
- ``okf_diff``          — what changed since the bundle was loaded
- ``okf_refresh``       — re-ingest a bundle after changes
- ``okf_sql``           — read-only SELECT over an in-memory catalog

The server speaks MCP over stdio. Install headcleaner with the ``mcp``
extra (``uv pip install 'headcleaner[mcp]'``) and run
``headcleaner mcp <bundle-dir> [...]``.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import re
import sys
import threading
from pathlib import Path
from typing import Optional

from . import registry as _registry
from .viewer import build_with_unresolved

try:
    from mcp.server.mcpserver import MCPServer
except ImportError as e:
    raise ImportError(
        "headcleaner.mcp requires the `mcp` package. Install with: "
        "`uv pip install 'headcleaner[mcp]'`"
    ) from e



# ---------------------------------------------------------------------------
# Bundle registry — minimal, in-process, lock-protected
# ---------------------------------------------------------------------------


class BundleEntry:
    """One loaded bundle + a snapshot of its files for diff detection."""

    def __init__(self, name: str, path: Path) -> None:
        self.name = name
        self.path = path
        self.loaded_at = _dt.datetime.now(_dt.timezone.utc).isoformat()
        self.nodes: list[dict] = []
        self.edges: list[dict] = []
        self.unresolved: list[dict] = []  # broken links captured at ingest
        self.by_id: dict[str, dict] = {}
        # inbound/outbound adjacency derived from edges
        self.out: dict[str, list[str]] = {}
        self.inb: dict[str, list[str]] = {}
        # file snapshot for okf_diff
        self.files: dict[str, str] = {}  # path -> sha256
        self._ingest()

    def _ingest(self) -> None:
        self.nodes, self.edges, self.unresolved = build_with_unresolved(self.path)
        self.by_id = {n["id"]: n for n in self.nodes}
        self.out = {n["id"]: [] for n in self.nodes}
        self.inb = {n["id"]: [] for n in self.nodes}
        for e in self.edges:
            self.out.setdefault(e["source"], []).append(e["target"])
            self.inb.setdefault(e["target"], []).append(e["source"])
        # Snapshot files for diff
        for f in self.path.rglob("*.md"):
            if f.is_file():
                try:
                    h = hashlib.sha256(f.read_bytes()).hexdigest()
                    self.files[str(f.relative_to(self.path)).replace("\\", "/")] = h
                except OSError:
                    pass


class BundleRegistry:
    def __init__(self) -> None:
        self._bundles: dict[str, BundleEntry] = {}
        self._order: list[str] = []  # preserve registration order; [0] is default
        self.lock = threading.Lock()

    def add(self, name: str, source: Path) -> None:
        with self.lock:
            if name in self._bundles:
                self._bundles[name]._ingest()  # refresh
                return
            entry = BundleEntry(name, source)
            self._bundles[name] = entry
            self._order.append(name)

    def refresh(self, name: Optional[str]) -> dict:
        with self.lock:
            if name is None and self._order:
                name = self._order[0]
            entry = self._bundles.get(name or "")
            if not entry:
                return {"ok": False, "error": f"bundle '{name}' not found"}
            before = len(entry.nodes), len(entry.edges)
            entry._ingest()
            after = len(entry.nodes), len(entry.edges)
            return {
                "ok": True,
                "name": name,
                "concepts_before": before[0],
                "concepts_after": after[0],
                "links_before": before[1],
                "links_after": after[1],
            }

    def get(self, name: Optional[str]) -> BundleEntry | None:
        with self.lock:
            if name:
                return self._bundles.get(name)
            if self._order:
                return self._bundles[self._order[0]]
            return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _resolve_slug(target: str) -> tuple[str | None, str]:
    """If target starts with `@`, resolve the slug to a registered bundle name.
    Returns (None, target) if no @ prefix or no slash after slug.
    """
    if not target or not target.startswith("@"):
        return None, target
    rest = target[1:]
    if not rest or "/" not in rest:
        return None, target
    slug, concept = rest.split("/", 1)
    mapping = _registry.load_registry()
    if slug not in mapping:
        return slug, concept
    return slug, concept


def _resolve_concept_id(
    reg: BundleRegistry, target: str, bundle_name: Optional[str]
) -> tuple[str | None, list[str]]:
    """Resolve a wikilink-style name to a concept id. Returns (id, candidates).

    Supports `@slug/concept` prefix for registered bundles.
    Mirrors upstream okf-mcp semantics: id, alias, title, or filename stem.
    Ambiguous names return candidates.
    """
    if target.startswith("@"):
        slug, rest = _resolve_slug(target)
        if slug is None:
            return None, []
        if bundle_name is None and slug:
            if reg.get(slug) is None:
                mapping = _registry.load_registry()
                if slug in mapping:
                    try:
                        reg.add(slug, mapping[slug])
                    except Exception:
                        return None, []
            bundle_name = slug
        target = rest
    entry = reg.get(bundle_name)
    if not entry:
        return None, []
    # Exact id match
    if target in entry.by_id:
        return target, [target]
    # Title (case-insensitive) match
    target_lower = target.lower().strip()
    by_title = [cid for cid, n in entry.by_id.items() if n.get("title", "").lower() == target_lower]
    if len(by_title) == 1:
        return by_title[0], by_title
    if len(by_title) > 1:
        return None, by_title
    # Filename stem match
    target_stem = target.rstrip(".md")
    by_stem = [cid for cid in entry.by_id if cid.endswith(target_stem)]
    if len(by_stem) == 1:
        return by_stem[0], by_stem
    if len(by_stem) > 1:
        return None, by_stem
    return None, []


# ---------------------------------------------------------------------------
# Tool implementations (deterministic, no model calls)
# ---------------------------------------------------------------------------


def okf_list_bundles(reg: BundleRegistry) -> list[dict]:
    with reg.lock:
        return [
            {
                "name": e.name,
                "path": str(e.path),
                "concepts": len(e.nodes),
                "links": len(e.edges),
                "loaded_at": e.loaded_at,
            }
            for e in [reg._bundles[n] for n in reg._order]
        ]


def okf_search(
    reg: BundleRegistry,
    term: str,
    bundle_name: Optional[str],
    limit: int,
    all_bundles: bool = False,
) -> list[dict]:
    """Search for `term` in concept titles, descriptions, bodies.

    With all_bundles=True, search every loaded bundle and tag each hit
    with its bundle name.
    """
    t = term.lower()
    hits: list[dict] = []
    with reg.lock:
        if all_bundles:
            entries = [(name, reg._bundles[name]) for name in reg._order]
        elif bundle_name and bundle_name in reg._bundles:
            entries = [(bundle_name, reg._bundles[bundle_name])]
        elif reg._order:
            entries = [(reg._order[0], reg._bundles[reg._order[0]])]
        else:
            entries = []

    for bname, entry in entries:
        if entry is None:
            continue
        for n in entry.nodes:
            if (
                t in n.get("title", "").lower()
                or t in n.get("description", "").lower()
                or t in n.get("body", "").lower()
            ):
                hit = {
                    "id": n["id"],
                    "type": n.get("type", ""),
                    "title": n.get("title", ""),
                    "description": n.get("description", ""),
                }
                if all_bundles:
                    hit["bundle"] = bname
                hits.append(hit)
    return hits[: max(1, limit)]


def okf_get_concept(reg: BundleRegistry, target: str, bundle_name: Optional[str]) -> dict:
    cid, cands = _resolve_concept_id(reg, target, bundle_name)
    if cid is None:
        if cands:
            return {"error": "ambiguous", "candidates": cands}
        return {"error": f"concept '{target}' not found"}
    entry = reg.get(bundle_name)
    assert entry is not None
    n = entry.by_id[cid]
    return {
        "id": cid,
        "type": n.get("type"),
        "title": n.get("title"),
        "description": n.get("description"),
        "tags": n.get("tags", []),
        "status": n.get("status"),
        "stale_after": n.get("stale_after"),
        "generated": n.get("generated"),
        "verified": n.get("verified"),
        "sources": n.get("sources", []),
        "body": n.get("body", ""),
    }


def okf_context(
    reg: BundleRegistry,
    start: Optional[str],
    depth: int,
    max_tokens: int,
    bundle_name: Optional[str],
) -> dict:
    entry = reg.get(bundle_name)
    if not entry:
        return {"error": "no bundle loaded"}
    depth = max(0, min(depth, 5))
    if start is None:
        # Pack everything (truncated)
        parts = [
            f"# {entry.name}\n\n",
            f"_{len(entry.nodes)} concepts, {len(entry.edges)} links_\n\n",
        ]
        for n in entry.nodes[:50]:
            parts.append(f"## {n['title']}\n\n{n.get('body', '')[:500]}\n\n")
        blob = "\n".join(parts)
        return {"bundle": entry.name, "concepts": len(entry.nodes), "body": blob[: max_tokens * 4]}

    cid, cands = _resolve_concept_id(reg, start, bundle_name)
    if cid is None:
        return {"error": "ambiguous" if cands else "not found", "candidates": cands}
    # BFS neighborhood
    seen = {cid}
    frontier = [cid]
    for _ in range(depth):
        new_frontier = []
        for n in frontier:
            for nb in entry.out.get(n, []) + entry.inb.get(n, []):
                if nb not in seen:
                    seen.add(nb)
                    new_frontier.append(nb)
        frontier = new_frontier
    # Build markdown blob
    parts = [f"# Context from {entry.name}\n\n"]
    for c in [cid] + [n for n in seen if n != cid]:
        node = entry.by_id[c]
        parts.append(f"## {node['title']}\n\n{node.get('body', '')[:500]}\n\n")
    blob = "\n".join(parts)
    return {
        "bundle": entry.name,
        "start": cid,
        "depth": depth,
        "concepts": len(seen),
        "body": blob[: max_tokens * 4],
    }


def okf_related(
    reg: BundleRegistry, concept: str, k: int, bundle_name: Optional[str]
) -> list[dict]:
    entry = reg.get(bundle_name)
    if not entry:
        return []
    cid, cands = _resolve_concept_id(reg, concept, bundle_name)
    if cid is None:
        return [{"error": "ambiguous" if cands else "not found", "candidates": cands}]
    # Degree-based "related": combine inbound + outbound counts
    scores: dict[str, int] = {}
    for nb in entry.out.get(cid, []):
        scores[nb] = scores.get(nb, 0) + 1
    for nb in entry.inb.get(cid, []):
        scores[nb] = scores.get(nb, 0) + 1
    ranked = sorted(scores.items(), key=lambda x: (-x[1], x[0]))[: max(1, k)]
    return [{"id": c, "score": s, "title": entry.by_id[c].get("title", c)} for c, s in ranked]


def okf_impact(reg: BundleRegistry, concept: str, bundle_name: Optional[str]) -> dict:
    entry = reg.get(bundle_name)
    if not entry:
        return {"error": "no bundle loaded"}
    cid, cands = _resolve_concept_id(reg, concept, bundle_name)
    if cid is None:
        return {"error": "ambiguous" if cands else "not found", "candidates": cands}
    outbound = entry.out.get(cid, [])
    inbound = entry.inb.get(cid, [])
    # Transitive closure (BFS from outbound) — what breaks if cid changes
    seen = set()
    frontier = list(outbound)
    while frontier:
        n = frontier.pop()
        if n in seen:
            continue
        seen.add(n)
        frontier.extend(entry.out.get(n, []))
    return {
        "concept": cid,
        "title": entry.by_id[cid].get("title", cid),
        "outbound": outbound,
        "inbound": inbound,
        "transitive_outbound": sorted(seen),
    }


def okf_doctor(
    reg: BundleRegistry,
    bundle_name: Optional[str],
    stale_days: Optional[int],
    now_iso: Optional[str],
) -> dict:
    entry = reg.get(bundle_name)
    if not entry:
        return {
            "score": 0,
            "errors": 1,
            "warnings": 0,
            "findings": [{"rule": "no-bundle", "severity": "error", "message": "no bundle loaded"}],
        }
    findings: list[dict] = []
    error_count = 0
    warning_count = 0
    # 1. Broken links — captured at ingest time (link_targets + read_sources
    #    walk that viewer.build() drops silently).
    broken = len(entry.unresolved)
    for u in entry.unresolved:
        findings.append(
            {
                "rule": "broken-link",
                "severity": "error",
                "concept": u["source"],
                "target": u["target"],
                "kind": u.get("kind", "markdown-link"),
            }
        )
    error_count += broken
    # 2. Orphans (no inbound AND no outbound)
    orphans = [
        n["id"] for n in entry.nodes if not entry.out.get(n["id"]) and not entry.inb.get(n["id"])
    ]
    if orphans:
        warning_count += len(orphans)
        for o in orphans:
            findings.append({"rule": "orphan", "severity": "warning", "concept": o})
    # 3. Missing type
    no_type = [n["id"] for n in entry.nodes if not n.get("type") or n["type"] == "Untyped"]
    if no_type:
        warning_count += len(no_type)
        for o in no_type:
            findings.append({"rule": "missing-type", "severity": "warning", "concept": o})
    # 4. Stale (if stale_days given)
    if stale_days and now_iso:
        from datetime import datetime, timedelta

        now = datetime.fromisoformat(now_iso.replace("Z", "+00:00"))
        cutoff = (now - timedelta(days=stale_days)).strftime("%Y-%m-%d")
        stale = []
        for n in entry.nodes:
            g = n.get("generated") or {}
            at = g.get("at", "")[:10] if isinstance(g, dict) else ""
            if at and at < cutoff:
                stale.append(n["id"])
        if stale:
            warning_count += len(stale)
            for s in stale:
                findings.append({"rule": "stale", "severity": "warning", "concept": s})
    total = len(entry.nodes)
    score = round(100 * (total - error_count) / total) if total else 0
    return {
        "bundle": entry.name,
        "score": score,
        "errors": error_count,
        "warnings": warning_count,
        "concepts": total,
        "findings": findings[:100],
    }


def okf_diff(reg: BundleRegistry, bundle_name: Optional[str]) -> dict:
    entry = reg.get(bundle_name)
    if not entry:
        return {"error": "no bundle loaded"}
    current_files: dict[str, str] = {}
    for f in entry.path.rglob("*.md"):
        if f.is_file():
            try:
                h = hashlib.sha256(f.read_bytes()).hexdigest()
                current_files[str(f.relative_to(entry.path)).replace("\\", "/")] = h
            except OSError:
                pass
    added = sorted(set(current_files) - set(entry.files))
    removed = sorted(set(entry.files) - set(current_files))
    changed = sorted(
        p for p in current_files if p in entry.files and current_files[p] != entry.files[p]
    )
    return {"bundle": entry.name, "added": added, "removed": removed, "changed": changed}


def okf_sql(reg: BundleRegistry, query: str, bundle_name: Optional[str]) -> list[dict]:
    """A minimal read-only SQL-ish layer: parse simple SELECT-style queries
    over the in-memory node/edge lists.

    Supports:
      SELECT <fields> FROM concepts [WHERE <field> <op> '<value>']
      SELECT <fields> FROM links [WHERE ...]

    Fields: id, type, title, description, tags, status, source, target
    Operators: =, !=, LIKE, IN
    """
    entry = reg.get(bundle_name)
    if not entry:
        return []
    q = query.strip().rstrip(";").strip()
    m = re.match(
        r"^SELECT\s+(?P<cols>[\w,\s*]+)\s+FROM\s+(?P<tbl>concepts|links)"
        r"(?:\s+WHERE\s+(?P<where>.+))?$",
        q,
        re.IGNORECASE | re.DOTALL,
    )
    if not m:
        return [{"error": f"unsupported query: {q!r}"}]
    cols = [c.strip() for c in m.group("cols").split(",")]
    want_all = cols == ["*"]
    tbl = m.group("tbl").lower()
    where = m.group("where")
    if tbl == "concepts":
        rows = [
            {
                "id": n["id"],
                "type": n.get("type", ""),
                "title": n.get("title", ""),
                "description": n.get("description", ""),
                "tags": n.get("tags", []),
                "status": n.get("status", ""),
            }
            for n in entry.nodes
        ]
    else:
        rows = [{"source": e["source"], "target": e["target"]} for e in entry.edges]
    if where:
        wm = re.match(r"^(\w+)\s*(=|!=|LIKE|IN)\s*(.+)$", where.strip(), re.IGNORECASE)
        if wm:
            field, op, raw = wm.group(1).lower(), wm.group(2).upper(), wm.group(3).strip()
            if op == "IN":
                vals = [v.strip().strip("'\"") for v in raw.strip("()").split(",")]
                rows = [r for r in rows if str(r.get(field, "")) in vals]
            elif op == "LIKE":
                pat = raw.strip("'\"")
                rows = [r for r in rows if re.search(pat, str(r.get(field, "")), re.IGNORECASE)]
            else:
                v = raw.strip("'\"")
                if op == "=":
                    rows = [r for r in rows if str(r.get(field, "")) == v]
                elif op == "!=":
                    rows = [r for r in rows if str(r.get(field, "")) != v]
    if want_all:
        return rows
    out = []
    for r in rows:
        out.append({c: r.get(c) for c in cols})
    return out


# ---------------------------------------------------------------------------
# MCP server wiring
# ---------------------------------------------------------------------------

mcp = MCPServer("headcleaner")
reg = BundleRegistry()


@mcp.tool()
def okf_list_bundles_tool() -> list[dict]:
    """List the OKF bundles this server has loaded."""
    with reg.lock:
        return okf_list_bundles(reg)


@mcp.tool()
def okf_search_tool(
    term: str,
    bundle: Optional[str] = None,
    limit: int = 20,
    all_bundles: bool = False,
) -> list[dict]:
    """Search one or all loaded bundles.

    Set all_bundles=True to search across every bundle currently registered
    with the server. Hits from other bundles include a `bundle` field.
    """
    """Find concepts whose title, description, or body contains `term`."""
    with reg.lock:
        return okf_search(reg, term, bundle, limit, all_bundles=all_bundles)


@mcp.tool()
def okf_get_concept_tool(target: str, bundle: Optional[str] = None) -> dict:
    """Read one concept (frontmatter + body). Accepts id, title, or filename stem."""
    with reg.lock:
        return okf_get_concept(reg, target, bundle)


@mcp.tool()
def okf_context_tool(
    start: Optional[str] = None,
    depth: int = 1,
    max_tokens: int = 8000,
    bundle: Optional[str] = None,
) -> dict:
    """Assemble a curated markdown blob: a concept + BFS neighborhood, capped by max_tokens."""
    with reg.lock:
        return okf_context(reg, start, depth, max_tokens, bundle)


@mcp.tool()
def okf_related_tool(concept: str, k: int = 10, bundle: Optional[str] = None) -> list[dict]:
    """Top-k concepts by link degree (inbound + outbound count)."""
    with reg.lock:
        return okf_related(reg, concept, k, bundle)


@mcp.tool()
def okf_impact_tool(concept: str, bundle: Optional[str] = None) -> dict:
    """Report outbound / inbound / transitive links for a concept."""
    with reg.lock:
        return okf_impact(reg, concept, bundle)


@mcp.tool()
def okf_doctor_tool(bundle: Optional[str] = None, stale_days: Optional[int] = None) -> dict:
    """Health report for a bundle (score, errors, warnings, per-rule findings)."""
    now_iso = None
    if stale_days is not None:
        now_iso = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with reg.lock:
        return okf_doctor(reg, bundle, stale_days, now_iso)


@mcp.tool()
def okf_diff_tool(bundle: Optional[str] = None) -> dict:
    """What changed on disk since the bundle was loaded."""
    with reg.lock:
        return okf_diff(reg, bundle)


@mcp.tool()
def okf_refresh_tool(bundle: Optional[str] = None) -> dict:
    """Re-ingest a bundle so the in-memory catalog reflects current files."""
    with reg.lock:
        return reg.refresh(bundle)


@mcp.tool()
def okf_sql_tool(query: str, bundle: Optional[str] = None) -> list[dict]:
    """Read-only SELECT over the in-memory catalog (concepts, links)."""
    with reg.lock:
        return okf_sql(reg, query, bundle)


def main(argv: Optional[list[str]] = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        return 0 if args else 2
    for a in args:
        if (
            "=" in a
            and not a.split("=", 1)[0].startswith((".", "/", "\\"))
            and ":" not in a.split("=", 1)[0]
        ):
            name, source = a.split("=", 1)
        else:
            name, source = None, a
        if name is None:
            base = source.rstrip("/\\").replace("\\", "/").rsplit("/", 1)[-1]
            name = base[:-7] if base.endswith(".duckdb") else base
        reg.add(name, Path(source).resolve())
    try:
        mcp.run()  # stdio
    except KeyboardInterrupt:
        return 0
    return 0




@mcp.tool()
def okf_registry_list() -> list[dict]:
    """List all bundles registered under @slug aliases."""
    mapping = _registry.load_registry()
    return [{"slug": slug, "path": str(p)} for slug, p in sorted(mapping.items())]


@mcp.tool()
def okf_registry_add(slug: str, bundle_path: str) -> dict:
    """Add a bundle under a slug alias. Then reference it as @<slug>/... .

    Example:
        okf_registry_add(slug="docs", bundle_path="C:/Users/me/Documents/okf")
        okf_get_concept("@docs/readme")
    """
    try:
        _registry.add_slug(slug, bundle_path)
    except ValueError as e:
        return {"ok": False, "error": str(e)}
    return {"ok": True, "slug": slug, "path": str(Path(bundle_path).expanduser().resolve())}


@mcp.tool()
def okf_registry_remove(slug: str) -> dict:
    """Remove a slug from the registry."""
    _registry.remove_slug(slug)
    return {"ok": True, "slug": slug}


@mcp.tool()
def okf_registry_resolve(target: str) -> dict:
    """Resolve `@slug/concept` to the bundle path + concept id."""
    slug, bundle_path = _registry.resolve_slug(target)
    if bundle_path is None:
        return {"ok": False, "error": f"unknown slug {slug!r}" if slug else "not a slug"}
    rest = target[len(f"@{slug}/"):] if target.startswith(f"@{slug}/") else ""
    return {
        "ok": True,
        "slug": slug,
        "bundle_path": str(bundle_path),
        "concept": rest or None,
    }


if __name__ == "__main__":
    sys.exit(main())
