"""Courtroom orchestrator state definitions for LangGraph."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from typing_extensions import TypedDict


class TrialPhase(str, Enum):
    SETUP = "SETUP"
    OPENINGS = "OPENINGS"
    EXAMINATION = "EXAMINATION"  # Expanded in Phase 6
    CLOSINGS = "CLOSINGS"
    DELIBERATION = "DELIBERATION"  # Expanded in Phase 7
    VERDICT = "VERDICT"  # Expanded in Phase 7
    FINISHED = "FINISHED"


class CourtroomState(TypedDict):
    """Execution state carried across LangGraph courtroom nodes."""

    trial_id: UUID
    case_id: UUID
    current_phase: str
    previous_phase: Optional[str]
    turn_seq: int
    active_speaker: Optional[str]
    turns: List[Dict[str, Any]]
    is_paused: bool
    error: Optional[str]
