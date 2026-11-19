"""Unit tests for the reranker wrapper (FakeReranker)."""

from app.rag.reranker import FakeReranker, get_reranker


class TestFakeReranker:
    def test_rerank_ordering(self) -> None:
        rr = FakeReranker()
        query = "punishment for murder"
        passages = [
            "BNS Section 303: Theft — whoever dishonestly takes property...",
            "BNS Section 103: Punishment for murder — whoever commits murder shall be punished...",
            "BSA Section 2: Definition of evidence — evidence means and includes...",
        ]
        result = rr.rerank(query, passages)
        assert len(result) == 3
        # The passage about murder should rank first
        top_idx = result[0][0]
        assert top_idx == 1  # passage index 1 is the murder passage

    def test_rerank_scores_descending(self) -> None:
        rr = FakeReranker()
        query = "bail in non-bailable offence"
        passages = [
            "BNSS Section 480: When bail may be taken in case of non-bailable offence...",
            "BNS Section 115: Voluntarily causing hurt...",
            "BNSS Section 482: Anticipatory bail direction...",
        ]
        result = rr.rerank(query, passages)
        scores = [s for _, s in result]
        for i in range(len(scores) - 1):
            assert scores[i] >= scores[i + 1]

    def test_rerank_empty(self) -> None:
        rr = FakeReranker()
        result = rr.rerank("test query", [])
        assert result == []

    def test_rerank_single_passage(self) -> None:
        rr = FakeReranker()
        result = rr.rerank("test", ["only passage here"])
        assert len(result) == 1
        assert result[0][0] == 0

    def test_rerank_returns_all_indices(self) -> None:
        rr = FakeReranker()
        passages = ["a", "b", "c", "d"]
        result = rr.rerank("test", passages)
        indices = sorted(idx for idx, _ in result)
        assert indices == [0, 1, 2, 3]


class TestGetReranker:
    def test_returns_fake_in_test_mode(self) -> None:
        reranker = get_reranker()
        assert isinstance(reranker, FakeReranker)

