# Embeddings and vectors

This page documents headcleaner's embedding layer: the provider protocol, the local vector cache, and the Qdrant adapter. It is the developer reference for the contracts that make semantic search possible without making it implicit.

## The provider protocol

The `EmbeddingProvider` protocol lives in `src/headcleaner/embeddings.py`. It is the contract every embedding implementation must satisfy.

```python
class EmbeddingProvider(Protocol):
    name: str
    model_id: str
    dimension: int

    def embed(self, texts: list[str], *, allow_network: bool = False) -> list[list[float]]: ...
```

The three properties describe the provider's identity. The `embed` method takes a list of texts and returns a list of equal-length float vectors. The `allow_network` flag is explicit; providers that do not make network calls ignore it, providers that do must refuse to make the call without it.

## Built-in providers

Headcleaner ships two built-in providers.

### `LocalSentenceTransformerProvider`

The local provider uses the Sentence Transformers library to compute embeddings in-process. No network call is made. The provider requires a local model file; the path is passed at construction time.

```python
provider = LocalSentenceTransformerProvider(model_path="/path/to/model")
vectors = provider.embed(["text one", "text two"], allow_network=False)
```

The provider returns a list of vectors, one per input text, each of length `dimension`. The model is loaded lazily on first use.

### `HttpEmbeddingProvider`

The HTTP provider sends a request to an OpenAI-compatible embedding endpoint. The provider refuses to make the request unless `allow_network=True`:

```python
provider = HttpEmbeddingProvider(
    endpoint="https://api.example.com/v1/embeddings",
    model_id="my-model",
    api_key="...",  # or read from configuration
)
vectors = provider.embed(["text one", "text two"], allow_network=True)
```

Without `allow_network=True`, the provider raises `NetworkPermissionError`. This is the deny-before-work behavior the contract requires.

## The local vector cache

The vector cache lives at `<bundle>/.headcleaner/vectors.json`. It maps a cache key to a vector plus metadata.

### Cache key

The cache key is a SHA-256 digest of `(chunk_text, provider_name, model_id, dimension, provider_version)`. Changing any of those inputs invalidates the cache. The provider version is the implementation version of the provider class; bumping it forces re-computation.

### Cache value

Each cache entry stores:

- `chunk_id`: the source chunk's ID, so orphan vectors can be identified.
- `vector`: the float list.
- `provider`: the provider name.
- `model_id`: the model ID.
- `dimension`: the vector dimension.
- `provider_version`: the implementation version.
- `cached_at`: the ISO 8601 timestamp of when the vector was cached.

### Lifecycle

`VectorCache.get` returns the cached vector if present, or `None` if not. `VectorCache.put` writes a vector. `VectorCache.prune_orphans(current_chunk_ids)` removes cache entries whose `chunk_id` is not in the provided set. The prune is called after every embed run so the cache stays in sync with the chunk derivative.

## The Qdrant adapter

The Qdrant adapter lives in `src/headcleaner/embeddings.py` and uses the `qdrant-client` library. The adapter is opt-in: it is only instantiated when `--qdrant-endpoint` is passed.

### Connection

The adapter stores an endpoint URL and a collection name. The connection is established lazily on first use. The adapter does not connect at construction time; this is intentional so the import does not require Qdrant to be reachable.

### Upsert

`QdrantVectorStore.upsert` writes a vector to the collection. The vector ID is the chunk ID (stable across rebuilds). The payload contains the chunk ID, the model ID, the dimension, and any citation-safe metadata the caller provides. Chunk text is never included in the payload.

### Compatibility inspection

`QdrantVectorStore.ensure_compatible` checks the existing collection's dimension and model ID against the current provider. If they match, the collection is reused. If they do not match, the adapter raises `VectorCollectionIncompatible` unless `recreate=True` is passed, in which case the adapter calls `recreate_collection`.

The CLI exposes this through `--recreate-qdrant-collection`. The flag is the explicit opt-in to drop the existing remote collection; without it, a dimension or model mismatch is an error.

### Orphan pruning

`QdrantVectorStore.prune_orphans(current_chunk_ids)` removes remote points whose IDs are not in the provided set. The implementation pages through the collection without loading payloads or vectors, identifies the orphans, and deletes them in one batch. The pruning is bounded: a single scan, no per-point payload fetch.

### Permission gating

The Qdrant adapter validates the explicit endpoint plus `--allow-network` before any chunk is read or any embedding is computed. The CLI flag pair is checked in the permission layer, not in the adapter; the adapter refuses to construct a client without an endpoint, and the CLI refuses to invoke the adapter without `--allow-network`.

## What to read next

The [canonical model developer guide](canonical-model.md) documents the data shapes. The [chunking and indexing developer guide](chunking-and-indexing.md) covers the search index that embeddings can be combined with. The [safety overview](../safety/safety-overview.md) documents the permission invariants.