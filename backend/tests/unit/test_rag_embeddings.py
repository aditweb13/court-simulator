"""Unit tests for the embedding model wrapper (FakeEmbedder)."""

import math

from app.rag.embeddings import EMBEDDING_DIM, FakeEmbedder, get_embedder


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class TestFakeEmbedder:
    def test_dimension(self) -> None:
        emb = FakeEmbedder()
        vec = emb.embed_query("punishment for murder")
        assert len(vec) == EMBEDDING_DIM

    def test_determinism(self) -> None:
        emb = FakeEmbedder()
        v1 = emb.embed_query("bail in non-bailable offence")
        v2 = emb.embed_query("bail in non-bailable offence")
        assert v1 == v2

    def test_normalization(self) -> None:
        emb = FakeEmbedder()
        vec = emb.embed_query("theft under BNS section 303")
        norm = math.sqrt(sum(v * v for v in vec))
        assert abs(norm - 1.0) < 1e-6

    def test_similar_texts_higher_similarity(self) -> None:
        emb = FakeEmbedder()
        v_murder = emb.embed_query("punishment murder death")
        v_murder2 = emb.embed_query("murder death punishment penalty")
        v_theft = emb.embed_query("theft property stolen goods")
        sim_same = _cosine_similarity(v_murder, v_murder2)
        sim_diff = _cosine_similarity(v_murder, v_theft)
        assert sim_same > sim_diff

    def test_embed_documents_batch(self) -> None:
        emb = FakeEmbedder()
        texts = ["first text", "second text", "third text"]
        results = emb.embed_documents(texts)
        assert len(results) == 3
        for vec in results:
            assert len(vec) == EMBEDDING_DIM

    def test_embed_documents_empty(self) -> None:
        emb = FakeEmbedder()
        results = emb.embed_documents([])
        assert results == []

    def test_empty_text(self) -> None:
        emb = FakeEmbedder()
        vec = emb.embed_query("")
        assert len(vec) == EMBEDDING_DIM
        assert all(v == 0.0 for v in vec)

    def test_custom_dimension(self) -> None:
        emb = FakeEmbedder(dimension=128)
        vec = emb.embed_query("test")
        assert len(vec) == 128


class TestGetEmbedder:
    def test_returns_fake_in_test_mode(self) -> None:
        embedder = get_embedder()
        assert isinstance(embedder, FakeEmbedder)
