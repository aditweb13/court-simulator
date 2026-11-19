"""Hybrid retrieval system for statutory legal knowledge base.

Implements multi-stage hybrid retrieval:
1. Exact statutory section/article regex lookup (including IPC concordance resolution)
2. PostgreSQL Full-Text Search (top 20) with ts_rank
3. Vector similarity search with BGE-M3 embeddings and pgvector (top 20)
4. Reciprocal Rank Fusion (RRF with k=60)
5. Cross-encoder reranking with BGE-Reranker-v2-m3 returning top k (default 5).

Strictly enforces role filtering (:role = ANY(audience)) and temporal validity filters.
"""

from __future__ import annotations

import datetime
import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple
from uuid import UUID

from sqlalchemy import or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.knowledge import KnowledgeChunk
from app.db.session import async_session_maker
from app.rag.embeddings import BaseEmbedder, get_embedder
from app.rag.ipc_bns_map import get_bns_equivalent
from app.rag.reranker import BaseReranker, get_reranker

logger = logging.getLogger(__name__)


@dataclass
class RetrievedChunk:
    """A statutory law chunk returned by the hybrid retrieval engine."""

    id: int | UUID
    act: str
    section_no: str
    title: str
    body: str
    domain: str
    audience: List[str]
    score: float
    ipc_equivalent: Optional[str] = None
    parent_section: Optional[str] = None


def detect_referenced_act(query: str) -> Optional[str]:
    """Detect which statutory act or Constitution is referenced in the query."""
    ql = query.lower()
    if "bharatiya nagarik suraksha sanhita" in ql or re.search(r"\bbnss\b", ql):
        return "BNSS"
    if "bharatiya nyaya sanhita" in ql or re.search(r"\bbns\b", ql):
        return "BNS"
    if "bharatiya sakshya adhiniyam" in ql or re.search(r"\bbsa\b", ql) or "evidence act" in ql:
        return "BSA"
    if "constitution" in ql or re.search(r"\bcoi\b", ql) or re.search(r"\barticle\b", ql):
        return "CONSTITUTION"
    if re.search(r"\bipc\b", ql) or "penal code" in ql:
        return "BNS"
    return None


# Pattern to detect exact statutory citations in legal queries
_EXACT_CITATION_PATTERNS = [
    # "BNS 103", "BNS Section 103", "Section 103 of BNS", full act names
    re.compile(
        r"\b(?:Section|Sec\.?|s\.)\s*(\d+[A-Z]?)\s*(?:of\s+(?:the\s+)?)?("
        r"BNS|BNSS|BSA|Bharatiya\s+Nyaya\s+Sanhita|Bharatiya\s+Nagarik\s+Suraksha\s+Sanhita|"
        r"Bharatiya\s+Sakshya\s+Adhiniyam)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b("
        r"BNS|BNSS|BSA|Bharatiya\s+Nyaya\s+Sanhita|Bharatiya\s+Nagarik\s+Suraksha\s+Sanhita|"
        r"Bharatiya\s+Sakshya\s+Adhiniyam)\s*(?:Section|Sec\.?|s\.)?\s*(\d+[A-Z]?)\b",
        re.IGNORECASE,
    ),
    # "Article 21", "Art. 21", "Article 21 of Constitution"
    re.compile(
        r"\b(?:Article|Art\.?)\s*(\d+[A-Z]?)(?:\s*(?:of\s+(?:the\s+)?)?(?:Constitution|COI))?\b",
        re.IGNORECASE,
    ),
    # Historical IPC references: "IPC 302", "Section 302 IPC"
    re.compile(
        r"\b(?:Section|Sec\.?|s\.)?\s*(\d+[A-Z]?)\s*(?:of\s+(?:the\s+)?)?(IPC|Indian\s+Penal\s+Code)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(IPC|Indian\s+Penal\s+Code)\s*(?:Section|Sec\.?|s\.)?\s*(\d+[A-Z]?)\b",
        re.IGNORECASE,
    ),
]


