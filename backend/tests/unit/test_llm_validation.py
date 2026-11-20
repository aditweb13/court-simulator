"""Unit tests for Pydantic JSON response validation and retry in LLM router."""

import httpx
import pytest
import respx
from app.core.errors import LLMUnavailable
from app.llm.chains import pool_registry
from app.llm.client import get_provider_endpoint
from app.llm.router import chat
from pydantic import BaseModel, Field


class SampleVerdict(BaseModel):
    guilty: bool
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str


@pytest.mark.asyncio
@respx.mock
async def test_chat_json_validation_immediate_success() -> None:
    pool_registry.reload_pools()
    groq_pool = pool_registry.get_pool("groq")
    assert groq_pool is not None
    groq_pool.add_key("gsk-test")

    payload = '{"guilty": true, "confidence": 0.95, "reasoning": "Clear evidence."}'
    respx.post(get_provider_endpoint("groq")).mock(
        return_value=httpx.Response(
            200,
            json={
                "choices": [{"message": {"role": "assistant", "content": payload}}],
                "usage": {"prompt_tokens": 20, "completion_tokens": 15},
            },
        )
    )

    result = await chat(
        "mid", [{"role": "user", "content": "Deliberate"}], response_model=SampleVerdict
    )
    assert isinstance(result, SampleVerdict)
    assert result.guilty is True
    assert result.confidence == 0.95
    assert result.reasoning == "Clear evidence."


@pytest.mark.asyncio
@respx.mock
async def test_chat_json_validation_markdown_codeblock() -> None:
    pool_registry.reload_pools()
    groq_pool = pool_registry.get_pool("groq")
    assert groq_pool is not None
    groq_pool.add_key("gsk-test")

    md_payload = (
        '```json\n{"guilty": false, "confidence": 0.88, "reasoning": "Reasonable doubt."}\n```'
    )
    respx.post(get_provider_endpoint("groq")).mock(
        return_value=httpx.Response(
            200,
            json={
                "choices": [{"message": {"role": "assistant", "content": md_payload}}],
                "usage": {"prompt_tokens": 20, "completion_tokens": 15},
            },
        )
    )

    result = await chat(
        "mid", [{"role": "user", "content": "Deliberate"}], response_model=SampleVerdict
    )
    assert isinstance(result, SampleVerdict)
    assert result.guilty is False
    assert result.confidence == 0.88


@pytest.mark.asyncio
@respx.mock
async def test_chat_json_invalid_then_retry_succeeds() -> None:
    pool_registry.reload_pools()
    groq_pool = pool_registry.get_pool("groq")
    assert groq_pool is not None
    groq_pool.add_key("gsk-test")

    endpoint = get_provider_endpoint("groq")
    valid_payload = '{"guilty": true, "confidence": 0.99, "reasoning": "Confession"}'
    respx.post(endpoint).mock(
        side_effect=[
            httpx.Response(
                200,
                json={
                    "choices": [
                        {"message": {"role": "assistant", "content": "The accused is guilty."}}
                    ],
                    "usage": {"prompt_tokens": 20, "completion_tokens": 10},
                },
            ),
            httpx.Response(
                200,
                json={
                    "choices": [{"message": {"role": "assistant", "content": valid_payload}}],
                    "usage": {"prompt_tokens": 40, "completion_tokens": 15},
                },
            ),
        ]
    )

    result = await chat(
        "mid", [{"role": "user", "content": "Deliberate"}], response_model=SampleVerdict
    )
    assert isinstance(result, SampleVerdict)
    assert result.guilty is True
    assert result.confidence == 0.99


@pytest.mark.asyncio
@respx.mock
async def test_chat_json_retry_fails_falls_through_to_next_provider() -> None:
    pool_registry.reload_pools()
    groq_pool = pool_registry.get_pool("groq")
    gemini_pool = pool_registry.get_pool("gemini")
    assert groq_pool is not None and gemini_pool is not None

    groq_pool.add_key("gsk-test")
    gemini_pool.add_key("gemini-test")

    respx.post(get_provider_endpoint("groq")).mock(
        side_effect=[
            httpx.Response(
                200,
                json={"choices": [{"message": {"role": "assistant", "content": "Bad format 1"}}]},
            ),
            httpx.Response(
                200,
                json={"choices": [{"message": {"role": "assistant", "content": "Still bad 2"}}]},
            ),
        ]
    )

    gemini_payload = '{"guilty": false, "confidence": 0.70, "reasoning": "Gemini fallback"}'
    respx.post(get_provider_endpoint("gemini")).mock(
        return_value=httpx.Response(
            200,
            json={
                "choices": [{"message": {"role": "assistant", "content": gemini_payload}}],
                "usage": {"prompt_tokens": 25, "completion_tokens": 15},
            },
        )
    )

    result = await chat(
        "mid", [{"role": "user", "content": "Deliberate"}], response_model=SampleVerdict
    )
    assert isinstance(result, SampleVerdict)
    assert result.guilty is False
    assert result.reasoning == "Gemini fallback"


@pytest.mark.asyncio
@respx.mock
async def test_chat_json_all_providers_invalid_raises_llm_unavailable() -> None:
    pool_registry.reload_pools()
    groq_pool = pool_registry.get_pool("groq")
    assert groq_pool is not None
    groq_pool.add_key("gsk-test")

    respx.post(get_provider_endpoint("groq")).mock(
        return_value=httpx.Response(
            200,
            json={"choices": [{"message": {"role": "assistant", "content": "Not JSON"}}]},
        )
    )
    respx.post(get_provider_endpoint("gemini")).mock(
        return_value=httpx.Response(
            200,
            json={"choices": [{"message": {"role": "assistant", "content": "Not JSON"}}]},
        )
    )
    respx.post(get_provider_endpoint("ollama")).mock(
        return_value=httpx.Response(
            200,
            json={"choices": [{"message": {"role": "assistant", "content": "Not JSON"}}]},
        )
    )

    with pytest.raises(LLMUnavailable):
        await chat("mid", [{"role": "user", "content": "Deliberate"}], response_model=SampleVerdict)
