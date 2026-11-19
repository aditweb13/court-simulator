"""WebSocket connection management, event dispatch, and ack tracking."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Dict, List
from uuid import UUID

from fastapi import WebSocket
from pydantic import BaseModel

from app.ws.schemas import ServerEvent

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages active WebSocket sessions per trial and resolves client acks."""

    def __init__(self) -> None:
        # trial_id -> list of active WebSockets
        self.active_connections: Dict[UUID, List[WebSocket]] = {}
        # (trial_id, seq) -> asyncio.Future
        self._pending_acks: Dict[tuple[UUID, int], asyncio.Future[bool]] = {}
        # trial_id -> set of acknowledged seq numbers
        self._acknowledged_seqs: Dict[UUID, set[int]] = {}

    async def connect(self, trial_id: UUID, websocket: WebSocket) -> None:
        await websocket.accept()
        if trial_id not in self.active_connections:
            self.active_connections[trial_id] = []
        self.active_connections[trial_id].append(websocket)
        logger.info(
            "WebSocket connected for trial %s (active: %d)",
            trial_id,
            len(self.active_connections[trial_id]),
        )

    def disconnect(self, trial_id: UUID, websocket: WebSocket) -> None:
        if trial_id in self.active_connections:
            if websocket in self.active_connections[trial_id]:
                self.active_connections[trial_id].remove(websocket)
            if not self.active_connections[trial_id]:
                del self.active_connections[trial_id]
                self._acknowledged_seqs.pop(trial_id, None)
        logger.info("WebSocket disconnected for trial %s", trial_id)

    def is_connected(self, trial_id: UUID) -> bool:
        return bool(self.active_connections.get(trial_id))

    async def send_event(self, trial_id: UUID, event: ServerEvent | BaseModel | dict) -> None:
        """Send an event payload to all clients connected to a trial."""
        sockets = self.active_connections.get(trial_id, [])
        if not sockets:
            logger.debug("No active WebSocket clients for trial %s to receive event", trial_id)
            return

        payload_str = event.model_dump_json() if isinstance(event, BaseModel) else json.dumps(event)

        dead_sockets: List[WebSocket] = []
        for ws in sockets:
            try:
                await ws.send_text(payload_str)
            except Exception as e:
                logger.warning("Failed to send WebSocket message on trial %s: %e", trial_id, e)
                dead_sockets.append(ws)

        for dead_ws in dead_sockets:
            self.disconnect(trial_id, dead_ws)

    def handle_ack(self, trial_id: UUID, seq: int) -> None:
        """Handle incoming client ack for sequence number."""
        if trial_id not in self._acknowledged_seqs:
            self._acknowledged_seqs[trial_id] = set()
        self._acknowledged_seqs[trial_id].add(seq)

        key = (trial_id, seq)
        future = self._pending_acks.pop(key, None)
        if future and not future.done():
            future.set_result(True)
            logger.debug("Ack resolved for trial %s, seq %d", trial_id, seq)

    async def wait_for_ack(self, trial_id: UUID, seq: int, timeout: float = 10.0) -> bool:
        """Wait for client to acknowledge playing a line turn within timeout seconds.

        Returns True if ack received within timeout, False if timed out (dead client or paused).
        """
        # If no client connected, fail fast / pause
        if not self.is_connected(trial_id):
            logger.warning(
                "No client connected for trial %s while awaiting ack for seq %d", trial_id, seq
            )
            return False

        # Fast path: already acknowledged
        if seq in self._acknowledged_seqs.get(trial_id, set()):
            return True

        loop = asyncio.get_running_loop()
        future: asyncio.Future[bool] = loop.create_future()
        key = (trial_id, seq)
        self._pending_acks[key] = future

        try:
            ack_received = await asyncio.wait_for(future, timeout=timeout)
            return ack_received
        except asyncio.TimeoutError:
            self._pending_acks.pop(key, None)
            logger.warning(
                "Ack timeout (%.1fs) on trial %s for seq %d; client assumed dead or paused",
                timeout,
                trial_id,
                seq,
            )
            return False


# Global singleton instance
manager = ConnectionManager()
