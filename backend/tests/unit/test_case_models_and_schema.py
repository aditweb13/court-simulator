"""Unit tests for Case, Evidence, and Witness models and Pydantic schemas."""

import uuid
from decimal import Decimal

import pytest
from app.db.models.case import Case, Evidence, Witness
from app.schemas.case import (
    CaseSchema,
    TimelineEvent,
    TruthData,
    WitnessData,
    get_case_json_schema,
)
from pydantic import ValidationError


def test_case_pydantic_schema_valid() -> None:
    raw_case = {
        "slug": "state-v-sharma-2024",
        "title": "State of Maharashtra v. Rajesh Sharma",
        "jurisdiction": "IN",
        "charge": "Murder under BNS Section 103",
        "difficulty": 2,
        "source": "handwritten",
        "truth": {
            "culprit": "Rajesh Sharma",
            "motive": "Financial dispute over ancestral property inheritance",
            "summary": "Victim was poisoned at family dinner.",
            "timeline": [
                {
                    "id": 0,
                    "time": "20:00",
                    "description": "Dinner commenced at Sharma residence",
                    "location": "Dining Hall",
                    "actors": ["Rajesh Sharma", "Vikram Sharma"],
                },
                {
                    "id": 1,
                    "time": "20:45",
                    "description": "Rajesh slipped arsenic into victim's beverage",
                    "location": "Kitchen",
                    "actors": ["Rajesh Sharma"],
                },
            ],
        },
        "evidence": [
            {
                "exhibit_no": "Ex. P-1",
                "type": "forensic",
                "description": "Chemical toxicology report confirming arsenic",
                "admissible": True,
            },
            {
                "exhibit_no": "Ex. D-1",
                "type": "documentary",
                "description": "Hearsay diary entry by unexamined witness",
                "admissible": False,
                "reason_inadmissible": "Inadmissible hearsay without corroborating testimony",
            },
        ],
        "witnesses": [
            {
                "name": "Dr. Sunita Rao",
                "saw_event_ids": [1],
                "reliability": 0.95,
                "hides": [],
                "persona": {"tone": "objective", "profession": "Forensic Pathologist"},
            }
        ],
    }

    schema = CaseSchema.model_validate(raw_case)
    assert schema.slug == "state-v-sharma-2024"
    assert schema.truth.culprit == "Rajesh Sharma"
    assert len(schema.truth.timeline) == 2
    assert len(schema.evidence) == 2
    assert len(schema.witnesses) == 1
    assert schema.witnesses[0].reliability == 0.95


def test_case_pydantic_schema_extra_fields_forbidden() -> None:
    with pytest.raises(ValidationError):
        CaseSchema(
            slug="test-slug",
            title="Title",
            charge="Charge",
            truth=TruthData(
                culprit="A",
                motive="B",
                timeline=[
                    TimelineEvent(
                        id=0,
                        time="10:00",
                        description="Desc",
                        location="Loc",
                    )
                ],
            ),
            unauthorized_extra_field="Should fail due to extra='forbid'",  # type: ignore[call-arg]
        )


def test_witness_reliability_range_validation() -> None:
    with pytest.raises(ValidationError):
        WitnessData(
            name="Bad Reliability",
            saw_event_ids=[],
            reliability=1.5,  # > 1.0 must fail
        )


def test_get_case_json_schema() -> None:
    json_schema = get_case_json_schema()
    assert isinstance(json_schema, dict)
    assert json_schema.get("title") == "CaseSchema"
    assert "properties" in json_schema
    assert "slug" in json_schema["properties"]
    assert "truth" in json_schema["properties"]
    assert "evidence" in json_schema["properties"]
    assert "witnesses" in json_schema["properties"]


def test_sqlalchemy_case_models() -> None:
    case_id = uuid.uuid4()
    case = Case(
        id=case_id,
        slug="case-001",
        title="Test Case",
        jurisdiction="IN",
        charge="Cheating BNS 318",
        difficulty=1,
        source="handwritten",
        truth={"culprit": "X", "timeline": []},
    )

    evidence = Evidence(
        case_id=case_id,
        exhibit_no="Ex. P-1",
        type="documentary",
        description="Forged bank cheque",
        admissible=True,
    )

    witness = Witness(
        case_id=case_id,
        name="Inspector Roy",
        saw_event_ids=[0, 1],
        reliability=Decimal("0.85"),
        hides=["informant identity"],
        persona={"style": "formal"},
    )

    assert case.slug == "case-001"
    assert evidence.case_id == case_id
    assert witness.case_id == case_id
    assert witness.reliability == Decimal("0.85")

    # Verify table index definitions
    ev_indexes = {idx.name for idx in Evidence.__table__.indexes}
    wit_indexes = {idx.name for idx in Witness.__table__.indexes}
    assert "evidence_case_idx" in ev_indexes
    assert "witnesses_case_idx" in wit_indexes
