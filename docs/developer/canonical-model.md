# Canonical model

This page documents every dataclass and contract that headcleaner uses to represent documents, chunks, graphs, claims, and sync state. It is the developer reference for the data shapes that flow through the pipeline.

## Source document

### `CanonicalDoc`

The per-source container. Every adapter produces one of these.

```python
@dataclass(frozen=True)
class CanonicalDoc:
    title: str
    body_md: str
    elements: tuple[Element, ...]
    frontmatter: dict[str, Any]
    source_path: Path
    source_relpath: Path
    source_uri: str
    source_sha256: str
    source_size_bytes: int
    source_format: str  # e.g. ".docx"
    engine: str         # e.g. "officecli"
    attachments: tuple[Attachment, ...]
```

The trust defaults set `verified: human:pending` and `stale_after: <today + 180d>` for every auto-converted doc. The implementation is in `src/headcleaner/normalize.py`.

### `Element`

The typed representation of a chunk of document content.

```python
@dataclass(frozen=True)
class Element:
    id: str                              # deterministic digest of source SHA + kind + ordinal + content
    kind: str                            # heading | paragraph | list | table | image | code | quote | attachment_ref | page_break
    ordinal: int                         # 0-based position within the source
    text: str
    source_location: SourceLocation | None  # {page, start, end}
    attributes: dict[str, Any]           # JSON-safe values only
```

The ID is a digest of source SHA, kind, ordinal, and normalized content. It is not a random UUID. The kind is one of nine values; the `__post_init__` validator enforces the enum. The implementation is in `src/headcleaner/model.py`.

### `SourceLocation`

```python
@dataclass(frozen=True)
class SourceLocation:
    page: int | None
    start: int | None
    end: int | None
```

All three fields are nullable. Page is the source page number; start and end are character offsets within the page when the source format supports them.

## Chunk derivative

### `Chunk`

The cited, deterministic chunk emitted for search and graph.

```python
@dataclass(frozen=True)
class Chunk:
    id: str
    concept_id: str                      # bundle-relative Markdown path
    source_sha256: str
    element_ids: tuple[str, ...]         # non-empty
    ordinal: int                         # 0-based within source
    heading_path: tuple[str, ...]
    text: str
    citation: dict[str, Any]             # source_uri, source_sha256, page, start, end
    token_estimate: int
    chunking_version: str = "1"
    oversize: bool = False
```

The ID is a digest of source SHA, ordered element IDs, ordinal, and `chunking_version`. The citation is required and must include all five keys. Table and code elements are indivisible: a single element that exceeds the size boundary is emitted whole with `oversize: true`. The implementation is in `src/headcleaner/chunking.py`.

## Graph derivative

### `GraphNode`

```python
@dataclass(frozen=True)
class GraphNode:
    id: str                              # stable identifier
    kind: str                            # concept | chunk | entity | topic
    label: str
    source_refs: tuple[str, ...]         # source SHA-256 values
    attributes: dict[str, Any]           # JSON-safe
```

The `__post_init__` validator rejects any kind outside the four allowed values. Node IDs are stable across rebuilds.

### `GraphEdge`

```python
@dataclass(frozen=True)
class GraphEdge:
    id: str
    kind: str                            # contains | cites | mentions | related_to | duplicate_candidate | conflicts_candidate
    from_id: str
    to_id: str
    evidence_chunk_ids: tuple[str, ...]  # required for every kind except "contains"
    method: str
    status: str                          # explicit | unverified
```

The `__post_init__` validator rejects edge kinds outside the six allowed values and statuses outside the two allowed values. Generated edges have `status: unverified`; explicit cross-references have `status: explicit`. The implementation is in `src/headcleaner/graph.py`.

## Claim derivative

### `ClaimCandidate`

```python
@dataclass(frozen=True)
class ClaimCandidate:
    id: str
    kind: str                            # date | amount | owner | status_label
    normalized_value: str
    source_chunk_id: str
    citation: dict[str, Any]
    extraction_rule: str
    status: str                          # extracted | unverified | suppressed
    suppression_reason: str | None = None
```

The kind enum is enforced at construction. Status defaults to `unverified`; suppressed claims keep `status: suppressed` with a `suppression_reason` so the audit trail is complete.

### `Finding`

```python
@dataclass(frozen=True)
class Finding:
    id: str
    type: str                            # stale | potential_conflict
    severity: str                        # info | warning | error
    claim_ids: tuple[str, ...]
    evidence: tuple[dict[str, Any], ...]
    rule_id: str                         # e.g. "claims/date/unequal/bundle"
```

Findings carry the rule ID so they can be filtered by policy. Conflict findings are labeled `potential_conflict`, never `false` or `contradiction` — headcleaner does not assert factual claims.

## Sync state

### `SyncRecord`

```python
@dataclass(frozen=True)
class SyncRecord:
    source_sha256: str
    current_relpath: str
    prior_relpaths: tuple[str, ...]
    generated_paths: tuple[str, ...]
    generation: int
    output_hashes: dict[str, str]        # relpath -> sha256
    last_seen_at: str                    # ISO 8601
```

Records are keyed by `(current_relpath, source_sha256)` so identical-content files at different paths retain distinct lineage. The state lives at `<bundle>/.headcleaner/sync.json` and is written atomically through temp+rename.

## Embeddings

### `EmbeddingProvider` protocol

```python
class EmbeddingProvider(Protocol):
    name: str
    model_id: str
    dimension: int

    def embed(self, texts: list[str], *, allow_network: bool = False) -> list[list[float]]: ...
```

Two implementations ship with headcleaner: `LocalSentenceTransformerProvider` (in-process, no network) and `HttpEmbeddingProvider` (raises `NetworkPermissionError` unless `allow_network` is true). Plugins implement this protocol through the `headcleaner_embedding_provider` entry-point group.

## Search

### `SearchHit`

```python
@dataclass(frozen=True)
class SearchHit:
    rank: float                          # bm25 score
    chunk_id: str
    concept_path: str                    # bundle-relative
    ordinal: int
    excerpt: str                         # bracketed FTS5 snippet
    citation: dict[str, Any]
    trust_state: str
    index_schema_version: str = INDEX_SCHEMA_VERSION
```

The deterministic tie-break is `(bm25, concept_path, ordinal)`. Two equivalent queries return identical hits in identical order.

## Manifest and run record

The `RunRecord` is the per-run summary. The manifest is the on-disk JSON form. The fields are documented in the [result reference](../reference/result-reference.md).

## What to read next

The [architecture developer guide](architecture.md) explains how the modules fit together. The [chunking and indexing developer guide](chunking-and-indexing.md) covers the chunk and index contracts in detail. The [graph development developer guide](graph-development.md) covers the graph contracts.