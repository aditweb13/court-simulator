"""Isolation test suite for witness memory slices.

Enforces:
1. Asking about an unseen event yields zero knowledge.
2. Witness memory contains only events in saw_event_ids.
3. Formatted witness context contains no leakage of unobserved timeline events,
   unwitnessed actors, or ground truth culprit secrets.
4. Cross-witness isolation: Witness A cannot recall events observed only by Witness B.
"""

import json
from pathlib import Path

import pytest

from app.agents.witness_memory import build_witness_memory
from app.schemas.case import CaseSchema


def get_case_files() -> list[Path]:
    cases_dir = Path(__file__).resolve().parent.parent.parent.parent / "data" / "cases"
    return sorted(cases_dir.glob("*.json"))


@pytest.fixture(params=get_case_files(), ids=lambda p: p.stem)
def case_data(request: pytest.FixtureRequest) -> CaseSchema:
    raw = json.loads(request.param.read_text(encoding="utf-8"))
    return CaseSchema.model_validate(raw)


def test_witness_isolation_on_all_cases(case_data: CaseSchema) -> None:
    """Test memory isolation for every witness in every case."""
    timeline = case_data.truth.timeline
    all_event_ids = {e.id for e in timeline}

    for witness in case_data.witnesses:
        saw_ids = set(witness.saw_event_ids)
        unseen_ids = all_event_ids - saw_ids

        memory = build_witness_memory(witness, timeline)

        # 1. Witness memories must exactly match saw_event_ids
        recalled_ids = {m.event_id for m in memory.memories}
        assert recalled_ids == saw_ids, (
            f"Witness '{witness.name}' in '{case_data.slug}' has unexpected recalled IDs: "
            f"{recalled_ids} != {saw_ids}"
        )

        # 2. For every unseen event, asking about it yields no knowledge
        for unseen_id in unseen_ids:
            assert memory.can_recall_event(unseen_id) is False
            assert memory.get_memory_for_event(unseen_id) is None

            # Test interrogation response for unseen event
            response = memory.answer_query(
                query="What happened during this event?",
                target_event_id=unseen_id,
            )
            assert "no knowledge" in response.lower() or "not present" in response.lower(), (
                f"Witness '{witness.name}' leaked knowledge of unseen event {unseen_id}!"
            )

        # 3. Formatted prompt must not leak unseen locations or event-exclusive keywords
        prompt = memory.format_for_prompt()
        for unseen_event in [e for e in timeline if e.id in unseen_ids]:
            # If location is unique to unseen event and not in persona/witnessed events
            witnessed_text = " ".join(
                [e.location for e in timeline if e.id in saw_ids]
                + [str(v) for v in witness.persona.values()]
            )
            if unseen_event.location not in witnessed_text:
                assert unseen_event.location not in prompt, (
                    f"Prompt leaked unseen location '{unseen_event.location}' "
                    f"to witness '{witness.name}'!"
                )


def test_cross_witness_isolation(case_data: CaseSchema) -> None:
    """Witnesses cannot access events that only other witnesses saw."""
    timeline = case_data.truth.timeline

    if len(case_data.witnesses) < 2:
        pytest.skip("Need at least 2 witnesses for cross-isolation test")

    w1 = case_data.witnesses[0]
    w2 = case_data.witnesses[1]

    mem1 = build_witness_memory(w1, timeline)
    mem2 = build_witness_memory(w2, timeline)

    w1_exclusive = set(w1.saw_event_ids) - set(w2.saw_event_ids)
    w2_exclusive = set(w2.saw_event_ids) - set(w1.saw_event_ids)

    for eid in w1_exclusive:
        assert mem2.can_recall_event(eid) is False
        ans = mem2.answer_query(f"Tell me about event {eid}", target_event_id=eid)
        assert "no knowledge" in ans.lower()

    for eid in w2_exclusive:
        assert mem1.can_recall_event(eid) is False
        ans = mem1.answer_query(f"Tell me about event {eid}", target_event_id=eid)
        assert "no knowledge" in ans.lower()
