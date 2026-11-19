"""Unit tests for LLM call logging model and persistence."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.db.models.llm_call import LLMCall
from app.llm.logger import record_llm_call


def test_llm_call_model_structure() -> None:
    trial_id = uuid.uuid4()
    call = LLMCall(
        trial_id=trial_id,
        agent_role="prosecutor",
        provider="groq",
        model="llama-3.3-70b-versatile",
        key_alias="groq#1",
        tokens_in=120,
        tokens_out=45,
        latency_ms=350,
        status="ok",
    )

    assert call.trial_id == trial_id
    assert call.agent_role == "prosecutor"
    assert call.provider == "groq"
    assert call.model == "llama-3.3-70b-versatile"
    assert call.key_alias == "groq#1"
    assert call.tokens_in == 120
    assert call.tokens_out == 45
    assert call.latency_ms == 350
    assert call.status == "ok"

    # Strictly verify that no prompt or secret fields exist
    assert not hasattr(call, "prompt")
    assert not hasattr(call, "secret")
    assert not hasattr(call, "api_key")


@pytest.mark.asyncio
async def test_record_llm_call_with_session() -> None:
    mock_session = MagicMock()
    mock_session.add = MagicMock()
    mock_session.flush = AsyncMock()

    trial_id = uuid.uuid4()
    result = await record_llm_call(
        provider="gemini",
        model="gemini-2.0-flash",
        key_alias="gemini#2",
        tokens_in=250,
        tokens_out=50,
        latency_ms=420,
        status="ok",
        trial_id=trial_id,
        agent_role="judge",
        session=mock_session,
    )

    assert result is not None
    assert result.key_alias == "gemini#2"
    assert result.trial_id == trial_id
    mock_session.add.assert_called_once()
    mock_session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_record_llm_call_session_error_handling() -> None:
    mock_session = MagicMock()
    mock_session.add = MagicMock()
    mock_session.flush = AsyncMock(side_effect=RuntimeError("DB write failed"))

    result = await record_llm_call(
        provider="ollama",
        model="llama3.2:latest",
        key_alias="ollama#local",
        tokens_in=None,
        tokens_out=None,
        latency_ms=100,
        status="timeout",
        session=mock_session,
    )

    # Should gracefully catch error and return None without raising
    assert result is None