def extract_exact_citation(query: str) -> Optional[Tuple[str, str]]:
    """Extract exact act and section/article numbers from a query string.

    Converts IPC section queries to modern BNS sections via concordance table.
    """
    for pat in _EXACT_CITATION_PATTERNS:
        match = pat.search(query)
        if match:
            matched_text = match.group(0).upper()
            groups = match.groups()

            if "IPC" in matched_text or "PENAL" in matched_text:
                sec_val = groups[0].strip() if groups[0].isdigit() else groups[1].strip()
                bns_num = get_bns_equivalent(sec_val)
                return "BNS", bns_num if bns_num else sec_val

            if len(groups) == 1:
                # Article match for Constitution
                return "CONSTITUTION", groups[0].strip()

            val1, val2 = groups[0].strip(), groups[1].strip()
            act1 = detect_referenced_act(val1)
            act2 = detect_referenced_act(val2)
            if act1 in {"BNS", "BNSS", "BSA"}:
                return act1, val2
            elif act2 in {"BNS", "BNSS", "BSA"}:
                return act2, val1

    return None


async def _fetch_exact_candidates(
    session: AsyncSession,
    act: str,
    section_no: str,
    role: str,
    as_of: Optional[datetime.date],
) -> List[KnowledgeChunk]:
    """Fetch exact matching section and its sub-parts with role and date filters."""
    query = (
        select(KnowledgeChunk)
        .where(
            KnowledgeChunk.act == act,
            text(":role = ANY(knowledge_chunks.audience)"),
            or_(
                KnowledgeChunk.section_no == section_no,
                KnowledgeChunk.section_no.like(f"{section_no} (%"),
            ),
        )
        .params(role=role)
    )

    if as_of is not None:
        query = query.where(
            (KnowledgeChunk.valid_to.is_(None)) | (KnowledgeChunk.valid_to >= as_of),
            (KnowledgeChunk.valid_from.is_(None)) | (KnowledgeChunk.valid_from <= as_of),
        )

    result = await session.execute(query)
    return list(result.scalars().all())


# Words that occur in act names / boilerplate and pollute FTS ranking.
# These are stripped from the user query *before* plainto_tsquery.
_FTS_STOPWORDS = {
    "bharatiya",
    "nyaya",
    "sanhita",
    "nagarik",
    "suraksha",
    "sakshya",
    "adhiniyam",
    "constitution",
    "india",
    "indian",
    "bns",
    "bnss",
    "bsa",
    "ipc",
    "crpc",
    "under",
    "section",
    "article",
    "sec",
    "art",
    "act",
    "code",
    "law",
    "provisions",
    "provision",
    "what",
    "which",
    "how",
    "when",
    "where",
    "who",
    "does",
    "the",
    "of",
    "is",
    "in",
    "for",
    "and",
    "or",
    "to",
    "a",
    "an",
}


def _clean_fts_query(raw: str) -> str:
    """Strip act-name keywords and common noise from a query for FTS."""
    words = re.sub(r"[^\w\s]", " ", raw).lower().split()
    meaningful = [w for w in words if w not in _FTS_STOPWORDS]
    return " ".join(meaningful) if meaningful else " ".join(words[:3])


_EXTRA_SEARCH_STOPWORDS = {
    "definition",
    "punishment",
    "punished",
    "offence",
    "offences",
    "what",
    "which",
    "how",
    "when",
    "where",
    "under",
    "act",
    "section",
    "article",
    "provisions",
    "procedure",
    "cases",
    "case",
    "code",
    "law",
    "res",
    "gestae",
    "remand",
    "dying",
    "declaration",
}


