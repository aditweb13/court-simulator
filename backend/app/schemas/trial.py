"""Pydantic schemas for Trials, Trial Configuration, and Agents."""

from __future__ import annotations

import datetime
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TrialConfig(BaseModel):
    """Configuration governing trial rules, juror counts, and thresholds."""

    model_config = ConfigDict(extra="forbid")

    juror_count: int = Field(
        default=3,
        ge=1,
        le=12,
        description="Number of juror agents to convene (3 in dev mode, up to 12)",
    )
    rounds: int = Field(
        default=1,
        ge=1,
        le=5,
        description="Number of juror deliberation rounds (1 in dev mode, up to 5)",
    )
    threshold: float = Field(
        default=0.75,
        ge=0.0,
        le=1.0,
        description="Criminal conviction guilt threshold (default: 0.75 beyond reasonable doubt)",
    )
    hung_band: float = Field(
        default=0.05,
        ge=0.0,
        le=0.5,
        description="Band around threshold for hung verdict (default: 0.05)",
    )


class TrialCreate(BaseModel):
    """Request payload to initiate a new courtroom trial."""

    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(description="UUID or slug of the case to simulate")
    mode: Literal["watch", "lawyer", "judge", "juror"] = Field(
        default="watch", description="Simulation mode"
    )
    human_role: Optional[Literal["judge", "prosecutor", "defense", "juror"]] = Field(
        default=None, description="Role assumed by human participant if in interactive mode"
    )
    config: Optional[TrialConfig] = Field(
        default=None, description="Custom configuration parameters override"
    )


class AgentSummary(BaseModel):
    """Public representation of an agent assigned to a trial."""

    id: UUID
    role: str
    tier: str
    persona: Dict[str, Any] = Field(default_factory=dict)


class TrialRead(BaseModel):
    """Concise representation of a trial for listings."""

    id: UUID
    case_id: UUID
    user_id: Optional[UUID] = None
    mode: str
    human_role: Optional[str] = None
    state: str
    config: Dict[str, Any]
    started_at: datetime.datetime
    finished_at: Optional[datetime.datetime] = None


class TrialDetail(BaseModel):
    """Detailed courtroom trial state including participants and turn counts."""

    id: UUID
    case_id: UUID
    case_title: str
    case_slug: str
    user_id: Optional[UUID] = None
    mode: str
    human_role: Optional[str] = None
    state: str
    config: Dict[str, Any]
    started_at: datetime.datetime
    finished_at: Optional[datetime.datetime] = None
    agents: List[AgentSummary] = Field(default_factory=list)
    turns_count: int = 0


class VerdictVoteDetail(BaseModel):
    """Details of an individual vote cast by a juror or verdict judge."""

    agent_id: UUID
    role: str
    kind: str  # juror_pre | juror_final | judge
    guilty: Optional[bool] = None
    guilt_probability: Optional[float] = None
    confidence: Optional[float] = None
    reasoning: str
    cited_turn_ids: List[UUID] = Field(default_factory=list)


class VerdictDetail(BaseModel):
    """Full trial verdict review including jury, judicial bench, and truth evaluation."""

    trial_id: UUID
    outcome: str  # guilty | not_guilty | hung
    score: float
    j: float
    p: float
    threshold: float
    disagreement: float
    matches_truth: Optional[bool] = None
    truth: Optional[Dict[str, Any]] = None
    sentence: Optional[Dict[str, Any]] = None
    judge_votes: List[VerdictVoteDetail] = Field(default_factory=list)
    juror_final_votes: List[VerdictVoteDetail] = Field(default_factory=list)
    juror_pre_votes: List[VerdictVoteDetail] = Field(default_factory=list)
