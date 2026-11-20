"""Forced-failover integration tests for LLM router.

Covers all required failover conditions:
- Bad API key (401/403): benched 24h, next key succeeds
- Rate limit (429): benched with Retry-After, next key succeeds
- All keys exhausted: moves to next provider
- Timeout / transport error: benched 30s, falls over
- Bad request (400/404/422): skips provider WITHOUT benching key
- Entire chain exhausted: raises LLMUnavailable (HTTP 503)
- Live test marker (@pytest.mark.live) exclusion check
"""

import httpx
import pytest
import respx
from app.core.errors import LLMUnavailable
from app.llm.chains import pool_registry
from app.llm.client import get_provider_endpoint
from app.llm.pool import KeyPool
from app.llm.router import chat


@pytest.fixture(autouse=True)
def clean_pools():
    """Ensure pools are clean for deterministic failover tests and restored afterward."""
    for pool in pool_registry._pools.values():
        pool.keys.clear()
    yield
    pool_registry.reload_pools()


@pytest.mark.asyncio
@respx.mock
async def test_failover_bad_key_401_benched_next_key_succeeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    groq_pool = pool_registry.get_pool("groq")
    assert groq_pool is not None

    k1 = groq_pool.add_key("bad-groq-key")
    k2 = groq_pool.add_key("good-groq-key")

    # Ensure k1 is picked first to test deterministic failover
    monkeypatch.setattr("random.choice", lambda items: items[0])

    endpoint = get_provider_endpoint("groq")

    def groq_dispatcher(request: httpx.Request) -> httpx.Response:
        auth = request.headers.get("Authorization", "")
        if "bad-groq-key" in auth:
            return httpx.Response(401, json={"error": "Unauthorized / Bad key"})
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"role": "assistant", "content": "Recovered with k2"}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5},
            },
        )

    respx.post(endpoint).mock(side_effect=groq_dispatcher)

    result = await chat("small", [{"role": "user", "content": "Test"}])
    assert result == "Recovered with k2"
    # k1 must be benched for 24h (auth_failure=True)
    assert k1.fail_count >= 1
    assert not k1.is_ready()
    # k2 must be reset and ready
    assert k2.is_ready()
    assert k2.fail_count == 0


@pytest.mark.asyncio
@respx.mock
async def test_failover_429_then_next_key_succeeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    groq_pool = pool_registry.get_pool("groq")
    assert groq_pool is not None

    k1 = groq_pool.add_key("quota-groq-key")
    k2 = groq_pool.add_key("fresh-groq-key")

    monkeypatch.setattr("random.choice", lambda items: items[0])

    endpoint = get_provider_endpoint("groq")

    def groq_quota_dispatcher(request: httpx.Request) -> httpx.Response:
        auth = request.headers.get("Authorization", "")
        if "quota-groq-key" in auth:
            return httpx.Response(
                429,
                headers={"Retry-After": "120"},
                json={"error": "Rate limit exceeded"},
            )
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"role": "assistant", "content": "Key 2 success"}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5},
            },
        )

    respx.post(endpoint).mock(side_effect=groq_quota_dispatcher)

    result = await chat("small", [{"role": "user", "content": "Hello"}])
    assert result == "Key 2 success"
    # k1 was benched
    assert not k1.is_ready()
    assert k2.is_ready()


@pytest.mark.asyncio
@respx.mock
async def test_failover_all_keys_exhausted_then_next_provider() -> None:
    groq_pool = pool_registry.get_pool("groq")
    gemini_pool = pool_registry.get_pool("gemini")
    assert groq_pool is not None and gemini_pool is not None

    k1 = groq_pool.add_key("groq-key-1")
    k2 = groq_pool.add_key("groq-key-2")
    g1 = gemini_pool.add_key("gemini-key-1")

    # Both Groq keys return 429
    respx.post(get_provider_endpoint("groq")).mock(
        return_value=httpx.Response(429, json={"error": "All groq keys down"})
    )
    # Gemini returns 200
    respx.post(get_provider_endpoint("gemini")).mock(
        return_value=httpx.Response(
            200,
            json={
                "choices": [{"message": {"role": "assistant", "content": "Gemini answer"}}],
                "usage": {"prompt_tokens": 15, "completion_tokens": 5},
            },
        )
    )

    result = await chat("mid", [{"role": "user", "content": "Exhaust groq"}])
    assert result == "Gemini answer"
    assert not k1.is_ready()
    assert not k2.is_ready()
    assert g1.is_ready()


@pytest.mark.asyncio
@respx.mock
async def test_failover_timeout_benches_30s_then_next_provider() -> None:
    groq_pool = pool_registry.get_pool("groq")
    gemini_pool = pool_registry.get_pool("gemini")
    assert groq_pool is not None and gemini_pool is not None

    k1 = groq_pool.add_key("slow-groq-key")
    gemini_pool.add_key("fast-gemini-key")

    respx.post(get_provider_endpoint("groq")).mock(
        side_effect=httpx.ReadTimeout("Request timed out")
    )
    respx.post(get_provider_endpoint("gemini")).mock(
        return_value=httpx.Response(
            200,
            json={
                "choices": [{"message": {"role": "assistant", "content": "Gemini saved the day"}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5},
            },
        )
    )

    result = await chat("mid", [{"role": "user", "content": "Timeout test"}], timeout=2.0)
    assert result == "Gemini saved the day"
    # k1 was benched for 30s
    assert not k1.is_ready()


@pytest.mark.asyncio
@respx.mock
async def test_failover_400_skips_provider_without_benching() -> None:
    groq_pool = pool_registry.get_pool("groq")
    gemini_pool = pool_registry.get_pool("gemini")
    assert groq_pool is not None and gemini_pool is not None

    k1 = groq_pool.add_key("valid-key-bad-model")
    gemini_pool.add_key("gemini-ok")

    # Groq returns 400 Bad Request
    respx.post(get_provider_endpoint("groq")).mock(
        return_value=httpx.Response(400, json={"error": "Model not supported"})
    )
    # Gemini succeeds
    respx.post(get_provider_endpoint("gemini")).mock(
        return_value=httpx.Response(
            200,
            json={
                "choices": [{"message": {"role": "assistant", "content": "Success on Gemini"}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5},
            },
        )
    )

    result = await chat("mid", [{"role": "user", "content": "Skip 400 test"}])
    assert result == "Success on Gemini"
    # k1 should NOT be benched because 400/404/422 skips provider without benching
    assert k1.fail_count == 0
    assert k1.is_ready()


@pytest.mark.asyncio
@respx.mock
async def test_failover_entire_chain_down_raises_503() -> None:
    # Use empty custom pools
    pool_registry._pools = {
        "groq": KeyPool(provider="groq"),
        "gemini": KeyPool(provider="gemini"),
        "openrouter": KeyPool(provider="openrouter"),
        "ollama": KeyPool(provider="ollama"),
    }
    pool_registry._pools["groq"].add_key("k")
    pool_registry._pools["ollama"].add_key("local")

    respx.post(get_provider_endpoint("groq")).mock(return_value=httpx.Response(500))
    respx.post(get_provider_endpoint("ollama")).mock(return_value=httpx.Response(500))

    with pytest.raises(LLMUnavailable) as exc:
        await chat("small", [{"role": "user", "content": "Down"}], max_attempts=4)

    assert exc.value.status_code == 503
    assert exc.value.code.value == "LLM_UNAVAILABLE"


@pytest.mark.live
def test_live_marker_example() -> None:
    """Excluded from CI runs using '-m not live'."""
    assert True
