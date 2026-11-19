"""Unit tests for citation extraction and verification."""

from __future__ import annotations

from uuid import uuid4

from app.rag.citation import extract_cited_provisions, verify_citations
from app.rag.retriever import RetrievedChunk


def _make_chunk(act: str, section_no: str, ipc_eq: str | None = None) -> RetrievedChunk:
    return RetrievedChunk(
        id=uuid4(),
        act=act,
        section_no=section_no,
        title=f"Section {section_no}",
        body="body",
        domain="statute",
        audience=["judge", "lawyer"],
        score=0.9,
        ipc_equivalent=ipc_eq,
    )


# ---------------------------------------------------------------------------
# extract_cited_provisions
# ---------------------------------------------------------------------------
class TestExtractCitedProvisions:
    def test_bns_section(self) -> None:
        text = "As per Section 103 BNS, the accused is liable."
        cited = extract_cited_provisions(text)
        assert ("BNS", "103") in cited

    def test_multiple_citations(self) -> None:
        text = "Section 103 BNS and Section 173 BNSS apply here."
        cited = extract_cited_provisions(text)
        assert ("BNS", "103") in cited
        assert ("BNSS", "173") in cited

    def test_article_citation(self) -> None:
        text = "Article 21 of the Constitution guarantees life."
        cited = extract_cited_provisions(text)
        assert ("CONSTITUTION", "21") in cited

    def test_ipc_resolution(self) -> None:
        text = "The charge under IPC 302 is equivalent to BNS."
        cited = extract_cited_provisions(text)
        # IPC 302 -> BNS 103
        assert any(act == "BNS" for act, _ in cited)

    def test_no_citations(self) -> None:
        text = "The accused committed the crime on Tuesday."
        cited = extract_cited_provisions(text)
        assert cited == []

    def test_no_duplicates(self) -> None:
        text = "Section 103 BNS applies. Under BNS Section 103, the penalty is..."
        cited = extract_cited_provisions(text)
        bns_103 = [p for p in cited if p == ("BNS", "103")]
        assert len(bns_103) == 1


# ---------------------------------------------------------------------------
# verify_citations
# ---------------------------------------------------------------------------
class TestVerifyCitations:
    def test_valid_citation(self) -> None:
        chunks = [_make_chunk("BNS", "103")]
        text = "Under Section 103 BNS, the accused is guilty."
        valid, violations = verify_citations(text, chunks)
        assert valid is True
        assert violations == []

    def test_invalid_citation(self) -> None:
        chunks = [_make_chunk("BNS", "103")]
        text = "Under Section 303 BNS, the property was stolen."
        valid, violations = verify_citations(text, chunks)
        assert valid is False
        assert len(violations) == 1
        assert "303" in violations[0]

    def test_mixed_valid_and_invalid(self) -> None:
        chunks = [_make_chunk("BNS", "103"), _make_chunk("BNSS", "173")]
        text = "Section 103 BNS and Section 999 BNSS were considered."
        valid, violations = verify_citations(text, chunks)
        assert valid is False
        assert len(violations) == 1
        assert "999" in violations[0]

    def test_no_citations_is_valid(self) -> None:
        chunks = [_make_chunk("BNS", "103")]
        text = "The witness testified about the events."
        valid, violations = verify_citations(text, chunks)
        assert valid is True
        assert violations == []

    def test_split_section_number(self) -> None:
        """Section_no like '103 (Part 1/2)' still matches citation of 103."""
        chunks = [_make_chunk("BNS", "103 (Part 1/2)")]
        text = "Under Section 103 BNS, murder is punishable."
        valid, violations = verify_citations(text, chunks)
        assert valid is True

    def test_ipc_equivalent_in_chunks(self) -> None:
        chunks = [_make_chunk("BNS", "103", ipc_eq="302")]
        text = "Under IPC 302, the accused was charged."
        valid, violations = verify_citations(text, chunks)
        # IPC 302 resolves to BNS 103 which is in chunks
        assert valid is True
