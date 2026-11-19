"""Case generation module."""

from app.casegen.generator import compute_generation_hash, generate_case
from app.casegen.schemas import (
    CaseGenerateRequest,
    Stage1TruthOutput,
    Stage2EvidenceOutput,
    Stage3WitnessesOutput,
)

__all__ = [
    "CaseGenerateRequest",
    "Stage1TruthOutput",
    "Stage2EvidenceOutput",
    "Stage3WitnessesOutput",
    "compute_generation_hash",
    "generate_case",
]
