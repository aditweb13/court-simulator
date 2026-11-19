"""create trials, agents, and turns tables and link llm_calls foreign key

Revision ID: 005_trials_agents_turns
Revises: 004_cases_evidence_witnesses
Create Date: 2026-11-19

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "005_trials_agents_turns"
down_revision: Union[str, None] = "004_cases_evidence_witnesses"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Trials table
    op.create_table(
        "trials",
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
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("mode", sa.Text(), nullable=False),  # watch | lawyer | judge | juror
        sa.Column("human_role", sa.Text(), nullable=True),
        sa.Column("state", sa.Text(), server_default=sa.text("'SETUP'"), nullable=False),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("trials_user_idx", "trials", ["user_id"])
    op.create_index("trials_case_idx", "trials", ["case_id"])

    # 2. Add deferred foreign key from llm_calls.trial_id to trials.id
    op.create_foreign_key(
        "fk_llm_calls_trial_id_trials",
        "llm_calls",
        "trials",
        ["trial_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # 3. Agents table
    op.create_table(
        "agents",
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
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column(
            "persona",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("tier", sa.Text(), nullable=False),  # strong | mid | small
        sa.Column(
            "memory",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )
    op.create_index("agents_trial_idx", "agents", ["trial_id"])

    # 4. Turns table
    op.create_table(
        "turns",
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
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column(
            "agent_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("agents.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("speaker_role", sa.Text(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("action", sa.Text(), nullable=True),
        sa.Column("emotion", sa.Text(), nullable=True),
        sa.Column("camera", sa.Text(), nullable=True),
        sa.Column("objection", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("admitted", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("struck", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("trial_id", "seq", name="uq_turns_trial_id_seq"),
    )
    op.create_index("turns_trial_idx", "turns", ["trial_id"])


def downgrade() -> None:
    op.drop_index("turns_trial_idx", table_name="turns")
    op.drop_table("turns")

    op.drop_index("agents_trial_idx", table_name="agents")
    op.drop_table("agents")

    op.drop_constraint("fk_llm_calls_trial_id_trials", "llm_calls", type_="foreignkey")

    op.drop_index("trials_case_idx", table_name="trials")
    op.drop_index("trials_user_idx", table_name="trials")
    op.drop_table("trials")