async def _fetch_fts_candidates(
    session: AsyncSession,
    query_text: str,
    role: str,
    as_of: Optional[datetime.date],
    act: Optional[str] = None,
    limit: int = 20,
) -> List[KnowledgeChunk]:
    """Fetch PostgreSQL full-text search candidates ranked by ts_rank.

    Uses weighted tsvector (title=A, body=D) and strips act-name noise words
    from the query to avoid ranking pollution from boilerplate mentions.
    Falls back to substantive keyword OR search if strict conjunction yields < 5 candidates.
    """
    clean_q = _clean_fts_query(query_text)
    if not clean_q.strip():
        return []

    date_filter = ""
    params: Dict[str, Any] = {"query": clean_q, "role": role, "limit": limit}
    if as_of is not None:
        date_filter = (
            "AND (valid_to IS NULL OR valid_to >= :as_of) "
            "AND (valid_from IS NULL OR valid_from <= :as_of)"
        )
        params["as_of"] = as_of

    act_filter = ""
    if act:
        act_filter = "AND act = :act"
        params["act"] = act

    sql_plain = text(
        f"""
        SELECT id, act, section_no, title, body, domain, audience, ipc_equivalent,
               valid_from, valid_to, source, license, embedding_model, embedding,
               ts_rank(
                   setweight(to_tsvector('english', coalesce(title, '')), 'A')
                     || setweight(to_tsvector('english', coalesce(body, '')), 'D'),
                   plainto_tsquery('english', :query),
                   32
               ) AS rank
        FROM knowledge_chunks
        WHERE :role = ANY(audience)
          {act_filter}
          {date_filter}
          AND (
            setweight(to_tsvector('english', coalesce(title, '')), 'A')
              || setweight(to_tsvector('english', coalesce(body, '')), 'D')
          ) @@ plainto_tsquery('english', :query)
        ORDER BY rank DESC
        LIMIT :limit
        """
    )

    res = await session.execute(sql_plain, params)
    rows = res.fetchall()

    if len(rows) < 5:
        # Fallback to substantive topical keywords with to_tsquery OR
        words = [w for w in clean_q.split() if len(w) > 2 and w not in _EXTRA_SEARCH_STOPWORDS]
        if not words:
            words = [w for w in clean_q.split() if len(w) > 2]
        if words:
            or_tsquery = " | ".join(words)
            or_params = dict(params)
            or_params["tsquery"] = or_tsquery
            sql_or = text(
                f"""
                SELECT id, act, section_no, title, body, domain, audience, ipc_equivalent,
                       valid_from, valid_to, source, license, embedding_model, embedding,
                       ts_rank(
                           setweight(to_tsvector('english', coalesce(title, '')), 'A')
                             || setweight(to_tsvector('english', coalesce(body, '')), 'D'),
                           to_tsquery('english', :tsquery),
                           32
                       ) AS rank
                FROM knowledge_chunks
                WHERE :role = ANY(audience)
                  {act_filter}
                  {date_filter}
                  AND (
                    setweight(to_tsvector('english', coalesce(title, '')), 'A')
                      || setweight(to_tsvector('english', coalesce(body, '')), 'D')
                  ) @@ to_tsquery('english', :tsquery)
                ORDER BY rank DESC
                LIMIT :limit
                """
            )
            res_or = await session.execute(sql_or, or_params)
            rows = res_or.fetchall()

    chunks: List[KnowledgeChunk] = []
    for r in rows:
        chunk = KnowledgeChunk(
            id=r[0],
            act=r[1],
            section_no=r[2],
            title=r[3],
            body=r[4],
            domain=r[5],
            audience=r[6],
            ipc_equivalent=r[7],
            valid_from=r[8],
            valid_to=r[9],
            source=r[10],
            license=r[11],
            embedding_model=r[12],
            embedding=r[13],
        )
        chunks.append(chunk)

    return chunks


async def _fetch_vector_candidates(
    session: AsyncSession,
    query_vector: List[float],
    role: str,
    as_of: Optional[datetime.date],
    act: Optional[str] = None,
    limit: int = 20,
) -> List[KnowledgeChunk]:
    """Fetch vector candidates using pgvector cosine distance <=>."""
    vec_str = "[" + ",".join(str(f) for f in query_vector) + "]"

    date_filter = ""
    params: Dict[str, Any] = {"query_vec": vec_str, "role": role, "limit": limit}
    if as_of is not None:
        date_filter = (
            "AND (valid_to IS NULL OR valid_to >= :as_of) "
            "AND (valid_from IS NULL OR valid_from <= :as_of)"
        )
        params["as_of"] = as_of

    act_filter = ""
    if act:
        act_filter = "AND act = :act"
        params["act"] = act

    sql = text(
        f"""
        SELECT id, act, section_no, title, body, domain, audience, ipc_equivalent,
               valid_from, valid_to, source, license, embedding_model, embedding,
               embedding <=> :query_vec AS dist
        FROM knowledge_chunks
        WHERE :role = ANY(audience)
          {act_filter}
          {date_filter}
        ORDER BY dist ASC
        LIMIT :limit
        """
    )

    res = await session.execute(sql, params)
    rows = res.fetchall()
    chunks: List[KnowledgeChunk] = []
    for r in rows:
        chunk = KnowledgeChunk(
            id=r[0],
            act=r[1],
            section_no=r[2],
            title=r[3],
            body=r[4],
            domain=r[5],
            audience=r[6],
            ipc_equivalent=r[7],
            valid_from=r[8],
            valid_to=r[9],
            source=r[10],
            license=r[11],
            embedding_model=r[12],
            embedding=r[13],
        )
        chunks.append(chunk)

    return chunks


