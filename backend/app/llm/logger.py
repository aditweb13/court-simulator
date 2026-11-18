"""Persistence and audit logger for individual LLM call attempts.

Records provider, model, key_alias, token counts, latency, and status.
Never records raw API keys, secrets, or prompt texts.
"""

from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.llm_call import LLMCall
from app.db.session import async_session_maker

logger = logging.getLogger("app.llm.logger")


async def record_llm_call(
    provider: str,
    model: str,
    key_alias: str,
    tokens_in: Optional[int],
    tokens_out: Optional[int],
    latency_ms: int,
    status: str,
    trial_id: Optional[UUID] = None,
    agent_role: Optional[str] = None,
    session: Optional[AsyncSession] = None,
) -> Optional[LLMCall]:
    """Persist an LLM attempt record to the database.

    Parameters
    ----------
    provider:
        Provider name (e.g. 'groq', 'gemini').
    model:
        Model ID (e.g. 'llama-3.3-70b-versatile').
    key_alias:
        Public identifier like 'gemini#1' (NEVER the actual key).
    tokens_in:
        Number of input prompt tokens if reported by provider.
    tokens_out:
        Number of generated completion tokens if reported by provider.
    latency_ms:
        Call duration in milliseconds.
    status:
        Outcome string: 'ok', 'quota', 'error', 'timeout'.
    trial_id:
        Optional UUID of the trial for attribution.
    agent_role:
        Optional role of the agent making the call.
    session:
        Optional active AsyncSession. If omitted, a new session is opened.

    Returns
    -------
    LLMCall | None:
        The persisted model instance or None if database is unreachable.
    """
    call_record = LLMCall(
        trial_id=trial_id,
        agent_role=agent_role,
        provider=provider,
        model=model,
        key_alias=key_alias,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        latency_ms=latency_ms,
        status=status,
    )

    if session is not None:
        try:
            session.add(call_record)
            await session.flush()
            return call_record
        except Exception as exc:
            logger.warning("Failed to record LLM call with provided session: %s", exc)
            return None

    try:
        async with async_session_maker() as new_session:
            async with new_session.begin():
                new_session.add(call_record)
        return call_record
    except Exception as exc:
        logger.debug("Database write for LLM call skipped (e.g. test environment): %s", exc)
        return None
