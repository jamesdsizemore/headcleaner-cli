"""headcleaner serve — local HTTP server for browsing the OKF bundle.

SKELETON (v0.4.0). Full implementation tracked in ENHANCEMENTS.md #22.

When the user runs `headcleaner serve <OKF_BUNDLE_DIR> [--port 8765]`,
this module:

1. Mounts the OKF bundle directory as a read-only file tree at `/`.
2. Serves each concept with a simple HTML page that:
   - Renders the OKF frontmatter as a definition list
   - Renders the body as rendered Markdown (via the `markdown` lib or
     just pre-rendered HTML in production)
   - Provides a small search across title + body + tags
3. Lists every concept at `/concepts` with paging.
4. Lists every directory's auto-generated index at `/<dir>/index.md`.

This module is intentionally a skeleton. To run it now:

    pip install fastapi uvicorn jinja2
    python -m headcleaner.serve <bundle_dir>

The CLI will be wired in Batch 4 once FastAPI is added as a dependency.

Routes (planned):
    GET  /                          → list of bundle root + first 20 concepts
    GET  /concepts?page=N            → paginated concept list
    GET  /c/{relpath}                → rendered single concept
    GET  /raw/{relpath}              → raw markdown of one concept
    GET  /search?q=term             → full-text search across all concepts
    GET  /{dir}/index.md             → serve auto-generated index.md
"""
from __future__ import annotations

# Planned imports (kept commented to avoid breaking the test suite that
# runs without fastapi installed):
#
# from fastapi import FastAPI, HTTPException, Query
# from fastapi.responses import HTMLResponse, FileResponse, PlainTextResponse
# from fastapi.staticfiles import StaticFiles
# from pathlib import Path
# import frontmatter   # for parsing OKF frontmatter
# import markdown      # for rendering body to HTML
#
#
# def create_app(bundle_dir: Path) -> FastAPI:
#     app = FastAPI(title="headcleaner bundle", version="0.4.0")
#     bundle = bundle_dir.resolve()
#
#     @app.get("/", response_class=HTMLResponse)
#     def root():
#         # Render an index page from the OKF index.md files
#         ...
#
#     @app.get("/concepts")
#     def concepts(page: int = Query(1, ge=1), per_page: int = Query(20, ge=1, le=100)):
#         # Paginated list of every *.md file (except index.md) under bundle/okf/
#         ...
#
#     @app.get("/c/{relpath:path}", response_class=HTMLResponse)
#     def concept(relpath: str):
#         # Render the concept's frontmatter + body as HTML
#         ...
#
#     @app.get("/raw/{relpath:path}", response_class=PlainTextResponse)
#     def raw(relpath: str):
#         # Serve the raw .md file
#         ...
#
#     @app.get("/search")
#     def search(q: str = Query(..., min_length=2)):
#         # Grep across title + body for the query term
#         ...
#
#     return app
#
#
# if __name__ == "__main__":
#     import uvicorn
#     import sys
#     bundle = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("./out/okf")
#     port = int(sys.argv[2]) if len(sys.argv) > 2 else 8765
#     app = create_app(bundle)
#     uvicorn.run(app, host="127.0.0.1", port=port)
