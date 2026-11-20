"""Headless auto-ack client for unattended trial simulations.

Allows the orchestrator and LangGraph courtroom graph to run without a browser,
automatically acknowledging LineEvents and streaming server events into memory.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from app.ws.connection import ConnectionManager
from app.ws.connection import manager as default_ws_manager

logger = logging.getLogger("app.orchestrator.headless")


class HeadlessWebSocket:
    """Mock WebSocket implementing the interface expected by ConnectionManager."""

    def __init__(
        self,
        trial_id: UUID,
        ws_manager: ConnectionManager,
        auto_ack: bool = True,
    ) -> None:
        self.trial_id = trial_id
        self.ws_manager = ws_manager
        self.auto_ack = auto_ack
        self.received_events: List[Dict[str, Any]] = []

    async def accept(self) -> None:
        """No-op accept."""
        pass

    async def send_text(self, data: str) -> None:
        """Receive serialized event from orchestrator and trigger auto-ack for lines."""
        try:
            event = json.loads(data)
        except Exception:
            event = {"raw": data}

        self.received_events.append(event)

        # If line turn event, immediately acknowledge sequence number
        if self.auto_ack:
            evt_type = event.get("type") or event.get("event")
            seq = event.get("seq")
            if evt_type == "line" and seq is not None:
                logger.debug(
                    "Headless auto-ack acknowledging trial %s seq %d",
                    self.trial_id,
                    seq,
                )
                self.ws_manager.handle_ack(self.trial_id, int(seq))

    async def close(self, code: int = 1000) -> None:
        """No-op close."""
        pass


class HeadlessAutoAckClient:
    """Context manager attaching a headless auto-ack receiver to a trial."""

    def __init__(
        self,
        trial_id: UUID,
        ws_manager: Optional[ConnectionManager] = None,
        auto_ack: bool = True,
    ) -> None:
        self.trial_id = trial_id
        self.ws_manager = ws_manager or default_ws_manager
        self.auto_ack = auto_ack
        self.mock_socket: Optional[HeadlessWebSocket] = None

    async def __aenter__(self) -> "HeadlessAutoAckClient":
        self.mock_socket = HeadlessWebSocket(
            trial_id=self.trial_id,
            ws_manager=self.ws_manager,
            auto_ack=self.auto_ack,
        )
        await self.ws_manager.connect(self.trial_id, self.mock_socket)  # type: ignore[arg-type]
        logger.info("Headless auto-ack client connected for trial %s", self.trial_id)
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self.mock_socket:
            self.ws_manager.disconnect(self.trial_id, self.mock_socket)  # type: ignore[arg-type]
            logger.info("Headless auto-ack client disconnected for trial %s", self.trial_id)

    @property
    def events(self) -> List[Dict[str, Any]]:
        """List of all server events recorded during the trial run."""
        if self.mock_socket:
            return self.mock_socket.received_events
        return []

    def get_events_by_type(self, event_type: str) -> List[Dict[str, Any]]:
        """Filter captured events by event name (e.g. 'line', 'verdict', 'ruling')."""
        return [
            e for e in self.events if (e.get("type") == event_type or e.get("event") == event_type)
        ]
