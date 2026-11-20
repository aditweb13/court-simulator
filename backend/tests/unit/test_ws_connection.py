"""Unit and integration tests for WebSocket connection, auth handshake, and event schemas."""

import asyncio
import json
import uuid

import pytest
from app.core.security import create_access_token
from app.main import app
from app.ws.connection import ConnectionManager
from app.ws.schemas import (
    AckEvent,
    AuthEvent,
    ErrorEvent,
    HumanActionEvent,
    LineEvent,
    ObjectEvent,
    PromptEvent,
    RulingEvent,
    StateEvent,
    VerdictEvent,
)
from starlette.testclient import TestClient


def test_ws_schemas_roundtrip():
    # LineEvent
    line = LineEvent(
        seq=1,
        speaker="judge",
        text="The court will come to order.",
        action="gavel",
        emotion="neutral",
        camera="wide",
    )
    assert json.loads(line.model_dump_json())["seq"] == 1

    # RulingEvent
    ruling = RulingEvent(
        seq=2,
        objection_type="hearsay",
        ruling="sustained",
        struck=True,
        reason="Witness cannot testify to out-of-court statements without exception.",
    )
    assert ruling.struck is True

    # StateEvent
    state = StateEvent(state="OPENINGS", previous_state="SETUP")
    assert state.state == "OPENINGS"

    # PromptEvent
    prompt = PromptEvent(role="defense", options=["examine", "object"])
    assert "object" in prompt.options

    # VerdictEvent
    verdict = VerdictEvent(
        outcome="guilty",
        score=0.82,
        threshold=0.75,
        disagreement=0.04,
        matches_truth=True,
    )
    assert verdict.outcome == "guilty"

    # ErrorEvent
    err = ErrorEvent(code="UNAUTHENTICATED", message="Auth required")
    assert err.code == "UNAUTHENTICATED"

    # Client events
    auth = AuthEvent(token="test-jwt-token")
    assert auth.token == "test-jwt-token"

    ack = AckEvent(seq=42)
    assert ack.seq == 42

    action = HumanActionEvent(action="examine", text="Where were you?")
    assert action.action == "examine"

    obj = ObjectEvent(objection_type="hearsay", reason="Hearsay evidence")
    assert obj.objection_type == "hearsay"


@pytest.mark.asyncio
async def test_connection_manager_ack_resolution():
    cm = ConnectionManager()
    trial_id = uuid.uuid4()

    # Simulate connection
    cm.active_connections[trial_id] = [object()]  # type: ignore[list-item]

    # Task awaiting ack
    async def awaiter() -> bool:
        return await cm.wait_for_ack(trial_id, seq=10, timeout=1.0)

    task = asyncio.create_task(awaiter())
    await asyncio.sleep(0.05)

    # Deliver ack
    cm.handle_ack(trial_id, seq=10)
    result = await task
    assert result is True


@pytest.mark.asyncio
async def test_connection_manager_ack_timeout():
    cm = ConnectionManager()
    trial_id = uuid.uuid4()
    cm.active_connections[trial_id] = [object()]  # type: ignore[list-item]

    # Await ack with very short timeout
    result = await cm.wait_for_ack(trial_id, seq=99, timeout=0.1)
    assert result is False


def test_ws_auth_handshake_success():
    client = TestClient(app)

    # Create a trial first
    create_resp = client.post(
        "/api/v1/trials",
        json={"case_id": "state-v-malhotra-2024", "mode": "watch"},
    )
    assert create_resp.status_code == 201
    trial_id = create_resp.json()["data"]["id"]

    # Generate valid JWT
    user_id = str(uuid.uuid4())
    token = create_access_token({"sub": user_id, "email": "lawyer@court.in"})

    with client.websocket_connect(f"/ws/v1/trials/{trial_id}") as ws:
        # Send auth message
        ws.send_text(json.dumps({"type": "auth", "token": token}))

        # Expect initial StateEvent
        msg = ws.receive_text()
        data = json.loads(msg)
        assert data["type"] == "state"
        assert data["state"] == "SETUP"

        # Send an ack
        ws.send_text(json.dumps({"type": "ack", "seq": 0}))


def test_ws_auth_handshake_invalid_token_rejected():
    client = TestClient(app)
    trial_id = str(uuid.uuid4())

    with client.websocket_connect(f"/ws/v1/trials/{trial_id}") as ws:
        ws.send_text(json.dumps({"type": "auth", "token": "invalid-garbage-token"}))
        msg = ws.receive_text()
        data = json.loads(msg)
        assert data["type"] == "error"
        assert data["code"] == "UNAUTHENTICATED"
