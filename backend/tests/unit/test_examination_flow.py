"""Unit tests for the examination node, objection flow, rulings, and struck testimony.

Verifies:
1. Direct -> Cross -> Redirect examination progression.
2. Defense and prosecution objection raising and quota checks.
3. Judge rulings (sustained vs overruled) based on BSA rules.
4. Marking turns as struck on sustained objections.
5. Turn embeddings persisted for generated turns.
"""

from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.db.models.trial import Turn, TurnEmbedding
from app.db.session import async_session_maker
from app.main import app
from app.orchestrator.nodes import examination_node
from app.orchestrator.schemas import (
    ExaminationQuestionOutput,
    ObjectionOutput,
    WitnessAnswerOutput,
)
from app.orchestrator.state import CourtroomState, TrialPhase


@pytest.fixture
async def seeded_trial():
    """Create a trial via the API so all agents and case links are seeded."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post(
            "/api/v1/trials",
            json={"case_id": "state-v-malhotra-2024", "mode": "watch"},
        )
        assert res.status_code == 201
        data = res.json()["data"]
        return uuid.UUID(data["id"]), uuid.UUID(data["case_id"])


@pytest.mark.asyncio
async def test_examination_with_sustained_objection_marks_turn_struck(seeded_trial):
    """Test that a sustained hearsay objection flags the preceding question as struck."""
    trial_id, case_id = seeded_trial

    state: CourtroomState = {
        "trial_id": trial_id,
        "case_id": case_id,
        "current_phase": TrialPhase.EXAMINATION.value,
        "previous_phase": TrialPhase.OPENINGS.value,
        "turn_seq": 2,
        "active_speaker": "clerk",
        "turns": [],
        "is_paused": False,
        "error": None,
    }

    call_counts = {"examination_q": 0, "objection": 0, "witness_ans": 0}

    async def mock_chat(tier, messages, response_model=None, **kwargs):
        if response_model is ExaminationQuestionOutput:
            call_counts["examination_q"] += 1
            return ExaminationQuestionOutput(
                text=f"Question {call_counts['examination_q']}: What did the bystander tell you?",
                action="point",
                emotion="serious",
            )
        elif response_model is ObjectionOutput:
            call_counts["objection"] += 1
            if call_counts["objection"] == 1:
                # First objection (defense on direct): sustain hearsay
                return ObjectionOutput(
                    raise_objection=True,
                    objection_type="hearsay",
                    legal_basis="BSA Section 55",
                    argument="Objection, Your Honour, this question solicits hearsay.",
                )
            # Other objections: do not object
            return ObjectionOutput(raise_objection=False)
        elif response_model is WitnessAnswerOutput:
            call_counts["witness_ans"] += 1
            return WitnessAnswerOutput(
                text=f"Answer {call_counts['witness_ans']}: I only know what I saw.",
                action="talk",
                emotion="neutral",
            )
        raise ValueError(f"Unexpected response_model: {response_model}")

    with patch("app.orchestrator.nodes.chat", side_effect=mock_chat):
        async with async_session_maker() as db:
            result_state = await examination_node(state, db)

            assert result_state["current_phase"] == TrialPhase.CLOSINGS.value
            assert result_state["error"] is None
            assert result_state["is_paused"] is False

            # Inspect all turns in DB
            stmt = select(Turn).where(Turn.trial_id == trial_id).order_by(Turn.seq)
            turns_res = await db.execute(stmt)
            turns = turns_res.scalars().all()

            # Sequence:
            # 2: Direct Q (prosecutor) -> STRUCK
            # 3: Objection (defense)
            # 4: Ruling (judge, sustained)
            # 5: Direct Answer (witness)
            # 6: Cross Q (defense)
            # 7: Cross Answer (witness)
            # 8: Redirect Q (prosecutor)
            # 9: Redirect Answer (witness)
            assert len(turns) == 8

            direct_q_turn = turns[0]
            assert direct_q_turn.speaker_role == "prosecutor"
            assert direct_q_turn.struck is True

            objection_turn = turns[1]
            assert objection_turn.speaker_role == "defense"
            assert "hearsay" in (objection_turn.objection or {}).get("type", "")

            ruling_turn = turns[2]
            assert ruling_turn.speaker_role == "judge"
            assert (ruling_turn.objection or {}).get("ruling") == "sustained"
            assert (ruling_turn.objection or {}).get("struck") is True

            # Check that turn embeddings were persisted for turns
            emb_stmt = select(TurnEmbedding).where(TurnEmbedding.trial_id == trial_id)
            emb_res = await db.execute(emb_stmt)
            embs = emb_res.scalars().all()
            assert len(embs) == 8


@pytest.mark.asyncio
async def test_examination_leading_question_rules_bsa(seeded_trial):
    """Test BSA Section 146 leading question rules:

    - Direct: leading question objection is SUSTAINED.
    - Cross: leading question objection is OVERRULED (permitted under BSA Section 146(3)).
    """
    trial_id, case_id = seeded_trial

    state: CourtroomState = {
        "trial_id": trial_id,
        "case_id": case_id,
        "current_phase": TrialPhase.EXAMINATION.value,
        "previous_phase": TrialPhase.OPENINGS.value,
        "turn_seq": 2,
        "active_speaker": "clerk",
        "turns": [],
        "is_paused": False,
        "error": None,
    }

    call_counts = {"examination_q": 0, "objection": 0, "witness_ans": 0}

    async def mock_chat(tier, messages, response_model=None, **kwargs):
        if response_model is ExaminationQuestionOutput:
            call_counts["examination_q"] += 1
            return ExaminationQuestionOutput(
                text=f"Question {call_counts['examination_q']}: You were there, weren't you?",
                action="point",
                emotion="serious",
            )
        elif response_model is ObjectionOutput:
            call_counts["objection"] += 1
            if call_counts["objection"] == 2:
                # Second objection is prosecution objecting to defense on cross for leading
                return ObjectionOutput(
                    raise_objection=True,
                    objection_type="leading",
                    legal_basis="BSA Section 146",
                    argument="Objection, leading question.",
                )
            return ObjectionOutput(raise_objection=False)
        elif response_model is WitnessAnswerOutput:
            call_counts["witness_ans"] += 1
            return WitnessAnswerOutput(
                text=f"Answer {call_counts['witness_ans']}: Yes.",
                action="talk",
                emotion="neutral",
            )
        raise ValueError(f"Unexpected response_model: {response_model}")

    with patch("app.orchestrator.nodes.chat", side_effect=mock_chat):
        async with async_session_maker() as db:
            result_state = await examination_node(state, db)
            assert result_state["current_phase"] == TrialPhase.CLOSINGS.value

            stmt = select(Turn).where(Turn.trial_id == trial_id).order_by(Turn.seq)
            turns_res = await db.execute(stmt)
            turns = turns_res.scalars().all()

            # Find ruling turn from judge on cross
            ruling_turns = [t for t in turns if t.speaker_role == "judge"]
            assert len(ruling_turns) == 1
            judge_ruling = ruling_turns[0]
            # Leading questions on cross MUST be overruled under BSA 146(3)
            assert (judge_ruling.objection or {}).get("ruling") == "overruled"
            assert (judge_ruling.objection or {}).get("struck") is False
