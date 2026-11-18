"""Unit tests for KeyPool, KeyState, and status code classification."""

from app.llm.pool import (
    AttemptOutcome,
    KeyPool,
    KeyState,
    classify_status,
)


def test_key_state_initial_ready() -> None:
    ks = KeyState(alias="gemini#1", secret="secret-key", provider="gemini")
    assert ks.is_ready(now=100.0) is True
    assert ks.fail_count == 0


def test_key_state_bench_and_expiry() -> None:
    ks = KeyState(alias="gemini#1", secret="secret-key", provider="gemini")
    now = 1000.0
    # First failure: duration = min(60 * 2^0, 86400) = 60s
    ks.bench(now=now)
    assert ks.fail_count == 1
    assert ks.cooldown_until == 1060.0
    assert ks.is_ready(now=1059.0) is False
    assert ks.is_ready(now=1060.0) is True


def test_key_state_escalating_backoff() -> None:
    ks = KeyState(alias="groq#1", secret="k", provider="groq")
    now = 100.0
    # 1st fail -> 60s
    ks.bench(now=now)
    assert ks.cooldown_until == 160.0

    # 2nd fail -> 120s
    ks.bench(now=now)
    assert ks.cooldown_until == 220.0

    # 3rd fail -> 240s
    ks.bench(now=now)
    assert ks.cooldown_until == 340.0

    # High fail count hits max cap 86400s (24h)
    ks.fail_count = 15
    ks.bench(now=now)
    assert ks.cooldown_until == 100.0 + 86400.0


def test_key_state_retry_after() -> None:
    ks = KeyState(alias="openrouter#1", secret="k", provider="openrouter")
    now = 500.0
    ks.bench(retry_after=45.0, now=now)
    assert ks.cooldown_until == 545.0
    assert ks.fail_count == 1


def test_key_state_auth_failure_24h() -> None:
    ks = KeyState(alias="gemini#1", secret="bad-key", provider="gemini")
    now = 1000.0
    ks.bench(auth_failure=True, now=now)
    assert ks.cooldown_until == 1000.0 + 86400.0
    assert ks.is_ready(now=1000.0 + 86399.0) is False
    assert ks.is_ready(now=1000.0 + 86400.0) is True


def test_key_state_timeout_bench() -> None:
    ks = KeyState(alias="ollama#1", secret="local", provider="ollama")
    now = 100.0
    ks.bench(seconds=30.0, now=now)
    assert ks.cooldown_until == 130.0


def test_key_state_reset_on_success() -> None:
    ks = KeyState(alias="gemini#1", secret="k", provider="gemini")
    ks.bench(now=100.0)
    assert ks.fail_count == 1
    assert ks.cooldown_until > 0.0

    ks.reset()
    assert ks.fail_count == 0
    assert ks.cooldown_until == 0.0
    assert ks.is_ready(now=50.0) is True


def test_key_pool_add_and_pick() -> None:
    pool = KeyPool(provider="gemini")
    assert pool.size == 0
    assert pool.pick(now=100.0) is None
    assert pool.all_cooling(now=100.0) is True

    k1 = pool.add_key("key-1")
    k2 = pool.add_key("key-2")
    assert pool.size == 2
    assert k1.alias == "gemini#1"
    assert k2.alias == "gemini#2"

    picked = pool.pick(now=100.0)
    assert picked is not None
    assert picked.secret in ("key-1", "key-2")


def test_key_pool_all_cooling_and_recovery() -> None:
    pool = KeyPool(provider="groq")
    k1 = pool.add_key("k1")
    k2 = pool.add_key("k2")

    now = 1000.0
    k1.bench(now=now)
    assert pool.all_cooling(now=now) is False
    assert pool.pick(now=now) == k2

    k2.bench(now=now)
    assert pool.all_cooling(now=now) is True
    assert pool.pick(now=now) is None

    # After cooldown expires (60s)
    future = 1061.0
    assert pool.all_cooling(now=future) is False
    picked = pool.pick(now=future)
    assert picked is not None


def test_classify_status() -> None:
    # 200 -> OK
    assert classify_status(200) == AttemptOutcome.OK

    # 401, 403 -> QUOTA (auth failure, bench 24h)
    assert classify_status(401) == AttemptOutcome.QUOTA
    assert classify_status(403) == AttemptOutcome.QUOTA

    # 400, 404, 422 -> SKIP_PROVIDER without benching
    assert classify_status(400) == AttemptOutcome.SKIP_PROVIDER
    assert classify_status(404) == AttemptOutcome.SKIP_PROVIDER
    assert classify_status(422) == AttemptOutcome.SKIP_PROVIDER

    # 429, 500, 502, 503 -> ERROR (bench with retry-after or escalation)
    assert classify_status(429) == AttemptOutcome.ERROR
    assert classify_status(500) == AttemptOutcome.ERROR
    assert classify_status(503) == AttemptOutcome.ERROR
