"""create knowledge_chunks table

Revision ID: 003_knowledge_chunks
Revises: 002_llm_calls
Create Date: 2026-11-18

"""
from typing import Sequence, Union

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "003_knowledge_chunks"
down_revision: Union[str, None] = "002_llm_calls"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "knowledge_chunks",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("domain", sa.Text(), nullable=False),
        sa.Column("audience", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("act", sa.Text(), nullable=True),
        sa.Column("section_no", sa.Text(), nullable=True),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("ipc_equivalent", sa.Text(), nullable=True),
        sa.Column("valid_from", sa.Date(), nullable=True),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("source", sa.Text(), nullable=True),
        sa.Column("license", sa.Text(), nullable=True),
        # Added per decision log
        sa.Column("embedding_model", sa.Text(), nullable=True),
        sa.Column(
            "ingested_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        # Full-text tsvector computed column
        sa.Column(
            "tsv",
            postgresql.TSVECTOR(),
            sa.Computed(
                "to_tsvector('english', coalesce(title,'') || ' ' || body)",
                persisted=True,
            ),
            nullable=True,
        ),
        # Dense vector embedding
        sa.Column("embedding", Vector(1024), nullable=False),
    )

    op.create_index(
        "kc_hnsw",
        "knowledge_chunks",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )
    op.create_index("kc_tsv", "knowledge_chunks", ["tsv"], postgresql_using="gin")
    op.create_index("kc_lookup", "knowledge_chunks", ["act", "section_no"])
    op.create_index("kc_domain", "knowledge_chunks", ["domain"])


def downgrade() -> None:
    op.drop_index("kc_domain", table_name="knowledge_chunks")
    op.drop_index("kc_lookup", table_name="knowledge_chunks")
    op.drop_index("kc_tsv", table_name="knowledge_chunks")
    op.drop_index("kc_hnsw", table_name="knowledge_chunks")
    op.drop_table("knowledge_chunks")
