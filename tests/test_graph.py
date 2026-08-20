from __future__ import annotations

import json
from pathlib import Path

from headcleaner.chunking import Chunk, write_chunks


def test_graph_builds_evidence_linked_containment_and_traversal(tmp_path: Path) -> None:
    from headcleaner.graph import build_graph, query_graph

    bundle = tmp_path / "bundle"
    bundle.mkdir()
    write_chunks(
        bundle,
        [
            Chunk(
                "a" * 64,
                "alpha.md",
                "b" * 64,
                ("e",),
                0,
                (),
                "text",
                {
                    "source_uri": "file:///a",
                    "source_sha256": "b" * 64,
                    "page": None,
                    "start": None,
                    "end": None,
                },
                1,
            )
        ],
    )
    graph = build_graph(bundle)

    assert all(edge.status in {"explicit", "unverified"} for edge in graph.edges)
    assert all(edge.evidence_chunk_ids or edge.kind == "contains" for edge in graph.edges)
    assert query_graph(graph, "concept:alpha.md", depth=1)["edges"]


def test_graph_rejects_out_of_contract_node_and_edge_kinds() -> None:
    import pytest

    from headcleaner.graph import GraphEdge, GraphNode

    with pytest.raises(ValueError, match="graph node kind"):
        GraphNode("bad", "claim_candidate", "bad", (), {})
    with pytest.raises(ValueError, match="graph edge kind"):
        GraphEdge("bad", "references", "a", "b", (), "test", "unverified")
    assert GraphEdge("candidate", "related_to", "a", "b", ("chunk",), "test", "unverified")


def test_graph_captures_explicit_markdown_cross_reference_with_cited_evidence(
    tmp_path: Path,
) -> None:
    from headcleaner.graph import build_graph

    bundle = tmp_path / "bundle"
    bundle.mkdir()
    write_chunks(
        bundle,
        [
            Chunk(
                "a" * 64,
                "alpha.md",
                "b" * 64,
                ("e",),
                0,
                (),
                "See [Beta](beta.md) for details.",
                {
                    "source_uri": "file:///a",
                    "source_sha256": "b" * 64,
                    "page": None,
                    "start": None,
                    "end": None,
                },
                5,
            ),
            Chunk(
                "c" * 64,
                "beta.md",
                "d" * 64,
                ("f",),
                0,
                (),
                "Beta details.",
                {
                    "source_uri": "file:///b",
                    "source_sha256": "d" * 64,
                    "page": None,
                    "start": None,
                    "end": None,
                },
                2,
            ),
        ],
    )

    graph = build_graph(bundle)

    assert any(
        edge.kind == "mentions"
        and edge.from_id == "concept:alpha.md"
        and edge.to_id == "concept:beta.md"
        and edge.evidence_chunk_ids == ("a" * 64,)
        and edge.status == "explicit"
        for edge in graph.edges
    )


