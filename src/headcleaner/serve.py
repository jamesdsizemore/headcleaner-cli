"""`headcleaner serve` — local HTTP server for browsing the OKF bundle (Eng #22 full impl).

Routes:
    GET  /                              Bundle index (paginated concept list)
    GET  /concepts?page=N               Paginated list
    GET  /c/{relpath:path}              Rendered concept (HTML)
    GET  /raw/{relpath:path}            Raw markdown
    GET  /search?q=term                  Grep concepts by term
    GET  /api/concepts                  JSON list
    GET  /api/concept/{relpath:path}    JSON concept

The server is read-only — it does not modify the bundle. Frontmatter is
parsed once at startup and cached in memory.

Usage:
    headcleaner serve <bundle-dir> [--port 8765] [--host 127.0.0.1]

The CLI command is implemented in cli.py and delegates to `run_serve`.
"""
from __future__ import annotations

import html
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)


@dataclass
class Concept:
    path: Path           # absolute path to the .md file
    relpath: str         # path relative to bundle root
    frontmatter: dict
    body: str            # markdown body (after frontmatter)


@dataclass
class Bundle:
    root: Path
    concepts: list[Concept]

    @property
    def total(self) -> int:
        return len(self.concepts)


def _read_concept(path: Path, root: Path) -> Concept | None:
    """Parse one concept file."""
    text = path.read_text(encoding="utf-8")
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return None
    try:
        fm = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        return None
    if "type" not in fm:
        return None
    return Concept(
        path=path,
        relpath=str(path.relative_to(root)).replace("\\", "/"),
        frontmatter=fm,
        body=text[m.end():],
    )


def load_bundle(bundle_root: Path) -> Bundle:
    """Walk `bundle_root` and parse every concept."""
    concepts: list[Concept] = []
    if not bundle_root.is_dir():
        return Bundle(bundle_root, concepts)
    for md_path in sorted(bundle_root.rglob("*.md")):
        if md_path.name in {"index.md", "log.md", "attestation.json"}:
            continue
        c = _read_concept(md_path, bundle_root)
        if c is not None:
            concepts.append(c)
    return Bundle(bundle_root, concepts)


# ---------------------------------------------------------------------------
# FastAPI app factory
# ---------------------------------------------------------------------------

