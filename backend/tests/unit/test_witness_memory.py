"""Unit tests for witness memory builder and first-person conversion."""

from app.agents.witness_memory import (
    build_witness_memory,
    convert_to_first_person,
)
from app.schemas.case import TimelineEvent, WitnessData


def test_convert_to_first_person_subject():
    desc = "Sunita Bai entered the study and discovered Anand Malhotra on the floor."
    result = convert_to_first_person(desc, "Sunita Bai")
    assert "I entered the study" in result
    assert "Sunita Bai" not in result


def test_convert_to_first_person_object():
    desc = "Anand Malhotra instructed Sunita Bai to prepare his study."
    result = convert_to_first_person(desc, "Sunita Bai")
    assert "instructed me to prepare" in result
    assert "Sunita Bai" not in result


def test_convert_to_first_person_possessive():
    desc = "Inspector Ramesh Shinde inspected Vikram Malhotra's phone at Ramesh Shinde's desk."
    result = convert_to_first_person(desc, "Inspector Ramesh Shinde")
    assert "my desk" in result
    assert "Ramesh Shinde" not in result


def test_build_witness_memory_filters_unseen_events():
    timeline = [
        TimelineEvent(
            id=0,
            time="18:30",
            location="Foyer",
            description="Sunita Bai greeted Anand Malhotra.",
            actors=["Sunita Bai", "Anand Malhotra"],
        ),
        TimelineEvent(
            id=1,
            time="19:00",
            location="Secret Room",
            description="Vikram poured poison into the decanter.",
            actors=["Vikram Malhotra"],
        ),
        TimelineEvent(
            id=2,
            time="20:00",
            location="Study",
            description="Sunita Bai heard a crash and entered.",
            actors=["Sunita Bai"],
        ),
    ]

    witness = WitnessData(
        name="Sunita Bai",
        saw_event_ids=[0, 2],  # Event 1 is strictly excluded
        reliability=0.9,
        hides=["Took cash"],
        persona={"occupation": "Housekeeper"},
    )

    memory = build_witness_memory(witness, timeline)

    assert memory.witness_name == "Sunita Bai"
    assert len(memory.memories) == 2
    assert memory.can_recall_event(0) is True
    assert memory.can_recall_event(1) is False  # Isolation
    assert memory.can_recall_event(2) is True

    # Prompt format should not contain event 1
    prompt = memory.format_for_prompt()
    assert "Secret Room" not in prompt
    assert "poison" not in prompt
    assert "Foyer" in prompt
    assert "Study" in prompt


def test_build_witness_memory_with_key_facts():
    timeline = [
        TimelineEvent(
            id=0,
            time="21:15",
            location="Corridor",
            description="Sunita Bai saw Vikram leaving the study.",
            actors=["Sunita Bai", "Vikram Malhotra"],
            key_facts=["Vikram was walking briskly", "Vikram carried a leather pouch"],
        ),
    ]

    witness = WitnessData(
        name="Sunita Bai",
        saw_event_ids=[0],
        reliability=0.95,
        hides=[],
        persona={"occupation": "Housekeeper"},
    )

    memory = build_witness_memory(witness, timeline)
    assert len(memory.memories) == 1
    assert memory.memories[0].key_facts == [
        "Vikram was walking briskly",
        "Vikram carried a leather pouch",
    ]

    prompt = memory.format_for_prompt()
    assert "Key facts: Vikram was walking briskly" in prompt
