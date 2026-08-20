"""Explicit embedding providers and versioned local vector cache."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol
from urllib import request


class EmbeddingModelUnavailable(RuntimeError):
    pass


class NetworkPermissionError(PermissionError):
    pass


class VectorCollectionIncompatible(RuntimeError):
    pass


class EmbeddingProvider(Protocol):
    name: str
    model_id: str
    dimension: int

    def embed(self, texts: list[str], *, allow_network: bool = False) -> list[list[float]]: ...


@dataclass
class LocalSentenceTransformerProvider:
    model_path: Path
    model_id: str
    dimension: int = 0
    name: str = "local_sentence_transformer"
    version: str = "1"

    def embed(self, texts: list[str], *, allow_network: bool = False) -> list[list[float]]:
        if not self.model_path.is_dir():
            raise EmbeddingModelUnavailable(f"EMBEDDING_MODEL_UNAVAILABLE: {self.model_path}")
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise EmbeddingModelUnavailable(
                "EMBEDDING_MODEL_UNAVAILABLE: sentence-transformers"
            ) from exc
        model = SentenceTransformer(str(self.model_path), local_files_only=True)
        vectors = model.encode(texts).tolist()
        if vectors:
            self.dimension = len(vectors[0])
        return [[float(value) for value in vector] for vector in vectors]


@dataclass
class HttpEmbeddingProvider:
    endpoint: str
    model_id: str
    dimension: int = 0
    name: str = "openai_compatible_http"
    version: str = "1"
    timeout: float = 30.0

    def embed(self, texts: list[str], *, allow_network: bool = False) -> list[list[float]]:
        if not allow_network:
            raise NetworkPermissionError("HTTP embeddings require --allow-network")
        payload = json.dumps({"model": self.model_id, "input": texts}).encode("utf-8")
        req = request.Request(
            self.endpoint, data=payload, headers={"Content-Type": "application/json"}
        )
        with request.urlopen(req, timeout=self.timeout) as response:  # noqa: S310 - explicit opt-in boundary
            data = json.loads(response.read().decode("utf-8"))
        vectors = [[float(value) for value in item["embedding"]] for item in data["data"]]
        if vectors:
            self.dimension = len(vectors[0])
        return vectors


class VectorCache:
    """Small local cache keyed by text digest plus provider/model/dimension/version."""

    def __init__(self, bundle_root: Path) -> None:
        self.path = bundle_root / ".headcleaner" / "vectors.json"

    @staticmethod
    def _key(chunk_text: str, provider: str, model_id: str, dimension: int, version: str) -> str:
        return hashlib.sha256(
            "\0".join(
                (
                    hashlib.sha256(chunk_text.encode()).hexdigest(),
                    provider,
                    model_id,
                    str(dimension),
                    version,
                )
            ).encode()
        ).hexdigest()

    def _read(self) -> dict[str, Any]:
        if not self.path.exists():
            return {}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

    def _write(self, values: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(values, sort_keys=True), encoding="utf-8")
        temporary.replace(self.path)

    def get(
        self, chunk_text: str, *, provider: str, model_id: str, dimension: int, version: str
    ) -> list[float] | None:
        value = self._read().get(self._key(chunk_text, provider, model_id, dimension, version))
        if isinstance(value, dict):
            vector = value.get("vector")
            return vector if isinstance(vector, list) else None
        return value if isinstance(value, list) else None

    def put(
        self,
        chunk_text: str,
        *,
        chunk_id: str,
        provider: str,
        model_id: str,
        dimension: int,
        version: str,
        vector: list[float],
    ) -> None:
        if len(vector) != dimension:
            raise ValueError("embedding dimension mismatch")
        if not chunk_id:
            raise ValueError("chunk_id is required")
        values = self._read()
        values[self._key(chunk_text, provider, model_id, dimension, version)] = {
            "chunk_id": chunk_id,
            "vector": vector,
        }
        self._write(values)

    def prune_orphans(self, current_chunk_ids: set[str]) -> int:
        """Delete only versioned records whose source chunk is absent from this rebuild."""
        values = self._read()
        retained = {
            key: value
            for key, value in values.items()
            if not isinstance(value, dict) or value.get("chunk_id") in current_chunk_ids
        }
        removed = len(values) - len(retained)
        if removed:
            self._write(retained)
        return removed


@dataclass
class QdrantVectorStore:
    """Explicit Qdrant adapter; never connects without a configured endpoint."""

    endpoint: str | None
    collection: str
    client_factory: Callable[[str], Any] | None = None

    def _client(self) -> Any:
        if not self.endpoint:
            raise NetworkPermissionError("Qdrant requires a configured endpoint")
        if self.client_factory is not None:
            return self.client_factory(self.endpoint)
        from qdrant_client import QdrantClient

        return QdrantClient(url=self.endpoint)

    def upsert(
        self,
        *,
        chunk_id: str,
        vector: list[float],
        metadata: dict[str, Any],
        model_id: str,
    ) -> None:
        """Upsert stable IDs and safe metadata, never embedding chunk text as payload."""
        payload = {
            key: value for key, value in metadata.items() if key not in {"text", "chunk_text"}
        }
        payload.update({"chunk_id": chunk_id, "model_id": model_id, "dimension": len(vector)})
        self._client().upsert(
            collection_name=self.collection,
            points=[{"id": chunk_id, "vector": vector, "payload": payload}],
        )

    def ensure_compatible(self, *, dimension: int, model_id: str, recreate: bool = False) -> str:
        """Create or explicitly recreate an incompatible remote collection."""
        client = self._client()
        if not hasattr(client, "collection_exists"):
            return "unchecked"
        if not client.collection_exists(collection_name=self.collection):
            client.create_collection(
                collection_name=self.collection,
                vectors_config={"size": dimension, "distance": "Cosine"},
            )
            return "created"
        points, _next_offset = client.scroll(
            collection_name=self.collection,
            with_payload=True,
            with_vectors=False,
            limit=1,
        )
        payload = (
            (points[0].get("payload", {}) if isinstance(points[0], dict) else points[0].payload)
            if points
            else {}
        )
        actual_dimension = payload.get("dimension")
        actual_model = payload.get("model_id")
        if (actual_dimension not in {None, dimension}) or (actual_model not in {None, model_id}):
            if not recreate:
                raise VectorCollectionIncompatible(
                    "QDRANT_COLLECTION_INCOMPATIBLE: pass --recreate-qdrant-collection "
                    "to replace vectors for a changed model or dimension"
                )
            client.recreate_collection(
                collection_name=self.collection,
                vectors_config={"size": dimension, "distance": "Cosine"},
            )
            return "recreated"
        return "compatible"

    def prune_orphans(self, current_chunk_ids: set[str]) -> int:
        """Remove remote points that no longer correspond to rebuilt cited chunks."""
        client = self._client()
        points, next_offset = client.scroll(
            collection_name=self.collection,
            with_payload=False,
            with_vectors=False,
            limit=256,
        )
        orphaned: list[str] = []
        while True:
            orphaned.extend(
                str(point["id"] if isinstance(point, dict) else point.id)
                for point in points
                if str(point["id"] if isinstance(point, dict) else point.id)
                not in current_chunk_ids
            )
            if next_offset is None:
                break
            points, next_offset = client.scroll(
                collection_name=self.collection,
                with_payload=False,
                with_vectors=False,
                limit=256,
                offset=next_offset,
            )
        if orphaned:
            client.delete(collection_name=self.collection, points_selector=orphaned)
        return len(orphaned)
