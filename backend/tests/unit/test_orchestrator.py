"""Unit tests for the LangGraph courtroom orchestrator.

Tests setup, openings, and closings nodes, state routing, DB turn persistence,
and full trial execution with mocked LLM inferences.
"""

from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.db.models.trial import Trial, Turn
from app.db.session import async_session_maker
from app.main import app
from app.orchestrator.graph import (
    _route_after_closings,
    _route_after_openings,
    _route_after_setup,
    build_courtroom_graph,
    run_trial,
)
from app.orchestrator.nodes import closings_node, openings_node, setup_node
from app.orchestrator.schemas import (
    ClerkAnnouncementOutput,
    ClosingArgumentOutput,
    JudgeClosingOutput,
    JudgeOpeningOutput,
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


def test_graph_structure():
    """Verify courtroom graph compiles with all registered nodes."""
    graph = build_courtroom_graph()
    assert graph is not None
    # Verify graph contains our nodes
    assert "setup" in graph.nodes
    assert "openings" in graph.nodes
    assert "closings" in graph.nodes


def test_conditional_routing() -> None:
    """Verify conditional edge routing functions handle errors and normal flow."""
    normal_state: CourtroomState = {
        "trial_id": uuid.uuid4(),
        "case_id": uuid.uuid4(),
        "current_phase": TrialPhase.SETUP.value,
        "previous_phase": None,
        "turn_seq": 0,
        "active_speaker": None,
        "turns": [],
        "is_paused": False,
        "error": None,
    }
    error_state: CourtroomState = dict(normal_state)  # type: ignore[assignment]
    error_state["error"] = "Something went wrong"
    paused_state: CourtroomState = dict(normal_state)  # type: ignore[assignment]
    paused_state["is_paused"] = True

    # setup routing
    assert _route_after_setup(normal_state) == "openings"
    assert _route_after_setup(error_state) == "__end__"
    assert _route_after_setup(paused_state) == "__end__"

    # openings routing
    assert _route_after_openings(normal_state) == "closings"
    assert _route_after_openings(error_state) == "__end__"
    assert _route_after_openings(paused_state) == "__end__"

    # closings routing
    assert _route_after_closings(normal_state) == "__end__"


@pytest.mark.asyncio
async def test_setup_node_success(seeded_trial):
    """Test setup_node transitions SETUP -> OPENINGS and updates DB state."""
    trial_id, case_id = seeded_trial

    initial_state: CourtroomState = {
        "trial_id": trial_id,
        "case_id": case_id,
        "current_phase": TrialPhase.SETUP.value,
        "previous_phase": None,
        "turn_seq": 0,
        "active_speaker": None,
        "turns": [],
        "is_paused": False,
        "error": None,
    }

    async with async_session_maker() as db:
        new_state = await setup_node(initial_state, db)

        assert new_state["current_phase"] == TrialPhase.OPENINGS.value
        assert new_state["previous_phase"] == TrialPhase.SETUP.value
        assert new_state["error"] is None

        # Verify DB state updated
        trial_row = await db.get(Trial, trial_id)
        assert trial_row is not None
        assert trial_row.state == TrialPhase.OPENINGS.value


@pytest.mark.asyncio
async def test_setup_node_nonexistent_trial():
    """Test setup_node gracefully handles missing trial record."""
    fake_id = uuid.uuid4()
    state: CourtroomState = {
        "trial_id": fake_id,
        "case_id": uuid.uuid4(),
        "current_phase": TrialPhase.SETUP.value,
        "previous_phase": None,
        "turn_seq": 0,
        "active_speaker": None,
        "turns": [],
        "is_paused": False,
        "error": None,
    }

    async with async_session_maker() as db:
        new_state = await setup_node(state, db)
        assert new_state["error"] is not None
        assert "not found" in new_state["error"]
        assert new_state["current_phase"] == TrialPhase.FINISHED.value


@pytest.mark.asyncio
async def test_openings_node_turn_generation(seeded_trial):
    """Test openings_node generates judge opening and clerk announcement."""
    trial_id, case_id = seeded_trial

    state: CourtroomState = {
        "trial_id": trial_id,
        "case_id": case_id,
        "current_phase": TrialPhase.OPENINGS.value,
        "previous_phase": TrialPhase.SETUP.value,
        "turn_seq": 0,
        "active_speaker": None,
        "turns": [],
        "is_paused": False,
        "error": None,
    }

    mock_judge_output = JudgeOpeningOutput(
        text="The Court is now in session for State v. Vikram Malhotra.",
        action="gavel",
        emotion="neutral",
        camera="judge",
    )
    mock_clerk_output = ClerkAnnouncementOutput(
        text="The accused is charged under Section 103(1) of BNS.",
        action="stand",
        emotion="neutral",
        camera="wide",
    )

    async def mock_chat(tier, messages, response_model=None, **kwargs):
        if response_model is JudgeOpeningOutput:
            return mock_judge_output
        elif response_model is ClerkAnnouncementOutput:
            return mock_clerk_output
        raise ValueError(f"Unexpected response_model: {response_model}")

    with patch("app.orchestrator.nodes.chat", side_effect=mock_chat):
        async with async_session_maker() as db:
            result_state = await openings_node(state, db)

            assert result_state["turn_seq"] == 2
            assert len(result_state["turns"]) == 2
            assert result_state["current_phase"] == TrialPhase.CLOSINGS.value
            assert result_state["active_speaker"] == "clerk"

            # Check turns in database
            stmt = select(Turn).where(Turn.trial_id == trial_id).order_by(Turn.seq)
            turns_res = await db.execute(stmt)
            turns = turns_res.scalars().all()
            assert len(turns) == 2
            assert turns[0].speaker_role == "judge"
            assert turns[0].text == mock_judge_output.text
            assert turns[0].seq == 0
            assert turns[1].speaker_role == "clerk"
            assert turns[1].text == mock_clerk_output.text
            assert turns[1].seq == 1


@pytest.mark.asyncio
async def test_closings_node_turn_generation(seeded_trial):
    """Test closings_node generates prosecution, defense, and judge summaries."""
    trial_id, case_id = seeded_trial

    state: CourtroomState = {
        "trial_id": trial_id,
        "case_id": case_id,
        "current_phase": TrialPhase.CLOSINGS.value,
        "previous_phase": TrialPhase.OPENINGS.value,
        "turn_seq": 2,
        "active_speaker": "clerk",
        "turns": [],
        "is_paused": False,
        "error": None,
    }

    mock_pros = ClosingArgumentOutput(
        text="The evidence establishes guilt beyond all reasonable doubt.",
        action="stand",
        emotion="firm",
        camera="close",
    )
    mock_def = ClosingArgumentOutput(
        text="The prosecution has failed to eliminate reasonable doubt.",
        action="stand",
        emotion="firm",
        camera="close",
    )
    mock_judge = JudgeClosingOutput(
        text="The jury will now retire to deliberate upon the verdict.",
        action="sit",
        emotion="neutral",
        camera="judge",
    )

    call_count = 0

    async def mock_chat(tier, messages, response_model=None, **kwargs):
        nonlocal call_count
        call_count += 1
        if response_model is ClosingArgumentOutput:
            return mock_pros if call_count == 1 else mock_def
        elif response_model is JudgeClosingOutput:
            return mock_judge
        raise ValueError(f"Unexpected response_model: {response_model}")

    with patch("app.orchestrator.nodes.chat", side_effect=mock_chat):
        async with async_session_maker() as db:
            result_state = await closings_node(state, db)

            assert result_state["turn_seq"] == 5
            assert len(result_state["turns"]) == 3
            assert result_state["current_phase"] == TrialPhase.FINISHED.value

            # Check turns in database
            stmt = select(Turn).where(Turn.trial_id == trial_id).order_by(Turn.seq)
            turns_res = await db.execute(stmt)
            turns = turns_res.scalars().all()
            assert len(turns) == 3
            assert turns[0].speaker_role == "prosecutor"
            assert turns[1].speaker_role == "defense"
            assert turns[2].speaker_role == "judge"


@pytest.mark.asyncio
async def test_full_run_trial(seeded_trial):
    """Test full execution of run_trial through LangGraph pipeline."""
    trial_id, _ = seeded_trial

    async def mock_chat(tier, messages, response_model=None, **kwargs):
        if response_model is JudgeOpeningOutput:
            return JudgeOpeningOutput(text="Judge opening statement.")
        elif response_model is ClerkAnnouncementOutput:
            return ClerkAnnouncementOutput(text="Clerk reading charges.")
        elif response_model is ClosingArgumentOutput:
            return ClosingArgumentOutput(text="Counsel closing argument.")
        elif response_model is JudgeClosingOutput:
            return JudgeClosingOutput(text="Judge closing charge.")
        raise ValueError(f"Unexpected response_model: {response_model}")

    with patch("app.orchestrator.nodes.chat", side_effect=mock_chat):
        async with async_session_maker() as db:
            final_state = await run_trial(trial_id, db)

            assert final_state["current_phase"] == TrialPhase.FINISHED.value
            assert final_state["error"] is None
            assert len(final_state["turns"]) == 5
            assert final_state["turn_seq"] == 5

            # Verify turns stored in database
            stmt = select(Turn).where(Turn.trial_id == trial_id).order_by(Turn.seq)
            turns_res = await db.execute(stmt)
            turns = turns_res.scalars().all()
            assert len(turns) == 5
            roles = [t.speaker_role for t in turns]
            assert roles == ["judge", "clerk", "prosecutor", "defense", "judge"]
