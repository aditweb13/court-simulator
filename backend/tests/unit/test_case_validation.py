"""Unit tests for case validation checks and business rules."""

import pytest

from app.cases.validator import CaseValidationError, assert_case_valid, validate_case_integrity
from app.schemas.case import CaseSchema, EvidenceData, TimelineEvent, TruthData, WitnessData


def create_base_case() -> CaseSchema:
    return CaseSchema(
        slug="valid-case-2024",
        title="State v. Accused",
        jurisdiction="IN",
        charge="Murder under BNS 103",
        difficulty=1,
        source="handwritten",
        truth=TruthData(
            culprit="Accused",
            motive="Greed",
            summary="A valid summary",
            timeline=[
                TimelineEvent(
                    id=0,
                    time="2024-08-01 10:00",
                    description="Event 0 occurred",
                    location="Location A",
                    actors=["Accused", "Witness 1"],
                ),
                TimelineEvent(
                    id=1,
                    time="2024-08-01 11:00",
                    description="Event 1 occurred",
                    location="Location B",
                    actors=["Accused"],
                ),
            ],
        ),
        evidence=[
            EvidenceData(
                exhibit_no="Ex. P-1",
                type="physical",
                description="Seized weapon",
                admissible=True,
            ),
            EvidenceData(
                exhibit_no="Ex. P-2",
                type="documentary",
                description="Uncertified electronic printout",
                admissible=False,
                reason_inadmissible="Lacks Section 63 BSA certificate",
            ),
        ],
        witnesses=[
            WitnessData(
                name="Witness 1",
                saw_event_ids=[0],
                reliability=0.9,
                hides=[],
                persona={"role": "Bystander"},
            )
        ],
    )


def test_valid_case_passes_validation():
    case = create_base_case()
    errors = validate_case_integrity(case)
    assert errors == []
    # Should not raise
    assert_case_valid(case)


def test_timeline_cannot_have_duplicate_ids():
    case = create_base_case()
    case.truth.timeline.append(
        TimelineEvent(
            id=0,  # Duplicate of 0
            time="2024-08-01 12:00",
            description="Duplicate event",
            location="Location C",
            actors=[],
        )
    )
    errors = validate_case_integrity(case)
    assert any("duplicate event IDs" in e for e in errors)
    with pytest.raises(CaseValidationError):
        assert_case_valid(case)


def test_offence_date_before_bns_effective_fails():
    case = create_base_case()
    case.truth.timeline[0].time = "2024-05-15 10:00"  # Before 2024-07-01
    errors = validate_case_integrity(case)
    assert any("before BNS effective date 2024-07-01" in e for e in errors)
    with pytest.raises(CaseValidationError):
        assert_case_valid(case)


def test_missing_inadmissible_evidence_fails():
    case = create_base_case()
    # Mark all evidence as admissible
    for ev in case.evidence:
        ev.admissible = True
        ev.reason_inadmissible = None
    errors = validate_case_integrity(case)
    assert any("at least one inadmissible evidence" in e for e in errors)
    with pytest.raises(CaseValidationError):
        assert_case_valid(case)


def test_inadmissible_evidence_without_reason_fails():
    case = create_base_case()
    case.evidence[1].reason_inadmissible = "   "  # Blank reason
    errors = validate_case_integrity(case)
    assert any("must specify reason_inadmissible" in e for e in errors)
    with pytest.raises(CaseValidationError):
        assert_case_valid(case)


def test_duplicate_exhibit_numbers_fails():
    case = create_base_case()
    case.evidence.append(
        EvidenceData(
            exhibit_no="Ex. P-1",  # Duplicate of Ex. P-1
            type="forensic",
            description="Another report",
            admissible=True,
        )
    )
    errors = validate_case_integrity(case)
    assert any("Duplicate exhibit number" in e for e in errors)
    with pytest.raises(CaseValidationError):
        assert_case_valid(case)


def test_witness_saw_event_id_outside_timeline_fails():
    case = create_base_case()
    case.witnesses[0].saw_event_ids = [0, 999]  # 999 does not exist
    errors = validate_case_integrity(case)
    assert any("non-existent timeline event IDs" in e for e in errors)
    with pytest.raises(CaseValidationError):
        assert_case_valid(case)


def test_duplicate_witness_names_fails():
    case = create_base_case()
    case.witnesses.append(
        WitnessData(
            name="Witness 1",  # Duplicate name
            saw_event_ids=[0],
            reliability=0.8,
        )
    )
    errors = validate_case_integrity(case)
    assert any("Duplicate witness name" in e for e in errors)
    with pytest.raises(CaseValidationError):
        assert_case_valid(case)
