"""SQLAlchemy 2.0 models for Trials, Agents, and Turns."""

from __future__ import annotations

import datetime
import uuid
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy import (
    text as sa_text,
)
from sqlalchemy.dialects.postgresql import JSONB
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

    __table_args__ = (
        UniqueConstraint("trial_id", "seq", name="uq_turns_trial_id_seq"),
        Index("turns_trial_idx", "trial_id"),
    )
