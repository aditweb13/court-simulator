"""Pydantic schemas for structured LLM outputs from courtroom agents."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class JudgeOpeningOutput(BaseModel):
    """Structured output from the judge's opening statement LLM call."""

    text: str = Field(description="The judge's spoken opening statement to the court")
    action: str = Field(
        default="gavel",
        description="Physical animation: sit, stand, talk, point, gavel",
    )
    emotion: str = Field(default="neutral", description="Facial expression / tone")
    camera: str = Field(default="judge", description="Camera shot: wide, close, judge")


class ClerkAnnouncementOutput(BaseModel):
    """Structured output from the clerk reading the charges."""

    text: str = Field(description="The clerk's formal reading of the charges")
    action: str = Field(default="stand", description="Physical animation state")
    emotion: str = Field(default="neutral", description="Expression")
    camera: str = Field(default="wide", description="Camera shot")


class ClosingArgumentOutput(BaseModel):
    """Structured output from a lawyer's closing argument."""

    text: str = Field(description="The closing argument spoken text")
    action: str = Field(default="stand", description="Physical animation state")
    emotion: str = Field(default="firm", description="Expression / tone")
    camera: str = Field(default="close", description="Camera shot")


class JudgeClosingOutput(BaseModel):
    """Structured output from the judge's pre-deliberation summary."""

    text: str = Field(description="Judge's summary and instructions to jurors")
    action: str = Field(default="sit", description="Physical animation state")
    emotion: str = Field(default="neutral", description="Expression")
    camera: str = Field(default="judge", description="Camera shot")


class ExaminationQuestionOutput(BaseModel):
    """Structured output from a lawyer asking a witness a question."""

    text: str = Field(description="The spoken question directed to the witness in the stand")
    action: str = Field(default="stand", description="Physical animation: stand, point, talk")
    emotion: str = Field(
        default="probing",
        description="Facial expression: firm, probing, skeptical, calm",
    )
    camera: str = Field(
        default="prosecution",
        description="Camera angle: prosecution, defense, witness",
    )
    private_note: Optional[str] = Field(
        default=None, description="Tactical reason or strategy note behind this question"
    )


class WitnessAnswerOutput(BaseModel):
    """Structured output from a witness answering a question from their recollection."""

    text: str = Field(description="The witness's spoken answer from their personal knowledge")
    action: str = Field(default="talk", description="Physical animation: sit, talk")
    emotion: str = Field(default="neutral", description="Emotion: neutral, anxious, firm, hesitant")
    camera: str = Field(default="witness", description="Camera angle: witness")


class ObjectionOutput(BaseModel):
    """Structured output when an opposing lawyer considers raising an objection."""

    raise_objection: bool = Field(
        description="Whether to formally raise an objection to the preceding question or answer"
    )
    objection_type: Optional[str] = Field(
        default=None,
        description="Ground: hearsay, leading, relevance, badgering, speculation, character",
    )
    legal_basis: Optional[str] = Field(
        default=None,
        description="Statutory reference under BSA 2023 (e.g. BSA Section 55)",
    )
    argument: Optional[str] = Field(
        default=None,
        description="Oral statement to the court, e.g. 'Objection, this calls for hearsay.'",
    )
    action: str = Field(default="stand", description="Physical animation state: stand, point")
    camera: str = Field(default="defense", description="Camera angle: prosecution, defense")


class RulingOutput(BaseModel):
    """Structured output from the judge ruling on an objection."""

    ruling: str = Field(description="Judicial decision: sustained or overruled")
    struck: bool = Field(
        default=False,
        description="Whether testimony should be struck from the court record",
    )
    reason: str = Field(description="Judge's stated oral legal justification")
    text: str = Field(
        description="Spoken statement to the court, e.g. 'Sustained. Counsel will rephrase.'"
    )
    action: str = Field(default="gavel", description="Physical animation state: gavel, talk, sit")
    camera: str = Field(default="judge", description="Camera angle: judge")


class TurnOutput(BaseModel):
    """Generic wrapper for a generated courtroom turn."""

    speaker_role: str
    text: str
    action: Optional[str] = None
    emotion: Optional[str] = None
    camera: Optional[str] = "wide"


class JurorVoteOutput(BaseModel):
    """Structured output from a juror casting their private pre- or post-deliberation vote."""

    guilty: bool = Field(
        description="Juror's ultimate binary verdict decision: guilty or not guilty"
    )
    guilt_probability: float = Field(
        ge=0.0,
        le=1.0,
        description="Assessed probability (0.0 to 1.0) that accused committed the charged offense",
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Self-rated certainty in this decision (0.0 to 1.0)",
    )
    reasoning: str = Field(
        description="Step-by-step reasoning assessing witness credibility and burden of proof",
    )
    cited_turn_seqs: List[int] = Field(
        default_factory=list,
        description="List of admitted turn seq numbers supporting this evaluation",
    )


class JurorDeliberationOutput(BaseModel):
    """Structured output when a juror contributes a speaking point during group deliberation."""

    statement: str = Field(
        description="Spoken statement under 60 words arguing evidence or perspective",
    )
    devil_advocate: bool = Field(
        default=False,
        description="Whether this statement actively challenges consensus as devil's advocate",
    )
    current_leaning: str = Field(
        default="undecided",
        description="Current juror leaning: guilty, not_guilty, or undecided",
    )
    key_point: Optional[str] = Field(
        default=None,
        description="Core evidentiary pivot, e.g. 'weapon recovery gap', 'alibi consistency'",
    )


class JudgeVerdictOutput(BaseModel):
    """Structured output from a verdict judge evaluating the trial from judicial philosophy."""

    guilty: bool = Field(
        description="Judicial finding: guilty beyond reasonable doubt or not guilty",
    )
    guilt_probability: float = Field(
        ge=0.0,
        le=1.0,
        description="Judicial probability of guilt (0.0 to 1.0)",
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Degree of judicial certainty (0.0 to 1.0)",
    )
    reasoning: str = Field(
        description="Formal judicial analysis applying statutory standards and legal doctrines",
    )
    cited_sections: List[str] = Field(
        default_factory=list,
        description="Statutory sections cited, e.g. ['BNS 103(1)', 'BSA 63']",
    )
