"""Cross-encoder reranker wrapper for BAAI/bge-reranker-v2-m3 and deterministic fake.

Reranks top candidate passages against an input legal query using a cross-encoder model.
Includes a fast, deterministic FakeReranker for CI and unit tests that requires no downloads.
"""

from __future__ import annotations

import logging
import os
import re
from typing import List, Optional, Protocol, Tuple

logger = logging.getLogger(__name__)


class BaseReranker(Protocol):
    """Protocol defining the reranker interface."""

    def rerank(
        self,
        query: str,
        passages: List[str],
        prior_scores: Optional[List[float]] = None,
    ) -> List[Tuple[int, float]]:
        """Rerank passages against a query.

        Returns a list of (passage_index, score) pairs sorted in descending order of score.
        """
        ...


_RERANKER_STOPWORDS = {
    "a",
    "an",
    "the",
    "is",
    "in",
    "for",
    "and",
    "or",
    "to",
    "of",
    "what",
    "which",
    "how",
    "when",
    "where",
    "who",
    "whom",
    "whose",
    "does",
    "do",
    "did",
    "under",
    "by",
    "from",
    "with",
    "as",
    "at",
    "be",
    "been",
    "being",
    "have",
    "has",
    "had",
    "case",
    "cases",
}


class FakeReranker:
    """Deterministic lexical and rank-based reranker for tests and CI without external models.

    Computes query token overlap with passages, boosting exact section mentions and title keywords.
    """

    def rerank(
        self,
        query: str,
        passages: List[str],
        prior_scores: Optional[List[float]] = None,
    ) -> List[Tuple[int, float]]:
        if not passages:
            return []

        q_clean = query.lower()
        q_tokens = [w for w in re.findall(r"[a-z0-9]+", q_clean) if w not in _RERANKER_STOPWORDS]

        # Extract cited section/article number from query if present
        m_sec = re.search(r"\b(?:section|sec\.?|s\.|article|art\.?)\s*(\d+[a-z]?)\b", q_clean)
        cited_sec = m_sec.group(1).lower() if m_sec else None

        max_prior = max(prior_scores) if prior_scores else 1.0
        scored: List[Tuple[int, float]] = []

        for idx, text in enumerate(passages):
            t_clean = text.lower()
            parts = t_clean.split(":", 1)
            header = parts[0]
            rest = parts[1] if len(parts) > 1 else ""
            title_part = rest.split(".", 1)[0] if "." in rest else rest[:80]

            match_score = 0.0
            for tok in q_tokens:
                if tok in header:
                    match_score += 4.0
                if tok in title_part:
                    match_score += 3.0
                elif tok in rest:
                    match_score += 0.5

            if cited_sec:
                if f"section {cited_sec}" in header or f"article {cited_sec}" in header:
                    match_score += 50.0

            if prior_scores and max_prior > 0:
                prior = prior_scores[idx] / max_prior
            else:
                prior = 0.1 / (idx + 1)
            final_score = (5.0 * prior) + match_score
            scored.append((idx, final_score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored


class BgeRerankerV2M3:
    """Production cross-encoder wrapper for BAAI/bge-reranker-v2-m3."""

    def __init__(
        self,
        model_name: str = "BAAI/bge-reranker-v2-m3",
        device: str = "cpu",
        batch_size: int = 16,
    ) -> None:
        self.model_name = model_name
        self.device = device
        self.batch_size = batch_size
        self._model = None

    def _load_model(self) -> None:
        if self._model is not None:
            return
        from sentence_transformers import CrossEncoder

        logger.info("Loading cross-encoder %s on %s...", self.model_name, self.device)
        self._model = CrossEncoder(self.model_name, device=self.device)

    def rerank(
        self,
        query: str,
        passages: List[str],
        prior_scores: Optional[List[float]] = None,
    ) -> List[Tuple[int, float]]:
        if not passages:
            return []
        self._load_model()
        assert self._model is not None
        pairs = [(query, p) for p in passages]
        scores = self._model.predict(pairs, batch_size=self.batch_size)
        scored = list(enumerate(scores.tolist() if hasattr(scores, "tolist") else scores))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored


def get_reranker() -> BaseReranker:
    """Return configured reranker: FakeReranker in test mode, real model in production."""
    use_fake = (
        os.getenv("VERDICT_FAKE_RERANKER", "1") == "1"
        or os.getenv("TESTING", "0") == "1"
        or os.getenv("PYTEST_CURRENT_TEST") is not None
    )
    if use_fake:
        return FakeReranker()
    try:
        return BgeRerankerV2M3()
    except Exception as exc:
        logger.warning("Could not load BgeRerankerV2M3 (%s), falling back to FakeReranker", exc)
        return FakeReranker()
