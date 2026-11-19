"""WebSocket route for live courtroom streaming and interactive player sessions."""

from __future__ import annotations

import asyncio
import json
import logging
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from pydantic import ValidationError
from sqlalchemy import select

from app.core.security import decode_access_token
from app.db.models.trial import Trial
from app.db.session import async_session_maker
from app.ws.connection import manager
from app.ws.schemas import (
    AckEvent,
    AuthEvent,
    ErrorEvent,
    HumanActionEvent,
    ObjectEvent,
    StateEvent,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/v1/trials/{trial_id}")
async def trial_websocket_endpoint(websocket: WebSocket, trial_id: UUID) -> None:
    await websocket.accept()

    # Step 1: 5-second Authentication Handshake
    try:
        raw_msg = await asyncio.wait_for(websocket.receive_text(), timeout=5.0)
    except asyncio.TimeoutError:
        err = ErrorEvent(
            code="UNAUTHENTICATED",
            message="Authentication timeout: missing auth message within 5 seconds",
        )
        await websocket.send_text(err.model_dump_json())
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    try:
        parsed_data = json.loads(raw_msg)
        auth_event = AuthEvent.model_validate(parsed_data)
        payload = decode_access_token(auth_event.token)
        if not payload.get("sub"):
            raise ValueError("Token missing subject identifier")
    except (json.JSONDecodeError, ValidationError, ValueError, Exception):
        err = ErrorEvent(
            code="UNAUTHENTICATED",
            message="Invalid or missing authentication credentials in auth handshake",
        )
        await websocket.send_text(err.model_dump_json())
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # Step 2: Validate trial existence in database
    async with async_session_maker() as session:
        stmt = select(Trial).where(Trial.id == trial_id)
        res = await session.execute(stmt)
        trial_row = res.scalar_one_or_none()
        if trial_row is None:
            err = ErrorEvent(
                code="NOT_FOUND",
                message=f"Trial '{trial_id}' does not exist",
            )
            await websocket.send_text(err.model_dump_json())
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
        initial_state = trial_row.state

    # Step 3: Register active connection and send initial trial state
    if trial_id not in manager.active_connections:
        manager.active_connections[trial_id] = []
    manager.active_connections[trial_id].append(websocket)
    logger.info("WebSocket authenticated for trial %s (user: %s)", trial_id, payload.get("sub"))

    state_event = StateEvent(state=initial_state)
    await websocket.send_text(state_event.model_dump_json())

    # Step 4: Receive and dispatch client events
    try:
        while True:
            text = await websocket.receive_text()
            try:
                data = json.loads(text)
                msg_type = data.get("type")

                if msg_type == "ack":
                    ack = AckEvent.model_validate(data)
                    manager.handle_ack(trial_id, ack.seq)
                elif msg_type == "human_action":
                    action_event = HumanActionEvent.model_validate(data)
                    logger.info("Human action on trial %s: %s", trial_id, action_event.action)
                elif msg_type == "object":
                    obj_event = ObjectEvent.model_validate(data)
                    logger.info("Objection on trial %s: %s", trial_id, obj_event.objection_type)
                else:
                    logger.debug(
                        "Unhandled event '%s' on trial %s", msg_type, trial_id
                    )
            except (json.JSONDecodeError, ValidationError) as e:
                logger.warning("Malformed client message on trial %s: %s", trial_id, e)
    except WebSocketDisconnect:
        manager.disconnect(trial_id, websocket)
    except Exception as e:
        logger.error("Unexpected WebSocket error on trial %s: %s", trial_id, e)
        manager.disconnect(trial_id, websocket)
