"""Embedding model wrapper for BAAI/bge-m3 with batching and deterministic fake.

Generates 1024-dimensional dense embeddings for statutory legal text and search queries.
Provides a deterministic FakeEmbedder for CI and unit tests that runs with zero downloads.
"""

from __future__ import annotations

import hashlib
import logging
import math
import os
from typing import List, Protocol

logger = logging.getLogger(__name__)

EMBEDDING_DIM = 1024


class BaseEmbedder(Protocol):
    """Protocol defining the embedding interface."""

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of text documents with batching."""
        ...

    def embed_query(self, query: str) -> List[float]:
        """Embed a single search query."""
        ...


class FakeEmbedder:
    """Deterministic, seed-based fake embedder for testing with zero model download.

    Generates normalized 1024-dimensional vectors using SHA-256 hashes of input text tokens.
    Texts with similar tokens produce higher cosine similarities than unrelated texts.
    """

    def __init__(self, dimension: int = EMBEDDING_DIM) -> None:
        self.dimension = dimension

    def _hash_to_vector(self, text: str) -> List[float]:
        words = text.lower().split()
        vec = [0.0] * self.dimension
        if not words:
            return vec

        for word in words:
            # Deterministic bucket based on MD5/SHA256
            h = int(hashlib.sha256(word.encode("utf-8")).hexdigest(), 16)
            idx = h % self.dimension
            sign = 1.0 if (h // self.dimension) % 2 == 0 else -1.0
            vec[idx] += sign

        # L2 normalize
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0.0:
            vec = [v / norm for v in vec]
        return vec

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self._hash_to_vector(t) for t in texts]

    def embed_query(self, query: str) -> List[float]:
        return self._hash_to_vector(query)


class BgeM3Embedder:
    """Production wrapper for BAAI/bge-m3 dense embedding model."""

    def __init__(
        self,
        model_name: str = "BAAI/bge-m3",
        batch_size: int = 32,
        device: str = "cpu",
    ) -> None:
        self.model_name = model_name
        self.batch_size = batch_size
        self.device = device
        self._model = None

    def _load_model(self) -> None:
        if self._model is not None:
            return
        from sentence_transformers import SentenceTransformer

        logger.info("Loading embedding model %s on %s...", self.model_name, self.device)
        self._model = SentenceTransformer(self.model_name, device=self.device)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        self._load_model()
        assert self._model is not None
        embeddings = self._model.encode(
            texts,
            batch_size=self.batch_size,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return embeddings.tolist()  # type: ignore[no-any-return]

    def embed_query(self, query: str) -> List[float]:
        results = self.embed_documents([query])
        return results[0] if results else [0.0] * EMBEDDING_DIM


def get_embedder() -> BaseEmbedder:
    """Return configured embedder: FakeEmbedder in test mode, real model in production."""
    use_fake = (
        os.getenv("VERDICT_FAKE_EMBEDDINGS", "1") == "1"
        or os.getenv("TESTING", "0") == "1"
        or os.getenv("PYTEST_CURRENT_TEST") is not None
    )
    if use_fake:
        return FakeEmbedder()
    try:
        return BgeM3Embedder()
    except Exception as exc:
        logger.warning(
            "Could not load BgeM3Embedder (%s), falling back to FakeEmbedder", exc
        )
        return FakeEmbedder()