def _reciprocal_rank_fusion(
    ranked_lists: Sequence[Sequence[KnowledgeChunk]],
    k: int = 60,
) -> List[Tuple[KnowledgeChunk, float]]:
    """Merge multiple ranked candidate lists using Reciprocal Rank Fusion (RRF)."""
    scores: Dict[Any, float] = {}
    chunk_map: Dict[Any, KnowledgeChunk] = {}

    for ranked_list in ranked_lists:
        for rank, chunk in enumerate(ranked_list):
            chunk_id = chunk.id
            chunk_map[chunk_id] = chunk
            scores[chunk_id] = scores.get(chunk_id, 0.0) + (1.0 / (k + rank + 1))

    sorted_items = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    return [(chunk_map[cid], score) for cid, score in sorted_items]


async def retrieve(
    query: str,
    role: str = "judge",
    k: int = 5,
    as_of: Optional[datetime.date] = None,
    session: Optional[AsyncSession] = None,
    embedder: Optional[BaseEmbedder] = None,
    reranker: Optional[BaseReranker] = None,
) -> List[RetrievedChunk]:
    """Hybrid retrieval of legal knowledge chunks.

    Steps:
      (1) Exact section/article lookup if cited in query
      (2) Full-text search (top 20)
      (3) Vector candidate search (top 20) with bge-m3 embedding
      (4) Reciprocal Rank Fusion (RRF, k=60)
      (5) Cross-encoder reranking of top 20 candidates, returning top k (default 5).

    Strictly applies role filter (:role = ANY(audience)) and as_of date validity.
    """
    embed_engine = embedder or get_embedder()
    rerank_engine = reranker or get_reranker()

    async def _do_retrieve(db_session: AsyncSession) -> List[RetrievedChunk]:
        act_scope = detect_referenced_act(query)

        # Step 1: Exact lookup
        exact_chunks: List[KnowledgeChunk] = []
        exact_ref = extract_exact_citation(query)
        if exact_ref:
            act, sec = exact_ref
            exact_chunks = await _fetch_exact_candidates(
                db_session, act, sec, role=role, as_of=as_of
            )

        # Step 2: Postgres full-text search candidates (top 20)
        fts_chunks = await _fetch_fts_candidates(
            db_session, query, role=role, as_of=as_of, act=act_scope, limit=20
        )

        # Step 3: Vector search candidates (top 20)
        query_vector = embed_engine.embed_query(query)
        vector_chunks = await _fetch_vector_candidates(
            db_session, query_vector, role=role, as_of=as_of, act=act_scope, limit=20
        )

        # Step 4: Reciprocal Rank Fusion (k=60)
        ranked_lists = []
        if exact_chunks:
            ranked_lists.append(exact_chunks)
        if fts_chunks:
            ranked_lists.append(fts_chunks)
        if vector_chunks:
            ranked_lists.append(vector_chunks)

        if not ranked_lists:
            return []

        rrf_merged = _reciprocal_rank_fusion(ranked_lists, k=60)
        top_20_candidates = [chunk for chunk, _ in rrf_merged[:20]]
        rrf_scores = [score for _, score in rrf_merged[:20]]

        # Step 5: Cross-encoder rerank
        passages = [
            f"{c.act} Section {c.section_no}: {c.title}. {c.body}" for c in top_20_candidates
        ]
        reranked_scores = rerank_engine.rerank(query, passages, prior_scores=rrf_scores)

        # Return top k
        results: List[RetrievedChunk] = []
        for rank_idx, score in reranked_scores[:k]:
            c = top_20_candidates[rank_idx]
            results.append(
                RetrievedChunk(
                    id=c.id,
                    act=c.act or "",
                    section_no=c.section_no or "",
                    title=c.title or "",
                    body=c.body,
                    domain=c.domain,
                    audience=c.audience,
                    score=float(score),
                    ipc_equivalent=c.ipc_equivalent,
                )
            )

        return results

    if session is not None:
        return await _do_retrieve(session)
    else:
        async with async_session_maker() as new_session:
            return await _do_retrieve(new_session)
