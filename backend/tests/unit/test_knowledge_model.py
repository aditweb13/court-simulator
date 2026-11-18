"""Unit tests for KnowledgeChunk model and indexes."""

import datetime

from app.db.models.knowledge import KnowledgeChunk


def test_knowledge_chunk_model_instantiation() -> None:
    chunk = KnowledgeChunk(
        domain="statute",
        audience=["judge", "lawyer"],
        act="BNS",
        section_no="103",
        title="Punishment for murder",
        body="Whoever commits murder shall be punished with death or imprisonment for life...",
        ipc_equivalent="IPC 302",
        valid_from=datetime.date(2024, 7, 1),
        source="Official Gazette of India",
        license="Public Domain (Government Work)",
        embedding_model="BAAI/bge-m3",
        embedding=[0.01] * 1024,
    )

    assert chunk.domain == "statute"
    assert chunk.audience == ["judge", "lawyer"]
    assert chunk.act == "BNS"
    assert chunk.section_no == "103"
    assert chunk.ipc_equivalent == "IPC 302"
    assert chunk.embedding_model == "BAAI/bge-m3"
    assert len(chunk.embedding) == 1024


def test_knowledge_chunk_indexes_definition() -> None:
    table = KnowledgeChunk.__table__
    index_names = {idx.name for idx in table.indexes}

    assert "kc_hnsw" in index_names
    assert "kc_tsv" in index_names
    assert "kc_lookup" in index_names
    assert "kc_domain" in index_names

    # Check HNSW index specifics
    hnsw_idx = next(idx for idx in table.indexes if idx.name == "kc_hnsw")
    assert hnsw_idx.dialect_options["postgresql"]["using"] == "hnsw"
    assert hnsw_idx.dialect_options["postgresql"]["ops"]["embedding"] == "vector_cosine_ops"

    # Check GIN index
    tsv_idx = next(idx for idx in table.indexes if idx.name == "kc_tsv")
    assert tsv_idx.dialect_options["postgresql"]["using"] == "gin"
