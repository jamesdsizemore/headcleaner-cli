"""Evidence-linked, rebuildable graph derivative for chunked OKF bundles."""

from __future__ import annotations

import hashlib
import json
import os
import posixpath
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .chunking import read_chunks

_MARKDOWN_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
_ENTITY_RE = re.compile(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b")


@dataclass(frozen=True)
class GraphNode:
    id: str
    kind: str
    label: str
    source_refs: tuple[str, ...]
    attributes: dict[str, Any]

    def __post_init__(self) -> None:
        if self.kind not in {"concept", "chunk", "entity", "topic"}:
            raise ValueError("graph node kind must be concept, chunk, entity, or topic")


@dataclass(frozen=True)
class GraphEdge:
    id: str
    kind: str
    from_id: str
    to_id: str
    evidence_chunk_ids: tuple[str, ...]
    method: str
    status: str

    def __post_init__(self) -> None:
        if self.kind not in {
            "contains",
            "cites",
            "mentions",
            "related_to",
            "duplicate_candidate",
            "conflicts_candidate",
        }:
            raise ValueError("graph edge kind must be a supported contract kind")
        if self.status not in {"explicit", "unverified"}:
            raise ValueError("graph edge status must be explicit or unverified")
        if self.kind != "contains" and not self.evidence_chunk_ids:
            raise ValueError("graph edge requires evidence chunk ids")


@dataclass(frozen=True)
class Graph:
    nodes: tuple[GraphNode, ...]
    edges: tuple[GraphEdge, ...]


def filter_graph(graph: Graph, excluded_edge_kinds: set[str]) -> Graph:
    """Return a derived view with policy-excluded relationships removed."""
    return Graph(
        graph.nodes,
        tuple(edge for edge in graph.edges if edge.kind not in excluded_edge_kinds),
    )


def filter_graph_for_bundle_policy(graph: Graph, bundle_root: Path) -> Graph:
    """Apply the bundle-local graph policy without mutating graph.jsonl."""
    policy_path = bundle_root / ".headcleaner" / "policy.toml"
    if not policy_path.is_file():
        return graph
    from .policy import Policy

    return filter_graph(graph, Policy.load(policy_path).graph_excluded_edge_kinds)


def _id(*values: str) -> str:
    return hashlib.sha256("\0".join(values).encode()).hexdigest()


def _suggestion_id(kind: str, label: str) -> str:
    normalized = " ".join(label.split()).casefold()
    return f"{kind}:{_id(kind, normalized)}"


def build_graph(bundle_root: Path) -> Graph:
    nodes: dict[str, GraphNode] = {}
    edges: list[GraphEdge] = []
    references: list[tuple[str, str, str]] = []
    for chunk in read_chunks(bundle_root):
        concept_id = f"concept:{chunk.concept_id}"
        chunk_id = f"chunk:{chunk.id}"
        nodes.setdefault(
            concept_id,
            GraphNode(concept_id, "concept", chunk.concept_id, (chunk.source_sha256,), {}),
        )
        nodes[chunk_id] = GraphNode(
            chunk_id, "chunk", chunk.id, (chunk.source_sha256,), {"citation": chunk.citation}
        )
        edges.append(
            GraphEdge(
                _id("contains", concept_id, chunk_id),
                "contains",
                concept_id,
                chunk_id,
                (),
                "canonical_chunks/v1",
                "explicit",
            )
        )
        source_id = f"source:{chunk.source_sha256}"
        nodes.setdefault(
            source_id,
            GraphNode(source_id, "topic", chunk.source_sha256, (chunk.source_sha256,), {}),
        )
        edges.append(
            GraphEdge(
                _id("cites", chunk_id, source_id),
                "cites",
                chunk_id,
                source_id,
                (chunk.id,),
                "canonical_chunks/v1",
                "explicit",
            )
        )
        for label in chunk.heading_path[-1:]:
            topic_id = _suggestion_id("topic", label)
            nodes.setdefault(
                topic_id,
                GraphNode(topic_id, "topic", label, (chunk.source_sha256,), {"label": label}),
            )
            edges.append(
                GraphEdge(
                    _id("mentions", chunk_id, topic_id, chunk.id),
                    "mentions",
                    chunk_id,
                    topic_id,
                    (chunk.id,),
                    "heading_topic/v1",
                    "unverified",
                )
            )
        for label in sorted(set(_ENTITY_RE.findall(chunk.text))):
            entity_id = _suggestion_id("entity", label)
            nodes.setdefault(
                entity_id,
                GraphNode(entity_id, "entity", label, (chunk.source_sha256,), {"label": label}),
            )
            edges.append(
                GraphEdge(
                    _id("mentions", chunk_id, entity_id, chunk.id),
                    "mentions",
                    chunk_id,
                    entity_id,
                    (chunk.id,),
                    "capitalized_entity/v1",
                    "unverified",
                )
            )
        for target in _MARKDOWN_LINK_RE.findall(chunk.text):
            target = target.split("#", 1)[0]
            if not target or "://" in target:
                continue
            target_path = posixpath.normpath(
                posixpath.join(posixpath.dirname(chunk.concept_id), target)
            )
            references.append((concept_id, target_path, chunk.id))
    for from_id, target_path, chunk_id in references:
        to_id = f"concept:{target_path}"
        if from_id == to_id or to_id not in nodes:
            continue
        edges.append(
            GraphEdge(
                _id("mentions", from_id, to_id, chunk_id),
                "mentions",
                from_id,
                to_id,
                (chunk_id,),
                "markdown_link/v1",
                "explicit",
            )
        )
    claim_review = bundle_root / "claim-review.json"
    if claim_review.exists():
        data = json.loads(claim_review.read_text(encoding="utf-8"))
        for claim in data.get("claims", []):
            if claim.get("status") != "unverified":
                continue
            source_chunk_id = f"chunk:{claim.get('source_chunk_id', '')}"
            if source_chunk_id not in nodes:
                continue
            claim_id = f"claim:{claim['id']}"
            nodes[claim_id] = GraphNode(
                claim_id,
                "topic",
                f"claim:{claim.get('kind', 'unknown')}",
                (str(claim["citation"].get("source_sha256", "")),),
                {
                    "classification": "claim_candidate",
                    "extraction_rule": claim.get("extraction_rule"),
                    "status": "unverified",
                },
            )
            edges.append(
                GraphEdge(
                    _id("related_to", source_chunk_id, claim_id, str(claim["id"])),
                    "related_to",
                    source_chunk_id,
                    claim_id,
                    (str(claim["source_chunk_id"]),),
                    "claims_candidate/v1",
                    "unverified",
                )
            )
    return Graph(
        tuple(nodes[key] for key in sorted(nodes)), tuple(sorted(edges, key=lambda edge: edge.id))
    )


def write_graph(bundle_root: Path, graph: Graph) -> Path:
    path = bundle_root / "graph.jsonl"
    rows = [{"record": "node", **node.__dict__} for node in graph.nodes] + [
        {"record": "edge", **edge.__dict__} for edge in graph.edges
    ]
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", delete=False, dir=bundle_root
    ) as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, default=list) + "\n")
        temporary = Path(handle.name)
    os.replace(temporary, path)
    return path


def query_graph(
    graph: Graph, node_id: str, *, depth: int = 1, kind: str | None = None
) -> dict[str, Any]:
    if depth < 0:
        raise ValueError("depth must be non-negative")
    seen = {node_id}
    frontier = {node_id}
    selected: list[GraphEdge] = []
    for _ in range(depth):
        next_frontier: set[str] = set()
        for edge in graph.edges:
            if edge.from_id in frontier:
                if not kind or edge.kind == kind:
                    selected.append(edge)
                # Traversal must follow all outgoing edges regardless of kind filter;
                # the filter only restricts what is returned.
                next_frontier.add(edge.to_id)
        seen.update(next_frontier)
        frontier = next_frontier
    return {
        "nodes": [
            {
                **node.__dict__,
                "source_refs": list(node.source_refs),
            }
            for node in graph.nodes
            if node.id in seen
        ],
        "edges": [
            {
                **edge.__dict__,
                "evidence_chunk_ids": list(edge.evidence_chunk_ids),
            }
            for edge in selected
        ],
    }