def test_graph_links_only_unverified_claim_candidates_without_value_leakage(tmp_path: Path) -> None:
    from headcleaner.graph import build_graph

    bundle = tmp_path / "bundle"
    bundle.mkdir()
    write_chunks(
        bundle,
        [
            Chunk(
                "a" * 64,
                "alpha.md",
                "b" * 64,
                ("e",),
                0,
                (),
                "Owner: Jane Doe",
                {
                    "source_uri": "file:///a",
                    "source_sha256": "b" * 64,
                    "page": None,
                    "start": None,
                    "end": None,
                },
                1,
            )
        ],
    )
    (bundle / "claim-review.json").write_text(
        json.dumps(
            {
                "claims": [
                    {
                        "id": "candidate",
                        "kind": "owner",
                        "source_chunk_id": "a" * 64,
                        "citation": {"source_sha256": "b" * 64},
                        "extraction_rule": "claims/owner",
                        "status": "unverified",
                        "normalized_value": "jane doe",
                    },
                    {
                        "id": "suppressed",
                        "kind": "owner",
                        "source_chunk_id": "a" * 64,
                        "citation": {"source_sha256": "b" * 64},
                        "extraction_rule": "claims/owner",
                        "status": "suppressed",
                        "normalized_value": "private value",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    graph = build_graph(bundle)

    assert "claim:candidate" in {node.id for node in graph.nodes}
    assert "claim:suppressed" not in {node.id for node in graph.nodes}
    claim_node = next(node for node in graph.nodes if node.id == "claim:candidate")
    assert claim_node.kind == "topic"
    assert claim_node.attributes["classification"] == "claim_candidate"
    serialized = json.dumps([node.__dict__ for node in graph.nodes])
    assert "jane doe" not in serialized
    assert "private value" not in serialized


def test_graph_filter_excludes_policy_selected_edge_kinds(tmp_path: Path) -> None:
    from headcleaner.graph import build_graph, filter_graph

    bundle = tmp_path / "bundle"
    bundle.mkdir()
    write_chunks(
        bundle,
        [
            Chunk(
                "a" * 64,
                "alpha.md",
                "b" * 64,
                ("e",),
                0,
                (),
                "See [Beta](beta.md).",
                {
                    "source_uri": "file:///a",
                    "source_sha256": "b" * 64,
                    "page": None,
                    "start": None,
                    "end": None,
                },
                1,
            ),
            Chunk(
                "c" * 64,
                "beta.md",
                "d" * 64,
                ("f",),
                0,
                (),
                "Beta.",
                {
                    "source_uri": "file:///b",
                    "source_sha256": "d" * 64,
                    "page": None,
                    "start": None,
                    "end": None,
                },
                1,
            ),
        ],
    )

    filtered = filter_graph(build_graph(bundle), {"mentions"})

    assert filtered.nodes
    assert all(edge.kind != "mentions" for edge in filtered.edges)


def test_graph_emits_unverified_cited_entity_and_heading_topic_suggestions(tmp_path: Path) -> None:
    from headcleaner.graph import build_graph

    bundle = tmp_path / "bundle"
    bundle.mkdir()
    write_chunks(
        bundle,
        [
            Chunk(
                "a" * 64,
                "alpha.md",
                "b" * 64,
                ("e",),
                0,
                ("Project Atlas",),
                "Project Atlas was reviewed by Ada Lovelace.",
                {
                    "source_uri": "file:///a",
                    "source_sha256": "b" * 64,
                    "page": None,
                    "start": None,
                    "end": None,
                },
                1,
            )
        ],
    )

    graph = build_graph(bundle)
    suggested = [edge for edge in graph.edges if edge.status == "unverified"]

    assert {node.kind for node in graph.nodes} >= {"entity", "topic"}
    assert suggested
    assert all(edge.evidence_chunk_ids == ("a" * 64,) for edge in suggested)


def test_graph_cli_kind_filter_returns_only_matching_edges(tmp_path: Path) -> None:
    from click.testing import CliRunner

    from headcleaner.chunking import Chunk, write_chunks
    from headcleaner.cli import cli

    bundle = tmp_path / "bundle"
    bundle.mkdir()
    write_chunks(
        bundle,
        [
            Chunk(
                "a" * 64,
                "alpha.md",
                "b" * 64,
                ("e",),
                0,
                ("Project Atlas",),
                "Project Atlas was reviewed by Ada Lovelace.",
                {
                    "source_uri": "file:///a",
                    "source_sha256": "b" * 64,
                    "page": None,
                    "start": None,
                    "end": None,
                },
                1,
            )
        ],
    )

    runner = CliRunner()
    all_edges = json.loads(
        runner.invoke(
            cli, ["graph", str(bundle), "--node", "concept:alpha.md", "--depth", "2", "--json"]
        ).output
    )["edges"]
    mentions_only = json.loads(
        runner.invoke(
            cli,
            [
                "graph",
                str(bundle),
                "--node",
                "concept:alpha.md",
                "--depth",
                "2",
                "--kind",
                "mentions",
                "--json",
            ],
        ).output
    )["edges"]
    contains_only = json.loads(
        runner.invoke(
            cli,
            [
                "graph",
                str(bundle),
                "--node",
                "concept:alpha.md",
                "--depth",
                "2",
                "--kind",
                "contains",
                "--json",
            ],
        ).output
    )["edges"]

    assert all_edges, "expected graph query to surface at least one edge"
    assert mentions_only and all(edge["kind"] == "mentions" for edge in mentions_only)
    assert all(edge["kind"] == "contains" for edge in contains_only)
    assert {edge["kind"] for edge in all_edges} >= {"mentions", "contains"}
