"""Unit and integration tests for send-then-wait-for-ack loop and client timeout pause."""

from __future__ import annotations

import asyncio
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from app.db.models.trial import Trial
from app.db.session import async_session_maker
from app.main import app
from app.orchestrator.graph import run_trial
from app.orchestrator.nodes import openings_node
from app.orchestrator.schemas import (
    ClerkAnnouncementOutput,
    JudgeOpeningOutput,
)
from app.orchestrator.state import CourtroomState, TrialPhase
from app.ws.connection import manager as ws_manager
from httpx import ASGITransport, AsyncClient
from starlette.websockets import WebSocket


@pytest.fixture
async def seeded_trial():
    """Create a trial via API so all agents and case links are seeded."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post(
            "/api/v1/trials",
            json={"case_id": "state-v-malhotra-2024", "mode": "watch"},
        )
        assert res.status_code == 201
        data = res.json()["data"]
        return uuid.UUID(data["id"]), uuid.UUID(data["case_id"])


@pytest.mark.asyncio
async def test_ack_loop_success_with_active_client(seeded_trial):
    """When a client acknowledges each turn, orchestrator progresses through turns."""
    trial_id, case_id = seeded_trial

    mock_ws = AsyncMock(spec=WebSocket)
    mock_ws.send_text = AsyncMock()
    await ws_manager.connect(trial_id, mock_ws)

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

    # Automatically acknowledge incoming turns in the background
    async def auto_ack():
        # Acknowledge seq 0 (judge) and seq 1 (clerk)
        for seq in [0, 1]:
            await asyncio.sleep(0.05)
            ws_manager.handle_ack(trial_id, seq)

    ack_task = asyncio.create_task(auto_ack())

    mock_judge = JudgeOpeningOutput(text="Court is now in session.")
    mock_clerk = ClerkAnnouncementOutput(text="Reading charges under BNS 103.")

    async def mock_chat(tier, messages, response_model=None, **kwargs):
        if response_model is JudgeOpeningOutput:
            return mock_judge
        elif response_model is ClerkAnnouncementOutput:
            return mock_clerk
        raise ValueError(f"Unexpected: {response_model}")

    try:
        with patch("app.orchestrator.nodes.chat", side_effect=mock_chat):
            async with async_session_maker() as db:
                new_state = await openings_node(state, db)

                assert new_state["is_paused"] is False
                assert new_state["turn_seq"] == 2
                assert len(new_state["turns"]) == 2
                assert new_state["current_phase"] == TrialPhase.EXAMINATION.value
        await ack_task
    finally:
        ws_manager.disconnect(trial_id, mock_ws)


@pytest.mark.asyncio
async def test_ack_timeout_pauses_trial(seeded_trial):
    """When a client fails to acknowledge within timeout, trial is paused in DB and state."""
    trial_id, case_id = seeded_trial

    mock_ws = AsyncMock(spec=WebSocket)
    mock_ws.send_text = AsyncMock()
    await ws_manager.connect(trial_id, mock_ws)

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

    mock_judge = JudgeOpeningOutput(text="Court is in session.")

    async def mock_chat(tier, messages, response_model=None, **kwargs):
        return mock_judge

    try:
        # Patch settings.ack_timeout_seconds to 0.1s for fast test
        with patch("app.orchestrator.nodes.settings.ack_timeout_seconds", 0.1):
            with patch("app.orchestrator.nodes.chat", side_effect=mock_chat):
                async with async_session_maker() as db:
                    new_state = await openings_node(state, db)

                    # State must be paused
                    assert new_state["is_paused"] is True
                    # Only the first turn was generated before stalling
                    assert new_state["turn_seq"] == 1
                    assert len(new_state["turns"]) == 1

                    # Verify database trial state is PAUSED
                    trial_row = await db.get(Trial, trial_id)
                    assert trial_row is not None
                    assert trial_row.state == "PAUSED"
    finally:
        ws_manager.disconnect(trial_id, mock_ws)


@pytest.mark.asyncio
async def test_run_trial_halts_on_ack_timeout(seeded_trial):
    """Full run_trial execution halts cleanly when paused due to dead client."""
    trial_id, _ = seeded_trial

    mock_ws = AsyncMock(spec=WebSocket)
    mock_ws.send_text = AsyncMock()
    await ws_manager.connect(trial_id, mock_ws)

    mock_judge = JudgeOpeningOutput(text="Opening statement.")

    async def mock_chat(tier, messages, response_model=None, **kwargs):
        return mock_judge

    try:
        with patch("app.orchestrator.nodes.settings.ack_timeout_seconds", 0.1):
            with patch("app.orchestrator.nodes.chat", side_effect=mock_chat):
                async with async_session_maker() as db:
                    final_state = await run_trial(trial_id, db)

                    assert final_state["is_paused"] is True
                    # Halts at openings, does not proceed to closings
                    assert len(final_state["turns"]) == 1
                    assert final_state["turn_seq"] == 1
    finally:
        ws_manager.disconnect(trial_id, mock_ws)
