"""Unit tests for retriever helper functions (no DB required)."""

from __future__ import annotations

from uuid import UUID, uuid4

from app.rag.retriever import (
    RetrievedChunk,
    _clean_fts_query,
    _reciprocal_rank_fusion,
    extract_exact_citation,
)


# ---------------------------------------------------------------------------
# extract_exact_citation
# ---------------------------------------------------------------------------
class TestExtractExactCitation:
    def test_bns_section_prefix(self) -> None:
        assert extract_exact_citation("BNS Section 103") == ("BNS", "103")

    def test_bns_section_suffix(self) -> None:
        assert extract_exact_citation("Section 303 of BNS") == ("BNS", "303")

    def test_bns_bare(self) -> None:
        assert extract_exact_citation("BNS 64") == ("BNS", "64")

    def test_bnss_section(self) -> None:
        assert extract_exact_citation("BNSS Section 173") == ("BNSS", "173")

    def test_bsa_section(self) -> None:
        assert extract_exact_citation("BSA Section 63") == ("BSA", "63")

    def test_article_constitution(self) -> None:
        assert extract_exact_citation("Article 21") == ("CONSTITUTION", "21")

    def test_article_of_constitution(self) -> None:
        assert extract_exact_citation(
            "Article 20 of the Constitution"
        ) == ("CONSTITUTION", "20")

    def test_ipc_to_bns_concordance(self) -> None:
        # IPC 302 -> BNS 103
        result = extract_exact_citation("IPC 302")
        assert result is not None
        assert result[0] == "BNS"
        assert result[1] == "103"

    def test_section_ipc_suffix(self) -> None:
        result = extract_exact_citation("Section 302 IPC")
        assert result is not None
        assert result[0] == "BNS"

    def test_no_citation(self) -> None:
        assert extract_exact_citation("punishment for murder") is None

    def test_alpha_suffix_section(self) -> None:
        assert extract_exact_citation("BNS 103A") == ("BNS", "103A")


# ---------------------------------------------------------------------------
# _clean_fts_query
# ---------------------------------------------------------------------------
class TestCleanFtsQuery:
    def test_strips_act_names(self) -> None:
        q = "What is the punishment for murder under Bharatiya Nyaya Sanhita"
        cleaned = _clean_fts_query(q)
        assert "bharatiya" not in cleaned
        assert "nyaya" not in cleaned
        assert "sanhita" not in cleaned
        assert "punishment" in cleaned
        assert "murder" in cleaned

    def test_strips_common_noise(self) -> None:
        q = "Section 103 of BNS under which act"
        cleaned = _clean_fts_query(q)
        assert "section" not in cleaned
        assert "bns" not in cleaned

    def test_preserves_substance(self) -> None:
        q = "bail non-bailable offence"
        cleaned = _clean_fts_query(q)
        assert "bail" in cleaned
        assert "offence" in cleaned

    def test_fallback_on_all_stopwords(self) -> None:
        # If all words are stopwords, we keep the first 3
        q = "under the act"
        cleaned = _clean_fts_query(q)
        assert len(cleaned.split()) > 0


# ---------------------------------------------------------------------------
# _reciprocal_rank_fusion
# ---------------------------------------------------------------------------
def _make_chunk(
    section_no: str, act: str = "BNS", chunk_id: UUID | None = None
) -> RetrievedChunk:
    """Helper to create a mock RetrievedChunk for RRF tests."""
    # We're using RetrievedChunk directly for lightweight testing.
    # _reciprocal_rank_fusion expects KnowledgeChunk objects, so we
    # test the pure RRF logic via a parallel implementation here.
    return RetrievedChunk(
        id=chunk_id or uuid4(),
        act=act,
        section_no=section_no,
        title=f"Section {section_no}",
        body="test body",
        domain="statute",
        audience=["judge", "lawyer"],
        score=0.0,
    )


class TestReciprocalRankFusion:
    def test_single_list(self) -> None:
        """With one ranked list, ordering is preserved."""

        # Build mock KnowledgeChunk-like objects with `.id` attribute
        class FakeKC:
            def __init__(self, chunk_id: UUID, sec: str):
                self.id = chunk_id
                self.section_no = sec

        c1_id, c2_id = uuid4(), uuid4()
        c1 = FakeKC(c1_id, "103")
        c2 = FakeKC(c2_id, "105")
        result = _reciprocal_rank_fusion([[c1, c2]], k=60)  # type: ignore[arg-type]
        assert result[0][0].id == c1_id
        assert result[1][0].id == c2_id

    def test_boost_from_multiple_lists(self) -> None:
        """A chunk appearing in both lists gets a higher RRF score."""

        class FakeKC:
            def __init__(self, chunk_id: UUID, sec: str):
                self.id = chunk_id
                self.section_no = sec

        shared_id = uuid4()
        only_fts_id = uuid4()

        fts_list = [FakeKC(shared_id, "103"), FakeKC(only_fts_id, "105")]
        vec_list = [FakeKC(shared_id, "103")]

        result = _reciprocal_rank_fusion([fts_list, vec_list], k=60)  # type: ignore[arg-type]
        # shared_id should be first because it appeared in both
        assert result[0][0].id == shared_id
        # Its score should be higher than the single-list chunk
        shared_score = result[0][1]
        only_score = next(s for c, s in result if c.id == only_fts_id)
        assert shared_score > only_score

    def test_empty_lists(self) -> None:
        result = _reciprocal_rank_fusion([], k=60)
        assert result == []

