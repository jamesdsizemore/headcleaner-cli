# Graph development

This page documents headcleaner's evidence-linked knowledge graph. It covers the data model, the build semantics, the bounded vocabulary, and the integration with the claim and report pipelines.

## The graph module

The graph module lives in `src/headcleaner/graph.py`. The entry points are `build_graph`, `query_graph`, `filter_graph`, `write_graph`, and `filter_graph_for_bundle_policy`.

## The data model

The graph is a small, bounded set of node and edge kinds. The vocabulary is enforced at construction; any other kind is rejected with a `ValueError`.

### Node kinds

- `concept` — a canonical concept in the OKF bundle. The node ID is `concept:<bundle-relative-path>`.
- `chunk` — a cited chunk. The node ID is `chunk:<chunk-id>`.
- `entity` — a named thing mentioned in a chunk (e.g. a person, a project). The node ID is `entity:<sha256-of-normalized-label>`.
- `topic` — a heading topic derived from a chunk's heading path. The node ID is `topic:<sha256-of-normalized-heading>`.

### Edge kinds

- `contains` — concept-to-chunk containment. The only edge kind that may omit `evidence_chunk_ids`.
- `cites` — chunk-to-source citation. Evidence is the chunk ID itself.
- `mentions` — chunk-to-entity or chunk-to-topic mention. Evidence is the chunk that mentions.
- `related_to` — claim-to-topic review linkage. Evidence is the cited claim candidate's chunk.
- `duplicate_candidate` — concept-to-concept near-duplicate suggestion. Evidence is the candidate pair's chunks.
- `conflicts_candidate` — concept-to-concept claim-conflict suggestion. Evidence is the conflict pair's citations.

### Status

Every edge has a `status` of exactly `explicit` or `unverified`. Explicit edges come from human-authored cross-references or deterministic containment/citation; unverified edges are suggestions produced by the graph builder. Downstream tools must not treat `unverified` edges as factual claims.

## Build semantics

`build_graph(bundle_root)` reads the canonical chunks and concepts, derives containment and citation edges deterministically, extracts entity and topic mentions from chunk text, and produces the full graph in memory.

The builder never overwrites a user-authored explicit cross-reference with a generated edge. If a concept contains an explicit Markdown link to another concept, that link is emitted as a `mentions` edge with `status: explicit` and the originating chunk ID as evidence. Generated mention edges have `status: unverified`.

### Entity and topic extraction

Entities are derived from capitalized-name detection in chunk text. The detection is conservative: only multi-word capitalized phrases and known proper-noun patterns are emitted. The implementation normalizes the label, hashes it, and uses the hash as the node ID. Topics are derived from chunk heading paths; the first heading in the path becomes the topic label.

Both derivations are deterministic: the same input produces the same nodes and edges across reruns. The builder records its version as `method: canonical_chunks/v1`.

### Claim linkage

After the canonical chunks are processed, the builder reads the claim-review derivative and links unverified claim candidates as `related_to` edges to topic nodes. Suppressed claims are omitted. The linkage is rebuilt every time the graph is built; there is no separate "claim graph" derivative.

## Query semantics

`query_graph(graph, node_id, depth=N, kind=K)` walks the graph from the given node to depth N, optionally restricted to edges of kind K. The traversal follows outgoing edges regardless of the kind filter; the kind filter restricts what is returned, not what is traversed. This is the property that makes `--kind mentions` return mention edges reachable from the starting node without trapping the search at depth 0.

The returned dict has `nodes` and `edges` lists, each with all dataclass fields plus list-ified tuples for JSON safety.

## Policy filtering

`filter_graph(graph, excluded_edge_kinds)` returns a new graph with edges of the given kinds removed. `filter_graph_for_bundle_policy(graph, bundle_root)` loads the policy from `<bundle>/.headcleaner/policies/` and filters using its `graph.exclude_edge_kinds` setting.

The filter is non-destructive: the original graph is unchanged, and the chunks used to build it are unchanged. The filter only affects what is written to the derivative and what queries return.

## ASCII: graph build pipeline

```text
canonical chunks + concepts + claim-review derivative
                  |
                  v
        +-------------------+
        | containment edges |  concept -> chunk (status=explicit)
        +-------------------+
                  |
                  v
        +-------------------+
        | citation edges    |  chunk -> source (status=explicit)
        +-------------------+
                  |
                  v
        +-------------------+
        | mention edges     |  chunk -> entity|topic (status=unverified)
        +-------------------+
                  |
                  v
        +-------------------+
        | explicit links    |  concept -> concept (status=explicit)
        +-------------------+
                  |
                  v
        +-------------------+
        | claim linkage     |  topic -> topic (status=unverified, kind=related_to)
        +-------------------+
                  |
                  v
            Graph (nodes + edges)
                  |
                  v
        filter by policy.exclude_edge_kinds
                  |
                  v
        write graph.jsonl atomically
```

## Emission

`write_graph(bundle_root, graph)` writes `graph.jsonl` to the OKF bundle. The write is atomic through temp+rename. Each line is a JSON object with one node or one edge.

## Integration with reports

The graph is summarized in the conversion report's "Evidence graph" section. The section lists the node count, the edge count, and the path to the derivative. The pipeline records the same metadata in the run manifest's `options.graph` field.

## What to read next

The [canonical model developer guide](canonical-model.md) documents the `GraphNode` and `GraphEdge` dataclasses. The [claims and policy developer guide](claims-and-policy.md) covers the claim-review derivative that the graph links into. The [MCP tool reference](../reference/mcp-tool-reference.md) documents the `okf_graph` and `okf_impact` tools.