from __future__ import annotations

from pathlib import Path

import pytest


def test_http_provider_refuses_before_network_without_permission(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from headcleaner.embeddings import HttpEmbeddingProvider, NetworkPermissionError

    provider = HttpEmbeddingProvider("https://example.invalid/v1", model_id="test")
    monkeypatch.setattr(
        "urllib.request.urlopen", lambda *_a, **_kw: pytest.fail("network attempted")
    )
    with pytest.raises(NetworkPermissionError):
        provider.embed(["private text"], allow_network=False)


def test_vector_cache_is_versioned_and_invalidates_dimension(tmp_path: Path) -> None:
    from headcleaner.embeddings import VectorCache

    cache = VectorCache(tmp_path)
    cache.put(
        "chunk",
        chunk_id="chunk-a",
        provider="fake",
        model_id="m1",
        dimension=2,
        version="1",
        vector=[1.0, 2.0],
    )
    assert cache.get("chunk", provider="fake", model_id="m1", dimension=2, version="1") == [
        1.0,
        2.0,
    ]
    assert cache.get("chunk", provider="fake", model_id="m1", dimension=3, version="1") is None
    assert cache.prune_orphans({"chunk-b"}) == 1
    assert cache.get("chunk", provider="fake", model_id="m1", dimension=2, version="1") is None


def test_local_provider_reports_missing_model(tmp_path: Path) -> None:
    from headcleaner.embeddings import EmbeddingModelUnavailable, LocalSentenceTransformerProvider

    with pytest.raises(EmbeddingModelUnavailable, match="EMBEDDING_MODEL_UNAVAILABLE"):
        LocalSentenceTransformerProvider(tmp_path / "missing", model_id="local").embed(["text"])


def test_qdrant_adapter_requires_explicit_endpoint_and_keeps_text_out_of_metadata() -> None:
    from headcleaner.embeddings import NetworkPermissionError, QdrantVectorStore

    with pytest.raises(NetworkPermissionError, match="configured endpoint"):
        QdrantVectorStore(endpoint=None, collection="bundle").upsert(
            chunk_id="chunk-1",
            vector=[0.1, 0.2],
            metadata={"source_sha256": "a" * 64, "text": "private chunk text"},
            model_id="fake",
        )

    calls: list[dict] = []

    class FakeClient:
        def upsert(self, *, collection_name, points):
            calls.append({"collection": collection_name, "points": points})

    store = QdrantVectorStore(
        endpoint="http://localhost:6333", collection="bundle", client_factory=lambda _: FakeClient()
    )
    store.upsert(
        chunk_id="chunk-1",
        vector=[0.1, 0.2],
        metadata={"source_sha256": "a" * 64, "text": "private chunk text"},
        model_id="fake",
    )
    payload = calls[0]["points"][0]["payload"]
    assert payload["chunk_id"] == "chunk-1"
    assert "text" not in payload


def test_qdrant_adapter_deletes_only_orphaned_stable_chunk_ids() -> None:
    from headcleaner.embeddings import QdrantVectorStore

    calls: list[dict] = []

    class FakeClient:
        def scroll(self, *, collection_name, with_payload, with_vectors, limit):
            calls.append({"scroll": collection_name, "limit": limit})
            return ([{"id": "current"}, {"id": "orphan"}], None)

        def delete(self, *, collection_name, points_selector):
            calls.append({"delete": collection_name, "points": points_selector})

    store = QdrantVectorStore(
        endpoint="http://localhost:6333", collection="bundle", client_factory=lambda _: FakeClient()
    )

    assert store.prune_orphans({"current"}) == 1
    assert calls[-1] == {"delete": "bundle", "points": ["orphan"]}


def test_qdrant_collection_model_or_dimension_change_requires_explicit_recreate() -> None:
    from headcleaner.embeddings import QdrantVectorStore, VectorCollectionIncompatible

    calls: list[str] = []

    class FakeClient:
        def collection_exists(self, *, collection_name):
            return True

        def scroll(self, **_kwargs):
            return ([{"id": "old", "payload": {"model_id": "old", "dimension": 2}}], None)

        def recreate_collection(self, **_kwargs):
            calls.append("recreate")

    store = QdrantVectorStore(
        endpoint="http://localhost:6333", collection="bundle", client_factory=lambda _: FakeClient()
    )

    with pytest.raises(VectorCollectionIncompatible, match="recreate-qdrant-collection"):
        store.ensure_compatible(dimension=3, model_id="new")
    assert store.ensure_compatible(dimension=3, model_id="new", recreate=True) == "recreated"
    assert calls == ["recreate"]


def test_embedding_plugin_loader_accepts_protocol_and_rejects_invalid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from headcleaner import plugins

    class Provider:
        name = "fixture"
        model_id = "fixture-model"
        dimension = 2
        version = "fixture-v1"

        def embed(self, texts: list[str], *, allow_network: bool = False) -> list[list[float]]:
            return [[0.0, 0.0] for _ in texts]

    class EntryPoint:
        def __init__(self, name: str, obj: object) -> None:
            self.name = name
            self._obj = obj

        def load(self) -> object:
            return self._obj

    monkeypatch.setattr(
        plugins,
        "_iter_embedding_entry_points",
        lambda: [
            ("fixture", EntryPoint("fixture", Provider)),
            ("broken", EntryPoint("broken", object())),
        ],
    )

    providers, results = plugins.load_embedding_providers()

    assert providers["fixture"].model_id == "fixture-model"
    assert ("loaded", "fixture", "fixture-model") in results
    assert any(status == "error" and name == "broken" for status, name, _ in results)


def test_index_embed_selects_an_explicit_embedding_plugin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from click.testing import CliRunner

    from headcleaner.cli import cli

    calls: list[tuple[list[str], bool]] = []

    class Provider:
        name = "fixture"
        model_id = "fixture-model"
        dimension = 2
        version = "fixture-v1"

        def embed(self, texts: list[str], *, allow_network: bool = False) -> list[list[float]]:
            calls.append((texts, allow_network))
            return [[0.0, 0.0] for _ in texts]

    bundle = tmp_path / "bundle"
    bundle.mkdir()
    monkeypatch.setattr(
        "headcleaner.plugins.load_embedding_providers", lambda: ({"fixture": Provider()}, [])
    )
    monkeypatch.setattr("headcleaner.chunking.read_chunks", lambda _bundle: [])

    result = CliRunner().invoke(
        cli,
        ["index", "embed", str(bundle), "--provider", "fixture", "--model", "ignored"],
    )

    assert result.exit_code == 0, result.output
    assert calls == [([], False)]
    assert result.output == "cached 0 vectors; pruned 0 local and 0 Qdrant orphans\n"


def test_index_embed_refuses_qdrant_before_provider_or_network_work(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from click.testing import CliRunner

    from headcleaner.cli import cli

    calls: list[bool] = []

    class Provider:
        name = "fixture"
        model_id = "fixture-model"
        dimension = 2
        version = "fixture-v1"

        def embed(self, texts: list[str], *, allow_network: bool = False) -> list[list[float]]:
            calls.append(allow_network)
            return []

    bundle = tmp_path / "bundle"
    bundle.mkdir()
    monkeypatch.setattr(
        "headcleaner.plugins.load_embedding_providers", lambda: ({"fixture": Provider()}, [])
    )
    result = CliRunner().invoke(
        cli,
        [
            "index",
            "embed",
            str(bundle),
            "--provider",
            "fixture",
            "--model",
            "ignored",
            "--qdrant-endpoint",
            "http://localhost:6333",
        ],
    )

    assert result.exit_code != 0
    assert "Qdrant requires --allow-network" in result.output
    assert not calls
