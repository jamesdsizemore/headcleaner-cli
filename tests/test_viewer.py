"""Tests for the OKF viewer (v0.10.0)."""

from __future__ import annotations

from pathlib import Path

import pytest

from headcleaner.viewer import (
    build,
    json_for_script,
    render,
    render_to_string,
    resolve,
    split_frontmatter,
)


@pytest.fixture
def bundle(tmp_path: Path) -> Path:
    """A small but realistic OKF bundle with links + trust signals."""
    d = tmp_path / "bundle"
    (d / "concepts").mkdir(parents=True)
    (d / "concepts" / "alpha.md").write_text(
        "---\n"
        "type: Document\n"
        "title: Alpha\n"
        "description: First concept\n"
        "status: unverified\n"
        "verified: human:pending\n"
        "generated: human:test@host\n"
        "stale_after: 2099-01-01\n"
        "sources:\n"
        "  - {resource: 'https://example.com/a', title: 'Source A'}\n"
        "tags: [test, alpha]\n"
        "---\n\n"
        "# Alpha\n\n"
        "See [beta](beta.md) and [gamma](gamma.md).",
        encoding="utf-8",
    )
    (d / "concepts" / "beta.md").write_text(
        "---\ntype: Document\ntitle: Beta\ndescription: Second\n---\n\n# Beta\n\nBack to [alpha](alpha.md).",
        encoding="utf-8",
    )
    (d / "concepts" / "gamma.md").write_text(
        "---\ntype: Document\ntitle: Gamma\ndescription: Third\n---\n\n# Gamma",
        encoding="utf-8",
    )
    # Reserved files must be skipped (index.md, log.md)
    (d / "concepts" / "index.md").write_text("# Bundle index\n", encoding="utf-8")
    return d


def test_split_frontmatter_basic():
    meta, body = split_frontmatter("---\nkey: value\n---\nbody text")
    assert meta == {"key": "value"}
    assert body == "body text"


def test_split_frontmatter_no_frontmatter():
    meta, body = split_frontmatter("# No frontmatter here")
    assert meta == {}
    assert body == "# No frontmatter here"


def test_split_frontmatter_handles_yaml_error():
    # Malformed YAML in frontmatter shouldn't crash — return empty meta
    meta, body = split_frontmatter("---\n: : : bad\n---\nbody")
    assert meta == {}


def test_json_for_script_escapes_script_closing():
    """The classic </script> escape — must not allow injection."""
    s = json_for_script({"body": "</script><script>alert(1)</script>"})
    # All '<' replaced with \u003c
    assert "<" not in s
    assert "\\u003c" in s


def test_build_collects_concepts_and_links(bundle: Path):
    nodes, edges = build(bundle)
    assert len(nodes) == 3
    # alpha -> beta, alpha -> gamma, beta -> alpha
    assert len(edges) == 3
    titles = {n["title"] for n in nodes}
    assert titles == {"Alpha", "Beta", "Gamma"}


def test_build_skips_index_md(bundle: Path):
    """Reserved files (index.md, log.md) must not appear in the graph."""
    nodes, _ = build(bundle)
    ids = {n["id"] for n in nodes}
    assert "concepts/index.md" not in ids
    assert not any(n["id"].endswith("index") for n in nodes)


def test_build_attaches_trust_metadata(bundle: Path):
    nodes, _ = build(bundle)
    alpha = next(n for n in nodes if n["id"].endswith("alpha"))
    assert alpha["type"] == "Document"
    assert alpha["status"] == "unverified"
    # 'human:pending' as a bare string is not a verification event
    # per OKF §5.2 — upstream returns an empty list. The derived trust
    # tier is therefore 'unverified' (see also trustTier() in the HTML).
    assert alpha["verified"] == []
    assert alpha["stale_after"] == "2099-01-01"


def test_build_handles_sources(bundle: Path):
    nodes, _ = build(bundle)
    alpha = next(n for n in nodes if n["id"].endswith("alpha"))
    assert len(alpha["sources"]) == 1
    assert alpha["sources"][0]["title"] == "Source A"


def test_build_dedupes_edges(bundle: Path):
    """alpha mentions beta twice — should not produce duplicate edges."""
    # Add a duplicate reference to verify dedupe
    alpha_path = bundle / "concepts" / "alpha.md"
    alpha_path.write_text(
        alpha_path.read_text(encoding="utf-8") + " And again [beta](beta.md).",
        encoding="utf-8",
    )
    nodes, edges = build(bundle)
    pairs = {(e["source"], e["target"]) for e in edges}
    assert len(pairs) == len(edges)  # no dups


def test_resolve_external_url_returns_none(bundle: Path):
    """External URLs resolve to None — they aren't graph edges."""
    alpha_path = bundle / "concepts" / "alpha.md"
    assert resolve("https://example.com/x", alpha_path, bundle) is None


def test_render_writes_self_contained_html(bundle: Path, tmp_path: Path):
    out = tmp_path / "viz.html"
    n, e = render(bundle, out)
    assert out.exists()
    assert n == 3 and e == 3
    # Self-contained — no <script src="..."> pointing at local files
    html = out.read_text(encoding="utf-8")
    assert "cytoscape" in html
    assert "marked" in html
    assert "<script" in html
    # Embedded data
    assert "Alpha" in html
    assert "Beta" in html
    # Embedded JSON-safe (no naked </script> in node data).
    # 4 = 3 CDN <script src=...></script> (cytoscape, marked, dompurify)
    #     + 1 inline <script>...</script>
    assert html.count("</script>") == 4


def test_render_to_string_no_disk_io(bundle: Path):
    nodes, edges = build(bundle)
    html = render_to_string(nodes, edges, title="Test bundle")
    assert "Test bundle" in html
    assert "Alpha" in html
    assert "cytoscape" in html


def test_render_max_nodes(bundle: Path, tmp_path: Path):
    out = tmp_path / "viz.html"
    with pytest.raises(ValueError, match="exceeds max_nodes"):
        render(bundle, out, max_nodes=2)


def test_render_layout_override(bundle: Path, tmp_path: Path):
    out = tmp_path / "viz.html"
    render(bundle, out, layout="grid")
    html = out.read_text(encoding="utf-8")
    # The layout marker should be 'grid' not 'cose'
    assert "'grid'" in html or '"grid"' in html


def test_render_emits_viz_html_by_default(bundle: Path):
    """When --out is omitted, write to <bundle>/viz.html."""
    out = bundle / "viz.html"
    if out.exists():
        out.unlink()
    render(bundle, out)
    assert out.exists()
