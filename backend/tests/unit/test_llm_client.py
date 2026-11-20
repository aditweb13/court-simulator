"""Unit tests for LLM provider HTTP client."""

import httpx
import pytest
import respx
from app.llm.client import (
    call_provider,
    get_provider_endpoint,
)
from app.llm.pool import AttemptOutcome, KeyState


def test_get_provider_endpoint() -> None:
    assert "googleapis.com" in get_provider_endpoint("gemini")
    assert "groq.com" in get_provider_endpoint("groq")
    assert "openrouter.ai" in get_provider_endpoint("openrouter")
    assert "11434" in get_provider_endpoint("ollama")
    assert get_provider_endpoint("gemini").endswith("/chat/completions")
    assert get_provider_endpoint("ollama").endswith("/v1/chat/completions")


@pytest.mark.asyncio
@respx.mock
async def test_call_provider_success() -> None:
    endpoint = get_provider_endpoint("groq")
    mock_route = respx.post(endpoint).mock(
        return_value=httpx.Response(
            200,
            json={
                "choices": [{"message": {"role": "assistant", "content": "Guilty as charged."}}],
                "usage": {"prompt_tokens": 42, "completion_tokens": 15},
            },
        )
    )

    key = KeyState(alias="groq#1", secret="gsk-test", provider="groq")
    resp = await call_provider(
        provider="groq",
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": "What is the verdict?"}],
        key=key,
    )

    assert mock_route.called
    assert resp.outcome == AttemptOutcome.OK
    assert resp.content == "Guilty as charged."
    assert resp.tokens_in == 42
    assert resp.tokens_out == 15
    assert resp.status_code == 200
    assert resp.latency_ms >= 0


@pytest.mark.asyncio
@respx.mock
async def test_call_provider_openrouter_headers() -> None:
    endpoint = get_provider_endpoint("openrouter")
    mock_route = respx.post(endpoint).mock(
        return_value=httpx.Response(
            200,
            json={
                "choices": [{"message": {"role": "assistant", "content": "OK"}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 2},
            },
        )
    )

    key = KeyState(alias="openrouter#1", secret="or-test", provider="openrouter")
    await call_provider(
        provider="openrouter",
        model="meta-llama/llama-3.3-70b",
        messages=[{"role": "user", "content": "Hi"}],
        key=key,
    )

    req = mock_route.calls.last.request
    assert req.headers.get("HTTP-Referer") == "https://verdict.local"
    assert req.headers.get("X-Title") == "Verdict"
    assert req.headers.get("Authorization") == "Bearer or-test"


@pytest.mark.asyncio
@respx.mock
async def test_call_provider_auth_error_401() -> None:
    endpoint = get_provider_endpoint("gemini")
    respx.post(endpoint).mock(return_value=httpx.Response(401, json={"error": "Invalid API key"}))

    key = KeyState(alias="gemini#1", secret="bad-key", provider="gemini")
    resp = await call_provider(
        provider="gemini",
        model="gemini-2.0-flash",
        messages=[{"role": "user", "content": "Hello"}],
        key=key,
    )

    assert resp.outcome == AttemptOutcome.QUOTA
    assert resp.status_code == 401
    assert resp.content is None


@pytest.mark.asyncio
@respx.mock
async def test_call_provider_skip_provider_400_404_422() -> None:
    endpoint = get_provider_endpoint("groq")
    respx.post(endpoint).mock(return_value=httpx.Response(404, json={"error": "Model not found"}))

    key = KeyState(alias="groq#1", secret="test", provider="groq")
    resp = await call_provider(
        provider="groq",
        model="nonexistent-model",
        messages=[{"role": "user", "content": "Hello"}],
        key=key,
    )

    assert resp.outcome == AttemptOutcome.SKIP_PROVIDER
    assert resp.status_code == 404


@pytest.mark.asyncio
@respx.mock
async def test_call_provider_rate_limit_with_retry_after() -> None:
    endpoint = get_provider_endpoint("groq")
    respx.post(endpoint).mock(
        return_value=httpx.Response(
            429,
            headers={"Retry-After": "45"},
            json={"error": "Rate limit exceeded"},
        )
    )

    key = KeyState(alias="groq#1", secret="test", provider="groq")
    resp = await call_provider(
        provider="groq",
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": "Hello"}],
        key=key,
    )

    assert resp.outcome == AttemptOutcome.ERROR
    assert resp.status_code == 429
    assert resp.retry_after == 45.0


@pytest.mark.asyncio
@respx.mock
async def test_call_provider_timeout() -> None:
    endpoint = get_provider_endpoint("ollama")
    respx.post(endpoint).mock(side_effect=httpx.ReadTimeout("Request timed out"))

    resp = await call_provider(
        provider="ollama",
        model="llama3.2:latest",
        messages=[{"role": "user", "content": "Hello"}],
        key=None,
        timeout=5.0,
    )

    assert resp.outcome == AttemptOutcome.TIMEOUT
    assert resp.content is None
    assert "Timeout" in (resp.error_message or "")


@pytest.mark.asyncio
@respx.mock
async def test_call_provider_transport_error() -> None:
    endpoint = get_provider_endpoint("ollama")
    respx.post(endpoint).mock(side_effect=httpx.ConnectError("Connection refused"))

    resp = await call_provider(
        provider="ollama",
        model="llama3.2:latest",
        messages=[{"role": "user", "content": "Hello"}],
        key=None,
    )

    assert resp.outcome == AttemptOutcome.TIMEOUT
    assert "Transport error" in (resp.error_message or "")
