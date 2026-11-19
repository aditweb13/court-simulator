"""Pydantic v2 schemas for the 3-stage case generator."""

from __future__ import annotations

from typing import List

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.case import EvidenceData, TimelineEvent, WitnessData


class CaseGenerateRequest(BaseModel):
    """Input payload to trigger case generation."""

    model_config = ConfigDict(extra="forbid")

    topic: str = Field(
        min_length=3,
        max_length=200,
        description="Factual scenario or offence topic (e.g., 'corporate cyber extortion')",
    )
    difficulty: int = Field(
        default=1,
        ge=1,
        le=5,
        description="Complexity tier from 1 (simple) to 5 (complex legal/factual nuances)",
    )
    jurisdiction: str = Field(
        default="IN",
        description="Jurisdiction code (defaults to 'IN' for Bharatiya Nyaya Sanhita)",
    )


class Stage1TruthOutput(BaseModel):
    """Stage 1: Hidden objective truth, timeline, and statutory charge."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(description="Formal legal title of the case (e.g., State v. Vikram Sharma)")
    slug: str = Field(description="Unique human-readable slug (e.g., state-v-sharma-2024)")
    charge: str = Field(
        description="Formal charge description, e.g. 'Cheating under Section 318(4) of BNS'"
    )
    cited_section: str = Field(
        description="Section number from retrieved statutory chunks, e.g. '318(4)' or '103(1)'"
    )
    culprit: str = Field(description="Full name of the true perpetrator")
    motive: str = Field(description="Underlying motive and rationale behind the alleged offence")
    summary: str = Field(description="Objective factual summary of what truly happened")
    timeline: List[TimelineEvent] = Field(
        min_length=3,
        description="Chronological event sequence with ISO dates on or after 2024-07-01",
    )


class Stage2EvidenceOutput(BaseModel):
    """Stage 2: Admitted and inadmissible evidence exhibits."""

    model_config = ConfigDict(extra="forbid")

    evidence: List[EvidenceData] = Field(
        min_length=2,
        description="Exhibits list including at least one inadmissible exhibit",
    )


class Stage3WitnessesOutput(BaseModel):
    """Stage 3: Witness accounts with memory bounds and credibility ratings."""

    model_config = ConfigDict(extra="forbid")

    witnesses: List[WitnessData] = Field(
        min_length=2,
        description="List of witnesses whose knowledge is strictly bounded to saw_event_ids",
    )
