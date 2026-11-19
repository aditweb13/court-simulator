"""SQLAlchemy 2.0 models for Trials, Agents, and Turns."""

from __future__ import annotations

import datetime
import uuid
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from uuid import UUID

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy import (
    text as sa_text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.case import Case
    from app.db.models.user import User


class Trial(Base):
    __tablename__ = "trials"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=sa_text("gen_random_uuid()"),
    )
    case_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    mode: Mapped[str] = mapped_column(Text, nullable=False)  # watch | lawyer | judge | juror
    human_role: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    state: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="SETUP",
        server_default=sa_text("'SETUP'"),
    )
    config: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    started_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    finished_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    case: Mapped[Case] = relationship("Case")
    user: Mapped[Optional[User]] = relationship("User")
    agents: Mapped[List[Agent]] = relationship(
        "Agent",
        back_populates="trial",
        cascade="all, delete-orphan",
        order_by="Agent.role",
    )
    turns: Mapped[List[Turn]] = relationship(
        "Turn",
        back_populates="trial",
        cascade="all, delete-orphan",
        order_by="Turn.seq",
    )
    votes: Mapped[List[Vote]] = relationship(
        "Vote",
        back_populates="trial",
        cascade="all, delete-orphan",
    )
    verdict: Mapped[Optional[Verdict]] = relationship(
        "Verdict",
        back_populates="trial",
        uselist=False,
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("trials_user_idx", "user_id"),
        Index("trials_case_idx", "case_id"),
    )


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=sa_text("gen_random_uuid()"),
    )
    trial_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("trials.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(Text, nullable=False)
    persona: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=sa_text("'{}'::jsonb"),
    )
    tier: Mapped[str] = mapped_column(Text, nullable=False)  # strong | mid | small
    memory: Mapped[List[Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=sa_text("'[]'::jsonb"),
    )

    trial: Mapped[Trial] = relationship("Trial", back_populates="agents")
    turns: Mapped[List[Turn]] = relationship("Turn", back_populates="agent")

    __table_args__ = (Index("agents_trial_idx", "trial_id"),)


class Turn(Base):
    __tablename__ = "turns"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=sa_text("gen_random_uuid()"),
    )
    trial_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("trials.id", ondelete="CASCADE"),
        nullable=False,
    )
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    agent_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="SET NULL"),
        nullable=True,
    )
    speaker_role: Mapped[str] = mapped_column(Text, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    action: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    emotion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    camera: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    objection: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    admitted: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=sa_text("true"),
    )
    struck: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=sa_text("false"),
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    trial: Mapped[Trial] = relationship("Trial", back_populates="turns")
    agent: Mapped[Optional[Agent]] = relationship("Agent", back_populates="turns")
    embedding_record: Mapped[Optional[TurnEmbedding]] = relationship(
        "TurnEmbedding",
        back_populates="turn",
        uselist=False,
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("trial_id", "seq", name="uq_turns_trial_id_seq"),
        Index("turns_trial_idx", "trial_id"),
    )


class TurnEmbedding(Base):
    __tablename__ = "turn_embeddings"

    turn_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("turns.id", ondelete="CASCADE"),
        primary_key=True,
    )
    trial_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("trials.id", ondelete="CASCADE"),
        nullable=False,
    )
    embedding: Mapped[List[float]] = mapped_column(Vector(1024), nullable=False)

    turn: Mapped[Turn] = relationship("Turn", back_populates="embedding_record")

    __table_args__ = (Index("turn_emb_trial_idx", "trial_id"),)


class Vote(Base):
    __tablename__ = "votes"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=sa_text("gen_random_uuid()"),
    )
    trial_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("trials.id", ondelete="CASCADE"),
        nullable=False,
    )
    agent_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
    )
    kind: Mapped[str] = mapped_column(Text, nullable=False)  # juror_pre | juror_final | judge
    guilty: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    guilt_probability: Mapped[Optional[float]] = mapped_column(Numeric(4, 3), nullable=True)
    confidence: Mapped[Optional[float]] = mapped_column(Numeric(4, 3), nullable=True)
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    cited_turn_ids: Mapped[List[UUID]] = mapped_column(
        ARRAY(PG_UUID(as_uuid=True)),
        nullable=False,
        default=list,
        server_default=sa_text("'{}'"),
    )
    cited_chunk_ids: Mapped[List[int]] = mapped_column(
        ARRAY(BigInteger),
        nullable=False,
        default=list,
        server_default=sa_text("'{}'"),
    )

    trial: Mapped[Trial] = relationship("Trial", back_populates="votes")
    agent: Mapped[Agent] = relationship("Agent")

    __table_args__ = (Index("votes_trial_idx", "trial_id"),)


class Verdict(Base):
    __tablename__ = "verdicts"

    trial_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("trials.id", ondelete="CASCADE"),
        primary_key=True,
    )
    j: Mapped[float] = mapped_column(Numeric(4, 3), nullable=False)
    p: Mapped[float] = mapped_column(Numeric(4, 3), nullable=False)
    score: Mapped[float] = mapped_column(Numeric(4, 3), nullable=False)
    threshold: Mapped[float] = mapped_column(Numeric(4, 3), nullable=False)
    outcome: Mapped[str] = mapped_column(Text, nullable=False)  # guilty | not_guilty | hung
    disagreement: Mapped[float] = mapped_column(Numeric(4, 3), nullable=False)
    matches_truth: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    trial: Mapped[Trial] = relationship("Trial", back_populates="verdict")
