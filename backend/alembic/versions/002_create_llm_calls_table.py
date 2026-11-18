"""create llm_calls table

Revision ID: 002_llm_calls
Revises: 001_users
Create Date: 2026-11-18

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "002_llm_calls"
down_revision: Union[str, None] = "001_users"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # trial_id is created as nullable UUID WITHOUT foreign key because the trials
    # table is introduced in Phase 5. FK will be added in Phase 5 trials migration.
    op.create_table(
        "llm_calls",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("trial_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("agent_role", sa.Text(), nullable=True),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column("key_alias", sa.String(length=64), nullable=False),
        sa.Column("tokens_in", sa.Integer(), nullable=True),
        sa.Column("tokens_out", sa.Integer(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("llm_calls_trial_idx", "llm_calls", ["trial_id"])


def downgrade() -> None:
    op.drop_index("llm_calls_trial_idx", table_name="llm_calls")
    op.drop_table("llm_calls")

