"""create turn_embeddings table with pgvector and hnsw index

Revision ID: 006_turn_embeddings
Revises: 005_trials_agents_turns
Create Date: 2026-11-19

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "006_turn_embeddings"
down_revision: Union[str, None] = "005_trials_agents_turns"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "turn_embeddings",
        sa.Column(
            "turn_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("turns.id", ondelete="CASCADE"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "trial_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("trials.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "embedding",
            Vector(1024),
            nullable=False,
        ),
    )

    # Indexes per Architecture.md
    op.create_index("turn_emb_trial_idx", "turn_embeddings", ["trial_id"])
    op.execute(
        "CREATE INDEX turn_emb_hnsw ON turn_embeddings USING hnsw (embedding vector_cosine_ops);"
    )


def downgrade() -> None:
    op.drop_index("turn_emb_trial_idx", table_name="turn_embeddings")
    op.execute("DROP INDEX IF EXISTS turn_emb_hnsw;")
    op.drop_table("turn_embeddings")
