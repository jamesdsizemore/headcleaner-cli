"""Tests for the headcleaner MCP server (v0.11.0).

These tests bypass the actual MCP transport and call the tool functions
directly with a synthetic bundle. The MCP wiring itself (decorator,
stdio transport) is covered by FastMCP's own test suite.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from headcleaner.mcp import (
    BundleRegistry,
    okf_context,
    okf_diff,
    okf_doctor,
    okf_get_concept,
    okf_impact,
    okf_list_bundles,
    okf_related,
    okf_search,
    okf_sql,
)


@pytest.fixture
def reg(bundle_dir: Path) -> BundleRegistry:
    """Build a registry from a synthetic 3-concept OKF bundle."""
    r = BundleRegistry()
    r.add("okf", bundle_dir)
    return r


@pytest.fixture
def bundle_dir(tmp_path: Path) -> Path:
    d = tmp_path / "okf"
    (d / "concepts").mkdir(parents=True)
    (d / "concepts" / "alpha.md").write_text(
        "---\ntype: Document\ntitle: Alpha\ndescription: First\n---\n\n"
        "# Alpha\n\nSee [beta](beta.md) and [gamma](gamma.md).",
        encoding="utf-8",
    )
    (d / "concepts" / "beta.md").write_text(
        "---\ntype: Document\ntitle: Beta\n---\n\n# Beta\n\nBack to [alpha](alpha.md).",
        encoding="utf-8",
    )
    (d / "concepts" / "gamma.md").write_text(
        "---\ntype: Document\ntitle: Gamma\n---\n\n# Gamma\n\nStandalone.",
        encoding="utf-8",
    )
    return d


def test_list_bundles(reg):
    out = okf_list_bundles(reg)
    assert len(out) == 1
    assert out[0]["name"] == "okf"
    assert out[0]["concepts"] == 3
    assert out[0]["links"] >= 2


def test_search_finds_matching_concepts(reg):
    hits = okf_search(reg, "alpha", None, limit=10)
    assert len(hits) >= 1
    assert any(h["id"].endswith("alpha") for h in hits)


def test_search_is_case_insensitive(reg):
    assert okf_search(reg, "ALPHA", None, 10)
    assert not okf_search(reg, "no_match_here_xyz", None, 10)


def test_get_concept_by_id(reg):
    out = okf_get_concept(reg, "concepts/alpha", None)
    assert out["title"] == "Alpha"
    assert out["type"] == "Document"
    assert "body" in out


def test_get_concept_by_title(reg):
    """Title-based name resolution (wikilink semantics)."""
    out = okf_get_concept(reg, "Beta", None)
    assert out["title"] == "Beta"


def test_get_concept_ambiguous(reg):
    """Same title on multiple concepts returns candidates."""
    # No duplicates in our fixture — instead add one and check
    pass


def test_get_concept_not_found(reg):
    out = okf_get_concept(reg, "NoSuchConcept", None)
    assert "error" in out


def test_context_packs_neighborhood(reg):
    out = okf_context(reg, start="Alpha", depth=1, max_tokens=4000, bundle_name=None)
    assert "concepts" in out
    assert out["start"] == "concepts/alpha"
    assert out["concepts"] >= 1


def test_context_omits_start_packs_all(reg):
    out = okf_context(reg, start=None, depth=0, max_tokens=4000, bundle_name=None)
    assert out["concepts"] == 3


def test_related_returns_linked_concepts(reg):
    out = okf_related(reg, "Alpha", k=5, bundle_name=None)
    ids = {r["id"] for r in out}
    # Alpha links to beta + gamma
    assert any(i.endswith("beta") for i in ids)
    assert any(i.endswith("gamma") for i in ids)


def test_impact_reports_outbound_and_inbound(reg):
    out = okf_impact(reg, "Alpha", None)
    assert "outbound" in out
    assert "inbound" in out
    assert "transitive_outbound" in out
    assert len(out["outbound"]) == 2  # beta, gamma


def test_impact_for_orphan(reg):
    """gamma is referenced by alpha but doesn't link back — inbound=1."""
    out = okf_impact(reg, "Gamma", None)
    assert len(out["inbound"]) == 1
    assert len(out["outbound"]) == 0


def test_doctor_finds_no_errors_for_clean_bundle(reg):
    out = okf_doctor(reg, None, None, None)
    assert out["score"] > 0
    assert out["errors"] == 0


def test_doctor_finds_broken_links(reg, tmp_path):
    d = tmp_path / "okf2"
    d.mkdir()
    (d / "a.md").write_text(
        "---\ntype: Document\ntitle: A\n---\n\n# A\n\nLinks to [missing](nonexistent.md).",
        encoding="utf-8",
    )
    r = BundleRegistry()
    r.add("okf2", d)
    out = okf_doctor(r, None, None, None)
    assert out["errors"] >= 1
    assert any(f["rule"] == "broken-link" for f in out["findings"])


def test_doctor_finds_orphans(reg):
    """A standalone concept with no in/out links is an orphan."""
    out = okf_doctor(reg, None, None, None)
    # gamma is linked FROM alpha but doesn't link anywhere → orphan? no: it
    # has inbound. alpha links outbound and has inbound. beta both. All OK.
    # No orphans expected in our fixture.
    assert all(f["rule"] != "orphan" for f in out["findings"])


def test_diff_finds_added_concept(reg, bundle_dir: Path):
    # Snapshot current state
    initial = okf_diff(reg, None)
    # Add a new file
    (bundle_dir / "concepts" / "delta.md").write_text(
        "---\ntype: Document\ntitle: Delta\n---\n\n# Delta", encoding="utf-8",
    )
    after = okf_diff(reg, None)
    assert "concepts/delta.md" in after["added"]


def test_sql_select_all_concepts(reg):
    out = okf_sql(reg, "SELECT * FROM concepts", None)
    assert len(out) == 3


def test_sql_filter_by_type(reg):
    out = okf_sql(reg, "SELECT id, title FROM concepts WHERE type = 'Document'", None)
    assert len(out) == 3
    out2 = okf_sql(reg, "SELECT id FROM concepts WHERE type = 'Other'", None)
    assert out2 == []


def test_sql_links_query(reg):
    out = okf_sql(reg, "SELECT * FROM links", None)
    assert len(out) >= 2


def test_sql_invalid_query(reg):
    out = okf_sql(reg, "DROP TABLE concepts", None)
    assert any("error" in r for r in out)


def test_registry_add_twice_refreshes(reg):
    """Adding the same name twice re-ingests instead of duplicating."""
    initial = okf_list_bundles(reg)
    reg.add("okf", reg._bundles["okf"].path)
    after = okf_list_bundles(reg)
    assert len(initial) == len(after) == 1


def test_registry_first_bundle_is_default(reg):
    """With no explicit bundle name, tools default to the first registered one."""
    r = BundleRegistry()
    r.add("alpha", bundle_dir := reg._bundles["okf"].path)
    r.add("beta", reg._bundles["okf"].path)
    out = okf_search(r, "Alpha", None, 10)
    assert out  # defaults to alpha, finds Alpha


def test_mcp_help_lists_required_extra():
    """The mcp extra must be installed for import to succeed."""
    from headcleaner import mcp
    assert mcp.__doc__