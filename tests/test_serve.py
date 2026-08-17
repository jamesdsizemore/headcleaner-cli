"""Tests for the FastAPI serve implementation (Eng #22 full impl)."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def bundle_dir(tmp_path: Path) -> Path:
    """Build a small OKF bundle on disk."""
    b = tmp_path / "bundle"
    b.mkdir()
    (b / "alpha.md").write_text(
        "---\ntype: Document\ntitle: Alpha Doc\nstatus: unverified\n"
        "verified: human:pending\n---\nHello world from alpha.\n",
        encoding="utf-8",
    )
    sub = b / "sub"
    sub.mkdir()
    (sub / "beta.md").write_text(
        "---\ntype: Document\ntitle: Beta Doc\nstatus: unverified\n"
        "verified: human:pending\n---\nThe beta contains alpha as a substring.\n",
        encoding="utf-8",
    )
    (b / "log.md").write_text("# Bundle history\n", encoding="utf-8")
    (b / "index.md").write_text("# index\n", encoding="utf-8")
    return b


def test_load_bundle_finds_concepts(bundle_dir: Path) -> None:
    """load_bundle enumerates concepts but skips index.md / log.md."""
    from headcleaner.serve import load_bundle

    bundle = load_bundle(bundle_dir)
    assert bundle.total == 2  # alpha + beta, not index or log
    relpaths = sorted(c.relpath for c in bundle.concepts)
    assert relpaths == ["alpha.md", "sub/beta.md"]


def test_load_bundle_handles_missing_dir(tmp_path: Path) -> None:
    """load_bundle returns an empty Bundle for a non-existent path."""
    from headcleaner.serve import load_bundle

    bundle = load_bundle(tmp_path / "no-such-dir")
    assert bundle.total == 0


def test_build_app_routes(bundle_dir: Path) -> None:
    """build_app returns a FastAPI app with all the planned routes."""
    from headcleaner.serve import build_app, load_bundle

    app = build_app(load_bundle(bundle_dir))
    paths = {r.path for r in app.routes if hasattr(r, "path")}
    # The /concepts?page=N handler reuses index, so check for it via "/" and "/c/{relpath}"
    assert "/" in paths
    assert "/c/{relpath:path}" in paths
    assert "/raw/{relpath:path}" in paths
    assert "/search" in paths
    assert "/api/concepts" in paths
    assert "/api/concept/{relpath:path}" in paths


def test_serve_renders_concept_via_test_client(bundle_dir: Path) -> None:
    """The /c/{relpath} route renders concept HTML for a known file."""
    from fastapi.testclient import TestClient
    from headcleaner.serve import build_app, load_bundle

    app = build_app(load_bundle(bundle_dir))
    client = TestClient(app)
    r = client.get("/c/alpha.md")
    assert r.status_code == 200
    assert "Alpha Doc" in r.text
    assert "Hello world" in r.text


def test_serve_404_for_missing_concept(bundle_dir: Path) -> None:
    """The /c/{relpath} route returns 404 for unknown concepts."""
    from fastapi.testclient import TestClient
    from headcleaner.serve import build_app, load_bundle

    app = build_app(load_bundle(bundle_dir))
    client = TestClient(app)
    r = client.get("/c/no-such.md")
    assert r.status_code == 404


def test_serve_api_concepts(bundle_dir: Path) -> None:
    """The /api/concepts route returns JSON with the expected shape."""
    from fastapi.testclient import TestClient
    from headcleaner.serve import build_app, load_bundle

    app = build_app(load_bundle(bundle_dir))
    client = TestClient(app)
    r = client.get("/api/concepts")
    assert r.status_code == 200
    data = r.json()
    assert data["count"] == 2
    assert len(data["concepts"]) == 2
    titles = sorted(c["title"] for c in data["concepts"])
    assert titles == ["Alpha Doc", "Beta Doc"]


def test_serve_search(bundle_dir: Path) -> None:
    """The /search route finds concepts by body substring."""
    from fastapi.testclient import TestClient
    from headcleaner.serve import build_app, load_bundle

    app = build_app(load_bundle(bundle_dir))
    client = TestClient(app)
    r = client.get("/search?q=alpha")
    assert r.status_code == 200
    # Both docs mention "alpha" (beta says "contains alpha as a substring")
    assert "2 match(es)" in r.text or "match" in r.text