def build_app(bundle: Bundle):
    """Build and return a FastAPI app for the given bundle.

    Imported lazily so FastAPI is only required when serve is invoked.
    """
    from fastapi import FastAPI, HTTPException, Query
    from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
    from jinja2 import Template

    app = FastAPI(title=f"headcleaner serve: {bundle.root.name}", version="0.7.0")

    INDEX_TPL = Template("""<!doctype html>
<html><head><meta charset="utf-8"><title>{{ root.name }} — headcleaner</title>
<style>
  body { font: 14px/1.5 -apple-system, system-ui, sans-serif;
         background: #111; color: #eee; max-width: 800px; margin: 2em auto; padding: 0 1em; }
  h1 { color: #22D3EE; }
  h2 { color: #A855F7; margin-top: 2em; }
  a { color: #EC4899; text-decoration: none; }
  a:hover { text-decoration: underline; }
  .concept { border-bottom: 1px solid #333; padding: 0.5em 0; }
  .title { font-weight: bold; }
  .meta { color: #888; font-size: 0.85em; margin-left: 0.5em; }
  .pager { margin: 1em 0; }
  .pager a { padding: 0.3em 0.8em; border: 1px solid #444; border-radius: 3px; margin-right: 0.5em; }
</style></head>
<body>
  <h1>{{ root.name }}</h1>
  <p><a href="/search">search</a> · <a href="/api/concepts">JSON</a></p>
  <p>{{ total }} concept{{ '' if total == 1 else 's' }}{% if total %} ({{ from }}-{{ to }} shown){% endif %}</p>
  <h2>Concepts</h2>
  {% for c in page_concepts %}
    <div class="concept">
      <a class="title" href="/c/{{ c.relpath }}">{{ c.frontmatter.title or c.relpath }}</a>
      <span class="meta">— {{ c.frontmatter.type or '?' }}{% if c.frontmatter.status %} ({{ c.frontmatter.status }}){% endif %}</span>
    </div>
  {% else %}
    <p><em>(no concepts)</em></p>
  {% endfor %}
  <p class="pager">
    {% if page > 0 %}<a href="/?page={{ page - 1 }}">‹ prev</a>{% endif %}
    page {{ page + 1 }} of {{ total_pages }}
    {% if page + 1 < total_pages %}<a href="/?page={{ page + 1 }}">next ›</a>{% endif %}
  </p>
</body></html>
""")

    CONCEPT_TPL = Template("""<!doctype html>
<html><head><meta charset="utf-8"><title>{{ c.frontmatter.title or c.relpath }}</title>
<style>
  body { font: 14px/1.5 -apple-system, system-ui, sans-serif;
         background: #111; color: #eee; max-width: 800px; margin: 2em auto; padding: 0 1em; }
  h1, h2, h3 { color: #22D3EE; }
  a { color: #EC4899; }
  pre { background: #1a1a1a; padding: 1em; overflow-x: auto; border-radius: 4px; }
  code { background: #1a1a1a; padding: 0.1em 0.4em; border-radius: 3px; }
  blockquote { border-left: 3px solid #A855F7; margin-left: 0; padding-left: 1em; color: #bbb; }
  table { border-collapse: collapse; }
  td, th { border: 1px solid #333; padding: 0.4em 0.8em; }
  pre.frontmatter { font-size: 0.85em; color: #888; }
  pre.frontmatter span.k { color: #EC4899; }
  pre.frontmatter span.v { color: #22D3EE; }
</style></head>
<body>
  <p><a href="/">← index</a> · · <a href="/raw/{{ c.relpath }}">raw</a></p>
  <h1>{{ c.frontmatter.title or c.relpath }}</h1>
  <pre class="frontmatter">{{ fm_html }}</pre>
  <hr>
  <pre>{{ body_html }}</pre>
</body></html>
""")

    def _escape(s: str) -> str:
        return html.escape(s).replace("\n", "<br>\n")

    @app.get("/", response_class=HTMLResponse)
    async def index(page: int = Query(0, ge=0)) -> str:
        page_size = 50
        start = page * page_size
        end = min(start + page_size, bundle.total)
        page_concepts = bundle.concepts[start:end]
        total_pages = max(1, (bundle.total + page_size - 1) // page_size)
        return INDEX_TPL.render(
            root=bundle.root,
            total=bundle.total,
            from_=start + 1 if bundle.total else 0,
            to=end,
            page_concepts=page_concepts,
            page=page,
            total_pages=total_pages,
        )

    @app.get("/concepts", response_class=HTMLResponse)
    async def concepts(page: int = Query(0, ge=0)) -> str:
        return await index(page=page)

    @app.get("/c/{relpath:path}", response_class=HTMLResponse)
    async def concept(relpath: str) -> str:
        c = next((c for c in bundle.concepts if c.relpath == relpath), None)
        if c is None:
            raise HTTPException(status_code=404, detail=f"concept not found: {relpath}")
        fm_html = _escape(yaml.safe_dump(c.frontmatter, sort_keys=False).strip())
        body_html = html.escape(c.body)
        return CONCEPT_TPL.render(c=c, fm_html=fm_html, body_html=body_html)

    @app.get("/raw/{relpath:path}", response_class=PlainTextResponse)
    async def raw(relpath: str) -> str:
        c = next((c for c in bundle.concepts if c.relpath == relpath), None)
        if c is None:
            raise HTTPException(status_code=404, detail=f"concept not found: {relpath}")
        return c.path.read_text(encoding="utf-8")

    @app.get("/search")
    async def search(q: str = Query("", min_length=1)) -> HTMLResponse:
        needle = q.lower()
        matches = [
            c for c in bundle.concepts
            if needle in c.relpath.lower()
            or needle in str(c.frontmatter).lower()
            or needle in c.body.lower()
        ]
        body = (
            "<!doctype html><html><body style=\"font:14px/1.5 sans-serif;background:#111;color:#eee;max-width:800px;margin:2em auto;padding:0 1em\">"
            f"<h1 style=\"color:#22D3EE\">search: {html.escape(q)}</h1>"
            f"<p>{len(matches)} match(es)</p>"
            "<ul>"
            + "".join(
                f'<li><a style="color:#EC4899" href="/c/{c.relpath}">{html.escape(c.frontmatter.get("title") or c.relpath)}</a></li>'
                for c in matches[:50]
            )
            + "</ul></body></html>"
        )
        return HTMLResponse(body)

    @app.get("/api/concepts", response_class=JSONResponse)
    async def api_concepts() -> dict[str, Any]:
        return {
            "bundle": str(bundle.root),
            "count": bundle.total,
            "concepts": [
                {
                    "relpath": c.relpath,
                    "title": c.frontmatter.get("title"),
                    "type": c.frontmatter.get("type"),
                    "status": c.frontmatter.get("status"),
                    "verified": c.frontmatter.get("verified"),
                }
                for c in bundle.concepts
            ],
        }

    @app.get("/api/concept/{relpath:path}", response_class=JSONResponse)
    async def api_concept(relpath: str) -> dict[str, Any]:
        c = next((c for c in bundle.concepts if c.relpath == relpath), None)
        if c is None:
            raise HTTPException(status_code=404, detail=f"concept not found: {relpath}")
        return {
            "relpath": c.relpath,
            "frontmatter": c.frontmatter,
            "body": c.body,
        }

    return app


def run_serve(bundle_root: Path, host: str = "127.0.0.1", port: int = 8765) -> None:
    """Load a bundle and run the FastAPI server.

    Blocks until the user hits Ctrl+C.
    """
    import uvicorn  # type: ignore[import]

    bundle = load_bundle(bundle_root)
    app = build_app(bundle)
    uvicorn.run(app, host=host, port=port, log_level="info")