"""SQLAlchemy 2.0 model for legal and philosophical knowledge chunks."""

from __future__ import annotations

import datetime
from typing import List, Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
    Computed,
    Date,
    DateTime,
    Index,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    domain: Mapped[str] = mapped_column(Text, nullable=False)
    audience: Mapped[List[str]] = mapped_column(ARRAY(Text), nullable=False)
    act: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    section_no: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    title: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    ipc_equivalent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    valid_from: Mapped[Optional[datetime.date]] = mapped_column(Date, nullable=True)
    valid_to: Mapped[Optional[datetime.date]] = mapped_column(Date, nullable=True)
    source: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    license: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Added per decision log
    embedding_model: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ingested_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Full-text search tsvector computed column
    tsv: Mapped[Optional[str]] = mapped_column(
        TSVECTOR,
        Computed("to_tsvector('english', coalesce(title,'') || ' ' || body)", persisted=True),
        nullable=True,
    )

    # 1024-dimensional dense vector embeddings (BAAI/bge-m3)
    embedding: Mapped[List[float]] = mapped_column(Vector(1024), nullable=False)

    __table_args__ = (
        Index(
            "kc_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
        Index("kc_tsv", "tsv", postgresql_using="gin"),
        Index("kc_lookup", "act", "section_no"),
        Index("kc_domain", "domain"),
    )
