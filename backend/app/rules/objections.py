"""Courtroom objection validation rules and statutory references under Indian law (BSA 2023).

Pure functions only — no side-effects or database/LLM dependencies.
"""

from __future__ import annotations

from typing import Dict, Final, Optional, Set

# Recognized legal objection grounds under the Bharatiya Sakshya Adhiniyam, 2023
VALID_OBJECTION_GROUNDS: Final[Set[str]] = {
    "hearsay",
    "leading",
    "relevance",
    "badgering",
    "speculation",
    "character",
}

# Statutory mappings to BSA 2023 provisions
GROUND_STATUTORY_CITATIONS: Final[Dict[str, str]] = {
    "hearsay": (
        "Section 55 & 57 of the Bharatiya Sakshya Adhiniyam, 2023 (Oral evidence must be direct)"
    ),
    "leading": (
        "Section 146 of the Bharatiya Sakshya Adhiniyam, 2023 "
        "(Leading questions prohibited in chief and re-examination)"
    ),
    "relevance": (
        "Sections 3 to 14 of the Bharatiya Sakshya Adhiniyam, 2023 (Relevancy of facts)"
    ),
    "badgering": (
        "Section 154 of the Bharatiya Sakshya Adhiniyam, 2023 "
        "(Questions intended to insult or annoy)"
    ),
    "speculation": (
        "Section 39 of the Bharatiya Sakshya Adhiniyam, 2023 "
        "(Opinions of third persons generally inadmissible)"
    ),
    "character": (
        "Sections 50 to 52 of the Bharatiya Sakshya Adhiniyam, 2023 "
        "(Previous bad character irrelevant in criminal proceedings)"
    ),
}

DEFAULT_OBJECTION_QUOTA_PER_EXAM: Final[int] = 3


def is_valid_objection_ground(ground: str) -> bool:
    """Check whether the ground is a recognized Indian criminal law objection."""
    return ground.lower().strip() in VALID_OBJECTION_GROUNDS


def get_statutory_basis(ground: str) -> Optional[str]:
    """Retrieve the BSA 2023 section citation for a given objection ground."""
    return GROUND_STATUTORY_CITATIONS.get(ground.lower().strip())


def check_objection_quota(used: int, limit: int = DEFAULT_OBJECTION_QUOTA_PER_EXAM) -> bool:
    """Return True if the lawyer has remaining objections within their quota."""
    return used < limit


def is_leading_question_permitted(examination_type: str) -> bool:
    """Check if leading questions are legally permitted for this examination stage.

    Under BSA Section 146(2), leading questions MUST NOT be asked in examination-in-chief
    or re-examination without court leave, but ARE freely permitted in cross-examination
    under Section 146(3).
    """
    exam_stage = examination_type.lower().strip()
    return exam_stage == "cross"
