"""create cases, evidence, and witnesses tables

Revision ID: 004_cases_evidence_witnesses
Revises: 003_knowledge_chunks
Create Date: 2026-11-18

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "004_cases_evidence_witnesses"
down_revision: Union[str, None] = "003_knowledge_chunks"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Cases table
    op.create_table(
        "cases",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("slug", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("jurisdiction", sa.Text(), server_default=sa.text("'IN'"), nullable=False),
        sa.Column("charge", sa.Text(), nullable=False),
        sa.Column("difficulty", sa.SmallInteger(), server_default=sa.text("1"), nullable=False),
        sa.Column("truth", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_cases_slug", "cases", ["slug"], unique=True)

    # 2. Evidence table
    op.create_table(
        "evidence",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "case_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cases.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("exhibit_no", sa.Text(), nullable=False),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("admissible", sa.Boolean(), nullable=False),
        sa.Column("reason_inadmissible", sa.Text(), nullable=True),
    )
    op.create_index("evidence_case_idx", "evidence", ["case_id"])

    # 3. Witnesses table
    op.create_table(
        "witnesses",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "case_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cases.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("saw_event_ids", postgresql.ARRAY(sa.Integer()), nullable=False),
        sa.Column("reliability", sa.Numeric(precision=3, scale=2), nullable=False),
        sa.Column(
            "hides",
            postgresql.ARRAY(sa.Text()),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column(
            "persona",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.CheckConstraint("reliability BETWEEN 0 AND 1", name="witness_reliability_range"),
    )
    op.create_index("witnesses_case_idx", "witnesses", ["case_id"])


def downgrade() -> None:
    op.drop_index("witnesses_case_idx", table_name="witnesses")
    op.drop_table("witnesses")
    op.drop_index("evidence_case_idx", table_name="evidence")
    op.drop_table("evidence")
    op.drop_index("ix_cases_slug", table_name="cases")
    op.drop_table("cases")
