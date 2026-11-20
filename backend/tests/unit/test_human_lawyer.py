"""Unit tests for the Human Lawyer Mode: input queue, WS routing, REST endpoint."""

from __future__ import annotations

import uuid
from typing import Any, Dict

import pytest

# ---------------------------------------------------------------------------
# Tests for human_input module (pure asyncio, no DB)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_post_and_wait_human_action() -> None:
    """post_human_action enqueues an event that wait_for_human_action retrieves."""
    from app.orchestrator.human_input import (
        clear_human_queue,
        post_human_action,
        wait_for_human_action,
    )

    trial_id = uuid.uuid4()
    try:
        event: Dict[str, Any] = {
            "type": "human_action",
            "action": "examine",
            "text": "Where were you on the night of 14 March?",
        }
        post_human_action(trial_id, event)
        result = await wait_for_human_action(trial_id, timeout=1.0)
        assert result is not None
        assert result["action"] == "examine"
        assert "night" in result["text"]
    finally:
        clear_human_queue(trial_id)


@pytest.mark.asyncio
async def test_wait_human_action_timeout() -> None:
    """wait_for_human_action returns None when queue is empty and timeout expires."""
    from app.orchestrator.human_input import (
        clear_human_queue,
        wait_for_human_action,
    )

    trial_id = uuid.uuid4()
    try:
        result = await wait_for_human_action(trial_id, timeout=0.05)
        assert result is None
    finally:
        clear_human_queue(trial_id)


@pytest.mark.asyncio
async def test_post_object_event_enqueued() -> None:
    """Objection events are enqueued correctly with 'type': 'object'."""
    from app.orchestrator.human_input import (
        clear_human_queue,
        post_human_action,
        wait_for_human_action,
    )

    trial_id = uuid.uuid4()
    try:
        obj_payload = {
            "type": "object",
            "objection_type": "hearsay",
            "reason": "The witness is repeating an out-of-court statement for its truth.",
        }
        post_human_action(trial_id, obj_payload)
        result = await wait_for_human_action(trial_id, timeout=1.0)
        assert result is not None
        assert result["type"] == "object"
        assert result["objection_type"] == "hearsay"
    finally:
        clear_human_queue(trial_id)


@pytest.mark.asyncio
async def test_clear_human_queue_drains_pending() -> None:
    """clear_human_queue removes all pending events without raising."""
    from app.orchestrator.human_input import (
        clear_human_queue,
        get_human_queue,
        post_human_action,
    )

    trial_id = uuid.uuid4()
    for i in range(5):
        post_human_action(trial_id, {"type": "human_action", "action": f"action_{i}"})

    q = get_human_queue(trial_id)
    assert q.qsize() == 5

    clear_human_queue(trial_id)
    # Queue should be gone from registry
    from app.orchestrator import human_input as hi_module

    assert trial_id not in hi_module._human_queues


# ---------------------------------------------------------------------------
# Tests for WS router human-event gating (spectator mode rejection)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_human_input_module_multiple_trials_isolated() -> None:
    """Each trial_id gets an isolated queue — posting to one does not affect another."""
    from app.orchestrator.human_input import (
        clear_human_queue,
        post_human_action,
        wait_for_human_action,
    )

    trial_a = uuid.uuid4()
    trial_b = uuid.uuid4()
    try:
        post_human_action(trial_a, {"type": "human_action", "action": "argue"})
        # trial_b queue should still be empty → timeout
        result_b = await wait_for_human_action(trial_b, timeout=0.05)
        assert result_b is None

        result_a = await wait_for_human_action(trial_a, timeout=1.0)
        assert result_a is not None
        assert result_a["action"] == "argue"
    finally:
        clear_human_queue(trial_a)
        clear_human_queue(trial_b)


# ---------------------------------------------------------------------------
# Tests for TurnSummary schema (no DB required)
# ---------------------------------------------------------------------------


def test_turn_summary_schema_fields() -> None:
    """TurnSummary accepts all expected fields and has sensible defaults."""
    from app.schemas.trial import TurnSummary

    turn_id = uuid.uuid4()
    summary = TurnSummary(
        id=turn_id,
        seq=5,
        speaker="prosecutor",
        text="The state submits Exhibit A.",
        struck=False,
    )
    assert summary.id == turn_id
    assert summary.seq == 5
    assert summary.speaker == "prosecutor"
    assert summary.struck is False
    assert summary.phase is None
    assert summary.action is None


def test_human_action_request_schema() -> None:
    """HumanActionRequest validates correct human_action payload."""
    from app.schemas.trial import HumanActionRequest

    req = HumanActionRequest(
        type="human_action",
        action="examine",
        text="Did you see the accused at the market?",
        target="witness_1",
    )
    assert req.type == "human_action"
    assert req.action == "examine"
    assert req.target == "witness_1"


def test_human_action_request_objection_schema() -> None:
    """HumanActionRequest validates correct objection payload."""
    from app.schemas.trial import HumanActionRequest

    req = HumanActionRequest(
        type="object",
        objection_type="leading",
        reason="Counsel is suggesting the answer to the witness.",
    )
    assert req.type == "object"
    assert req.objection_type == "leading"
    assert req.action is None

