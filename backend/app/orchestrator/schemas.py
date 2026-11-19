"""Pydantic schemas for structured LLM outputs from courtroom agents."""

from __future__ import annotations

from typing import Optional

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


class TurnOutput(BaseModel):
    """Generic wrapper for a generated courtroom turn."""

    speaker_role: str
    text: str
    action: Optional[str] = None
    emotion: Optional[str] = None
    camera: Optional[str] = "wide"
