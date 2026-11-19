"""Unit tests for tier chain parsing and LLM router chat failover."""

import httpx
import pytest
import respx

from app.core.errors import LLMUnavailable
from app.llm.chains import (
    ChainLink,
    get_tier_chain,
    parse_chain,
    pool_registry,
)
from app.llm.client import get_provider_endpoint
from app.llm.router import chat


def test_parse_chain_ensures_ollama_terminal() -> None:
    # No ollama specified -> appends ollama
    links = parse_chain("groq|llama-3.3-70b-versatile,gemini|gemini-2.0-flash")
    assert len(links) == 3
    assert links[0] == ChainLink(provider="groq", model="llama-3.3-70b-versatile")
    assert links[1] == ChainLink(provider="gemini", model="gemini-2.0-flash")
    assert links[2].provider == "ollama"

    # Ollama in the middle -> moved to end
    links2 = parse_chain("ollama|llama3.2:latest,groq|llama-3.1-8b-instant")
    assert links2[0].provider == "groq"
    assert links2[-1].provider == "ollama"


def test_get_tier_chain() -> None:
    strong = get_tier_chain("strong")
    mid = get_tier_chain("mid")
    small = get_tier_chain("small")

    assert len(strong) >= 1
    assert strong[-1].provider == "ollama"
    assert mid[-1].provider == "ollama"
    assert small[-1].provider == "ollama"


@pytest.mark.asyncio
@respx.mock
async def test_chat_success_first_provider() -> None:
    pool_registry.reload_pools()
    # Add key to groq pool
    groq_pool = pool_registry.get_pool("groq")
    assert groq_pool is not None
    groq_pool.add_key("gsk-test-key")

    endpoint = get_provider_endpoint("groq")
    respx.post(endpoint).mock(
        return_value=httpx.Response(
            200,
            json={
                "choices": [{"message": {"role": "assistant", "content": "Sustained."}}],
                "usage": {"prompt_tokens": 12, "completion_tokens": 3},
            },
        )
    )

    result = await chat("mid", [{"role": "user", "content": "Your Honor?"}])
    assert result == "Sustained."


@pytest.mark.asyncio
@respx.mock
async def test_chat_failover_to_next_provider() -> None:
    pool_registry.reload_pools()
    groq_pool = pool_registry.get_pool("groq")
    gemini_pool = pool_registry.get_pool("gemini")
    assert groq_pool is not None and gemini_pool is not None

    groq_pool.add_key("gsk-test-groq")
    gemini_pool.add_key("gemini-test-key")

    # Groq returns 500 server error
    respx.post(get_provider_endpoint("groq")).mock(
        return_value=httpx.Response(500, text="Internal Groq Error")
    )
    # Gemini succeeds
    respx.post(get_provider_endpoint("gemini")).mock(
        return_value=httpx.Response(
            200,
            json={
                "choices": [{"message": {"role": "assistant", "content": "Overruled."}}],
                "usage": {"prompt_tokens": 15, "completion_tokens": 4},
            },
        )
    )

    result = await chat("mid", [{"role": "user", "content": "Objection!"}])
    assert result == "Overruled."


@pytest.mark.asyncio
@respx.mock
async def test_chat_all_providers_fail_raises_llm_unavailable() -> None:
    pool_registry.reload_pools()
    # Force mock on all potential endpoints to return 503
    respx.post(get_provider_endpoint("groq")).mock(return_value=httpx.Response(503))
    respx.post(get_provider_endpoint("gemini")).mock(return_value=httpx.Response(503))
    respx.post(get_provider_endpoint("openrouter")).mock(return_value=httpx.Response(503))
    respx.post(get_provider_endpoint("ollama")).mock(return_value=httpx.Response(503))

    with pytest.raises(LLMUnavailable) as exc_info:
        await chat("mid", [{"role": "user", "content": "Hello"}], max_attempts=4)

    assert exc_info.value.code.value == "LLM_UNAVAILABLE"
    assert exc_info.value.status_code == 503
