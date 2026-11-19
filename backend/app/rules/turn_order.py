"""Courtroom turn order and examination stage sequencing rules.

Pure functions only — no side-effects or database/LLM dependencies.
"""

from __future__ import annotations

from typing import Final, Literal, Set

ExaminationStage = Literal["direct", "cross", "redirect"]

VALID_STAGES: Final[Set[str]] = {"direct", "cross", "redirect"}


def get_opposing_party(party: str) -> str:
    """Return the adversarial opposing party role."""
    norm = party.lower().strip()
    if norm in ("prosecutor", "prosecution"):
        return "defense"
    if norm in ("defense", "defendant"):
        return "prosecutor"
    raise ValueError(f"Unrecognized courtroom party: {party}")


def get_examining_lawyer(stage: ExaminationStage, calling_party: str) -> str:
    """Determine which lawyer conducts the examination given stage and calling party.

    Under Section 142 of the Bharatiya Sakshya Adhiniyam, 2023:
    1. Examination-in-chief ('direct') is conducted by the party calling the witness.
    2. Cross-examination ('cross') is conducted by the adverse party.
    3. Re-examination ('redirect') is conducted by the party who called the witness.
    """
    calling = "prosecutor" if calling_party.lower() in ("prosecutor", "prosecution") else "defense"
    opposing = get_opposing_party(calling)

    if stage in ("direct", "redirect"):
        return calling
    elif stage == "cross":
        return opposing
    raise ValueError(f"Invalid examination stage: {stage}")


def get_next_examination_stage(current_stage: ExaminationStage) -> ExaminationStage | None:
    """Return the sequential next stage of witness examination, or None if examination complete."""
    if current_stage == "direct":
        return "cross"
    elif current_stage == "cross":
        return "redirect"
    elif current_stage == "redirect":
        return None
    return None
