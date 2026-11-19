"""Pydantic v2 schemas for Cases, Evidence, Witnesses, and Ground Truth."""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TimelineEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int = Field(ge=0, description="0-indexed sequence position in the event timeline")
    time: str = Field(description="Timestamp or relative time string, e.g. 21:30")
    description: str = Field(description="Factual description of what occurred")
    location: str = Field(description="Physical location of the event")
    actors: List[str] = Field(default_factory=list, description="Characters involved or present")


class TruthData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    culprit: str = Field(description="Name of the true perpetrator")
    motive: str = Field(description="Actual motive behind the alleged crime")
    timeline: List[TimelineEvent] = Field(
        min_length=1, description="Complete factual event sequence"
    )
    summary: Optional[str] = Field(default=None, description="Concise overview of the crime")


class EvidenceData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    exhibit_no: str = Field(description="Courtroom label, e.g. Exhibit P-1")
    type: Literal["physical", "documentary", "forensic", "testimonial"] = Field(
        description="Category of the evidence"
    )
    description: str = Field(description="Factual summary of the exhibit")
    admissible: bool = Field(description="Whether the exhibit complies with admissibility rules")
    reason_inadmissible: Optional[str] = Field(
        default=None,
        description="Legal justification if marked inadmissible (e.g. hearsay, chain of custody)",
    )


class WitnessData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="Full character name")
    saw_event_ids: List[int] = Field(
        default_factory=list,
        description="List of timeline event IDs this witness actually witnessed",
    )
    reliability: float = Field(
        ge=0.0,
        le=1.0,
        description="Baseline reliability score between 0.0 and 1.0",
    )
    hides: List[str] = Field(
        default_factory=list,
        description="Facts or lies this witness attempts to conceal under examination",
    )
    persona: Dict[str, Any] = Field(
        default_factory=dict,
        description="Personality traits, emotional baseline, and vocal mannerisms",
    )


class CaseSchema(BaseModel):
    """Full Case definition matching the ground truth and courtroom data schema."""

    model_config = ConfigDict(extra="forbid")

    slug: str = Field(description="Unique human-readable slug, e.g. state-v-sharma")
    title: str = Field(description="Formal legal title of the case")
    jurisdiction: str = Field(default="IN", description="Country/state jurisdiction code")
    charge: str = Field(description="Primary criminal charge, e.g. Murder (BNS 103)")
    difficulty: int = Field(default=1, ge=1, le=5, description="Difficulty level 1 to 5")
    source: Literal["handwritten", "generated"] = Field(
        default="handwritten", description="Origin of the case definition"
    )
    truth: TruthData = Field(description="Hidden objective ground truth")
    evidence: List[EvidenceData] = Field(
        default_factory=list, description="All prosecution and defense exhibits"
    )
    witnesses: List[WitnessData] = Field(
        default_factory=list, description="All witnesses called to testify"
    )


class CaseRead(BaseModel):
    """Response schema for public case views (excluding hidden ground truth)."""

    id: UUID
    slug: str
    title: str
    jurisdiction: str
    charge: str
    difficulty: int
    source: str
    evidence_count: int = 0
    witness_count: int = 0


class EvidenceRead(BaseModel):
    """Public representation of case evidence."""

    id: UUID
    exhibit_no: str
    type: str
    description: str
    admissible: bool
    reason_inadmissible: Optional[str] = None


class WitnessRead(BaseModel):
    """Public representation of case witness."""

    id: UUID
    name: str
    persona: Dict[str, Any] = Field(default_factory=dict)


class CaseDetail(BaseModel):
    """Full public case detail with admitted/marked evidence and witnesses."""

    id: UUID
    slug: str
    title: str
    jurisdiction: str
    charge: str
    difficulty: int
    source: str
    evidence: List[EvidenceRead] = Field(default_factory=list)
    witnesses: List[WitnessRead] = Field(default_factory=list)


def get_case_json_schema() -> Dict[str, Any]:
    """Return the raw JSON Schema dictionary for Case validation."""
    return CaseSchema.model_json_schema()

