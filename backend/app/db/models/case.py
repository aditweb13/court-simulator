"""SQLAlchemy 2.0 models for Cases, Evidence, and Witnesses."""

from __future__ import annotations

import datetime
import uuid
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    SmallInteger,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Case(Base):
    __tablename__ = "cases"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    slug: Mapped[str] = mapped_column(Text, unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    jurisdiction: Mapped[str] = mapped_column(Text, nullable=False, default="IN")
    charge: Mapped[str] = mapped_column(Text, nullable=False)
    difficulty: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)
    truth: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    source: Mapped[str] = mapped_column(Text, nullable=False)  # handwritten | generated
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    evidence: Mapped[List[Evidence]] = relationship(
        "Evidence",
        back_populates="case",
        cascade="all, delete-orphan",
        order_by="Evidence.exhibit_no",
    )
    witnesses: Mapped[List[Witness]] = relationship(
        "Witness",
        back_populates="case",
        cascade="all, delete-orphan",
        order_by="Witness.name",
    )


class Evidence(Base):
    __tablename__ = "evidence"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    case_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False,
    )
    exhibit_no: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    admissible: Mapped[bool] = mapped_column(Boolean, nullable=False)
    reason_inadmissible: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    case: Mapped[Case] = relationship("Case", back_populates="evidence")

    __table_args__ = (Index("evidence_case_idx", "case_id"),)


class Witness(Base):
    __tablename__ = "witnesses"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    case_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    saw_event_ids: Mapped[List[int]] = mapped_column(ARRAY(SmallInteger), nullable=False)
    reliability: Mapped[Decimal] = mapped_column(
        Numeric(3, 2),
        CheckConstraint("reliability BETWEEN 0 AND 1", name="witness_reliability_range"),
        nullable=False,
    )
    hides: Mapped[List[str]] = mapped_column(
        ARRAY(Text),
        nullable=False,
        server_default=text("'{}'"),
        default=list,
    )
    persona: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
        default=dict,
    )

    case: Mapped[Case] = relationship("Case", back_populates="witnesses")

    __table_args__ = (Index("witnesses_case_idx", "case_id"),)
