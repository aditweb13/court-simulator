"""Human-input coordination module for interactive trial modes.

Provides a per-trial asyncio Queue that the WebSocket router populates and
orchestrator nodes drain when awaiting human actions (lawyer, judge, juror modes).
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Optional
from uuid import UUID

logger = logging.getLogger(__name__)

# Module-level registry: trial_id -> asyncio.Queue[dict]
_human_queues: Dict[UUID, asyncio.Queue[dict]] = {}


def get_human_queue(trial_id: UUID) -> asyncio.Queue[dict]:
    """Return (and create if absent) the queue for *trial_id*."""
    if trial_id not in _human_queues:
        _human_queues[trial_id] = asyncio.Queue()
    return _human_queues[trial_id]


def post_human_action(trial_id: UUID, event: Dict[str, Any]) -> None:
    """Put *event* into the trial's human-input queue (non-blocking)."""
    q = get_human_queue(trial_id)
    q.put_nowait(event)
    logger.debug("Human action posted to trial %s: %s", trial_id, event.get("type"))


async def wait_for_human_action(
    trial_id: UUID,
    timeout: float = 120.0,
) -> Optional[Dict[str, Any]]:
    """Await the next human action for *trial_id*, returning None on timeout."""
    q = get_human_queue(trial_id)
    try:
        event = await asyncio.wait_for(q.get(), timeout=timeout)
        logger.info("Human action received for trial %s: %s", trial_id, event.get("type"))
        return event
    except asyncio.TimeoutError:
        logger.warning("Human action timed out for trial %s after %.0fs", trial_id, timeout)
        return None


def clear_human_queue(trial_id: UUID) -> None:
    """Drain and remove the queue for a finished trial (cleanup)."""
    q = _human_queues.pop(trial_id, None)
    if q is not None:
        while not q.empty():
            try:
                q.get_nowait()
            except asyncio.QueueEmpty:
                break
        logger.debug("Human queue cleared for trial %s", trial_id)

