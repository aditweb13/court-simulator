"""create votes and verdicts tables

Revision ID: 007_votes_verdicts
Revises: 006_turn_embeddings
Create Date: 2026-11-19

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "007_votes_verdicts"
down_revision: Union[str, None] = "006_turn_embeddings"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "votes",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "trial_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("trials.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "agent_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("agents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", sa.Text(), nullable=False),  # juror_pre | juror_final | judge
        sa.Column("guilty", sa.Boolean(), nullable=True),
        sa.Column("guilt_probability", sa.Numeric(4, 3), nullable=True),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=True),
        sa.Column("reasoning", sa.Text(), nullable=False),
        sa.Column(
            "cited_turn_ids",
            postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column(
            "cited_chunk_ids",
            postgresql.ARRAY(sa.BigInteger()),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
    )
    op.create_index("votes_trial_idx", "votes", ["trial_id"])

    op.create_table(
        "verdicts",
        sa.Column(
            "trial_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("trials.id", ondelete="CASCADE"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("j", sa.Numeric(4, 3), nullable=False),
        sa.Column("p", sa.Numeric(4, 3), nullable=False),
        sa.Column("score", sa.Numeric(4, 3), nullable=False),
        sa.Column("threshold", sa.Numeric(4, 3), nullable=False),
        sa.Column("outcome", sa.Text(), nullable=False),  # guilty | not_guilty | hung
        sa.Column("disagreement", sa.Numeric(4, 3), nullable=False),
        sa.Column("matches_truth", sa.Boolean(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("verdicts")
    op.drop_index("votes_trial_idx", table_name="votes")
    op.drop_table("votes")
