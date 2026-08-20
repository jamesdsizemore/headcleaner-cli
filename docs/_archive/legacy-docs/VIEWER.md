# `headcleaner view` — OKF bundle viewer

Render an OKF bundle as a **single self-contained interactive HTML graph**. No backend, no service, no data leaves the page — open `viz.html` in any browser.

Adopted from [`scaccogatto/okf-skills`](https://github.com/scaccogatto/okf-skills) (MIT, 312 stars). Vendored in [`src/headcleaner/viewer.py`](../src/headcleaner/viewer.py).

## Usage

```bash
# Default: writes <bundle>/viz.html
headcleaner view ./out/okf

# Custom output path
headcleaner view ./out/okf -o /tmp/knowledge-graph.html

# Open in default browser after rendering
headcleaner view ./out/okf --open

# Serve on a local HTTP server (Ctrl+C to stop)
headcleaner view ./out/okf --serve --port 8765

# Override layout (default: cose for <1000 concepts, concentric for larger)
headcleaner view ./out/okf --layout breadthfirst

# Set a title + source link for the header
headcleaner view ./out/okf -t "Team knowledge graph" -l "https://github.com/me/repo"

# CI guard: refuse to render huge bundles
headcleaner view ./out/okf --max-nodes 5000
```

## What the viewer shows

- **Graph view** — concepts as nodes, colored by `type`, sized by body length. Edges are markdown links + `sources[].resource` references to other concepts in the bundle.
- **Detail panel** — click any node to see:
  - Rendered Markdown body (with DOMPurify-sanitized HTML)
  - OKF v0.2 trust tier badge: `unverified` / `machine-confirmed` / `human-reviewed` (derived from `verified[].by` prefix)
  - Status, generated, verified, stale_after
  - Sources (with citation count + window)
  - "Links to" / "Cited by" backlinks (graph neighbors)
  - Tags, type chip
- **Layout switcher** — force (cose), concentric, breadth-first, circle, grid
- **Per-type filter** — click legend chips to hide/show types
- **Free-text search** — matches title + type + description + tags
- **Neighbour highlight** — clicking a node dims everything except its neighborhood

## Programmatic API

```python
from headcleaner.viewer import render, build, split_frontmatter

# Render to a file
n, e = render(Path("./okf"), Path("viz.html"), layout="cose")
print(f"rendered {n} concepts, {e} edges")

# Reuse the parser from Python
nodes, edges = build(Path("./okf"))
for n in nodes:
    print(f"{n['id']}: {n['title']} ({n['type']}) — verified={n['verified']}")
```

## Limitations

- Force (cose) layout freezes the page on >2k concepts. Above 1000 concepts the default switches to `concentric` automatically; you can override with `--layout cose` (browser will confirm).
- Above 5000 concepts the page is slow on any layout (measured ~27s load, ~650 MB heap in Chrome) and reads as a hairball. Use `--max-nodes` in CI or render a subtree.
- The viewer relies on `cdn.jsdelivr.net` for cytoscape.js, marked.js, DOMPurify. For air-gapped use, replace the `<script src>` URLs in the rendered HTML with local copies.

## License + attribution

The HTML/CSS/JS template is byte-identical to the upstream `okf_visualize.py` from `scaccogatto/okf-skills`. See the docstring at the top of `src/headcleaner/viewer.py` for the full MIT notice.
