"""Unit tests for HeadlessAutoAckClient."""

from __future__ import annotations

import uuid

import pytest
from app.orchestrator.headless import HeadlessAutoAckClient
from app.orchestrator.nodes import _send_and_wait_ack
from app.ws.connection import ConnectionManager
from app.ws.schemas import LineEvent, StateEvent


@pytest.mark.asyncio
async def test_headless_client_auto_ack_flow():
    """Headless client automatically acknowledges LineEvents and captures all events."""
    custom_manager = ConnectionManager()
    trial_id = uuid.uuid4()

    async with HeadlessAutoAckClient(trial_id=trial_id, ws_manager=custom_manager) as client:
        assert custom_manager.is_connected(trial_id)

        # Dispatch state event
        state_evt = StateEvent(state="OPENINGS", previous_state="SETUP")
        await custom_manager.send_event(trial_id, state_evt)

        # Dispatch line event directly
        line_evt = LineEvent(
            seq=1,
            speaker="judge",
            text="Court is now in session.",
            camera="judge",
        )
        await custom_manager.send_event(trial_id, line_evt)

        # Verify auto-ack marked seq 1 as acknowledged
        assert 1 in custom_manager._acknowledged_seqs.get(trial_id, set())

        # Verify event history captured
        assert len(client.events) == 2
        line_events = client.get_events_by_type("line")
        assert len(line_events) == 1
        assert line_events[0]["seq"] == 1
        assert line_events[0]["text"] == "Court is now in session."

    # Disconnected after exit
    assert not custom_manager.is_connected(trial_id)


@pytest.mark.asyncio
async def test_headless_client_send_and_wait_ack():
    """_send_and_wait_ack succeeds immediately with HeadlessAutoAckClient."""
    trial_id = uuid.uuid4()

    async with HeadlessAutoAckClient(trial_id=trial_id) as client:
        # Send line and wait for ack with tight timeout
        ack_success = await _send_and_wait_ack(
            trial_id=trial_id,
            seq=10,
            speaker="prosecutor",
            text="The state calls its first witness.",
            timeout=1.0,
        )
        assert ack_success is True

        lines = client.get_events_by_type("line")
        assert len(lines) == 1
        assert lines[0]["seq"] == 10
