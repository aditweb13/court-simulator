"""Pydantic schemas for WebSocket events (Server-to-Client and Client-to-Server)."""

from __future__ import annotations

from typing import Annotated, Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field

# ============================================================================
# Client to Server Events
# ============================================================================


class AuthEvent(BaseModel):
    """Initial client authentication handshake message."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["auth"] = "auth"
    token: str = Field(description="JWT bearer token obtained from /auth/login or /auth/guest")


class AckEvent(BaseModel):
    """Client acknowledgement that a sequence number turn has finished playing."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["ack"] = "ack"
    seq: int = Field(ge=0, description="Sequence number of the line played")


class HumanActionEvent(BaseModel):
    """Action or statement initiated by a human lawyer or judge player."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["human_action"] = "human_action"
    action: str = Field(description="Action name, e.g. 'examine', 'argue', 'submit'")
    text: Optional[str] = Field(default=None, description="Spoken line or argument text")
    target: Optional[str] = Field(default=None, description="Target character role or exhibit")


class ObjectEvent(BaseModel):
    """Objection raised by a human lawyer player."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["object"] = "object"
    objection_type: str = Field(
        description="Legal objection ground: 'hearsay', 'leading', 'relevance', 'badgering', etc."
    )
    reason: Optional[str] = Field(default=None, description="Detailed basis for the objection")


ClientEvent = Annotated[
    Union[AuthEvent, AckEvent, HumanActionEvent, ObjectEvent],
    Field(discriminator="type"),
]


# ============================================================================
# Server to Client Events
# ============================================================================


class LineEvent(BaseModel):
    """Spoken courtroom dialogue turn played by a character in 3D scene."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["line"] = "line"
    seq: int = Field(ge=0, description="Sequential dialogue turn index")
    speaker: str = Field(
        description="Speaking role: judge, clerk, prosecutor, defense, witness, defendant, juror"
    )
    text: str = Field(description="Spoken dialogue text")
    action: Optional[str] = Field(
        default=None, description="Physical animation state: sit, stand, talk, point, gavel"
    )
    emotion: Optional[str] = Field(
        default=None, description="Facial expression / emotion: neutral, firm, angry, nervous"
    )
    camera: Optional[str] = Field(
        default="wide", description="Directorial camera shot: wide, close, jury, judge, witness"
    )
    audio_url: Optional[str] = Field(
        default=None, description="Audio TTS streaming URL if enabled"
    )


class RulingEvent(BaseModel):
    """Judicial ruling on an objection (sustained or overruled)."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["ruling"] = "ruling"
    seq: int = Field(ge=0, description="Sequential index of the ruling turn")
    objection_type: str = Field(description="Ground of objection that was ruled upon")
    ruling: Literal["sustained", "overruled"] = Field(description="Judicial decision")
    struck: bool = Field(
        default=False, description="Whether the contested testimony was struck from the record"
    )
    reason: Optional[str] = Field(default=None, description="Judge's stated oral justification")


class StateEvent(BaseModel):
    """Trial state machine progression event."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["state"] = "state"
    state: str = Field(
        description="New trial state: SETUP, OPENINGS, EXAMINATION, CLOSINGS, DELIBERATION, VERDICT"
    )
    previous_state: Optional[str] = Field(default=None, description="Prior trial state")


class PromptEvent(BaseModel):
    """Prompt sent to a human participant when input is required."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["prompt"] = "prompt"
    role: str = Field(description="Human role prompt is directed to")
    options: List[str] = Field(
        default_factory=list, description="Available actions, e.g. ['examine', 'object', 'pass']"
    )


class VerdictEvent(BaseModel):
    """Final trial verdict outcome, aggregated scores, and ground truth evaluation."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["verdict"] = "verdict"
    outcome: Literal["guilty", "not_guilty", "hung"] = Field(description="Final verdict outcome")
    score: float = Field(ge=0.0, le=1.0, description="Aggregated guilt score (0.5*J + 0.5*P)")
    threshold: float = Field(default=0.75, description="Applied guilt threshold")
    disagreement: float = Field(
        ge=0.0, le=1.0, description="Disagreement metric abs(J - P) between jury and bench"
    )
    matches_truth: Optional[bool] = Field(
        default=None, description="Whether outcome matches hidden ground truth"
    )
    reasoning: Optional[str] = Field(default=None, description="Summary verdict commentary")


class ErrorEvent(BaseModel):
    """WebSocket error event sent to client."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["error"] = "error"
    code: str = Field(description="Standard error code")
    message: str = Field(description="Human readable description")
    details: Dict[str, Any] = Field(default_factory=dict)


ServerEvent = Union[LineEvent, RulingEvent, StateEvent, PromptEvent, VerdictEvent, ErrorEvent]
