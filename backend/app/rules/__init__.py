"""Rules engine package: pure functions governing courtroom order, objections, and admissibility."""

from app.rules.admissibility import evaluate_evidence_admissibility
from app.rules.objections import (
    DEFAULT_OBJECTION_QUOTA_PER_EXAM,
    GROUND_STATUTORY_CITATIONS,
    VALID_OBJECTION_GROUNDS,
    check_objection_quota,
    get_statutory_basis,
    is_leading_question_permitted,
    is_valid_objection_ground,
)
from app.rules.turn_order import (
    ExaminationStage,
    get_examining_lawyer,
    get_next_examination_stage,
    get_opposing_party,
)

__all__ = [
    "evaluate_evidence_admissibility",
    "check_objection_quota",
    "get_statutory_basis",
    "is_leading_question_permitted",
    "is_valid_objection_ground",
    "DEFAULT_OBJECTION_QUOTA_PER_EXAM",
    "GROUND_STATUTORY_CITATIONS",
    "VALID_OBJECTION_GROUNDS",
    "ExaminationStage",
    "get_examining_lawyer",
    "get_next_examination_stage",
    "get_opposing_party",
]
