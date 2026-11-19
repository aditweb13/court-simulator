"""Unit tests for GET /admin/llm-status and admin authorization."""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_current_user
from app.db.models.llm_call import LLMCall
from app.db.models.user import User
from app.db.session import async_session_maker, get_db
from app.llm.chains import pool_registry
from app.main import app


@pytest.fixture
async def db_session():
    async with async_session_maker() as session:
        yield session


@pytest.mark.asyncio
async def test_admin_llm_status_unauthenticated():
    """Unauthenticated access to /admin/llm-status must be rejected with 401."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/admin/llm-status")
        assert res.status_code == 401
        body = res.json()
        assert body["error"]["code"] == "UNAUTHENTICATED"


@pytest.mark.asyncio
async def test_admin_llm_status_forbidden_for_non_admin():
    """Authenticated user whose email is not in ADMIN_EMAILS must receive 403."""
    non_admin_user = User(
        id=uuid.uuid4(),
        email="regular_user@example.com",
        display_name="Regular User",
        is_guest=False,
    )
    app.dependency_overrides[get_current_user] = lambda: non_admin_user

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            res = await client.get("/admin/llm-status")
            assert res.status_code == 403
            body = res.json()
            assert body["error"]["code"] == "FORBIDDEN"
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_admin_llm_status_forbidden_for_guest():
    """Guest user without an email must receive 403."""
    guest_user = User(
        id=uuid.uuid4(),
        email=None,
        display_name="Guest User",
        is_guest=True,
    )
    app.dependency_overrides[get_current_user] = lambda: guest_user

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            res = await client.get("/admin/llm-status")
            assert res.status_code == 403
            body = res.json()
            assert body["error"]["code"] == "FORBIDDEN"
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_admin_llm_status_success_for_admin(db_session: Any):
    """Admin user in ADMIN_EMAILS receives provider statuses and no secret keys."""
    admin_user = User(
        id=uuid.uuid4(),
        email="admin@verdict.internal",
        display_name="Admin",
        is_guest=False,
    )
    app.dependency_overrides[get_current_user] = lambda: admin_user
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            res = await client.get("/admin/llm-status")
            assert res.status_code == 200
            payload = res.json()
            assert "data" in payload
            providers = payload["data"]
            assert isinstance(providers, list)
            assert len(providers) > 0

            # Verify providers exist
            prov_names = {p["provider"] for p in providers}
            assert "gemini" in prov_names or "groq" in prov_names

            # Verify key structure and guarantee no secrets leaked
            for prov in providers:
                assert "provider" in prov
                assert "total_keys" in prov
                assert "ready_keys" in prov
                assert "cooling_keys" in prov
                assert isinstance(prov["keys"], list)

                for k in prov["keys"]:
                    assert "key_alias" in k
                    assert "cooling_down_seconds" in k
                    assert "fail_count" in k
                    assert "is_ready" in k
                    assert "last_status" in k
                    assert "recent_call_count" in k
                    # Critical security rule: NEVER leak secrets
                    assert "secret" not in k
                    assert "key" not in k
                    assert not k["key_alias"].startswith("sk-")
                    assert not k["key_alias"].startswith("gsk_")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_admin_llm_status_cooldown_and_call_logging(db_session: Any):
    """Cooldown seconds and recent calls in DB are properly reflected."""
    admin_user = User(
        id=uuid.uuid4(),
        email="admin@verdict.internal",
        display_name="Admin",
        is_guest=False,
    )
    app.dependency_overrides[get_current_user] = lambda: admin_user
    app.dependency_overrides[get_db] = lambda: db_session

    pool = pool_registry.get_pool("groq")
    assert pool is not None
    if not pool.keys:
        pool.add_key("test_secret_val", alias="groq#test")

    test_key = pool.keys[0]
    original_fail = test_key.fail_count
    original_cooldown = test_key.cooldown_until

    try:
        # Bench key for 300 seconds
        test_key.bench(seconds=300.0)
        assert not test_key.is_ready()

        # Insert a recorded call into db
        call_log = LLMCall(
            provider="groq",
            model="llama-3.3-70b-versatile",
            key_alias=test_key.alias,
            tokens_in=100,
            tokens_out=50,
            latency_ms=250,
            status="ok",
        )
        db_session.add(call_log)
        await db_session.commit()

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            res = await client.get("/admin/llm-status")
            assert res.status_code == 200
            data = res.json()["data"]

            groq_info = next(p for p in data if p["provider"] == "groq")
            target_key = next(k for k in groq_info["keys"] if k["key_alias"] == test_key.alias)

            assert target_key["is_ready"] is False
            assert target_key["cooling_down_seconds"] > 250.0
            assert target_key["fail_count"] > 0
            assert target_key["recent_call_count"] >= 1
            assert target_key["last_status"] == "ok"
    finally:
        test_key.fail_count = original_fail
        test_key.cooldown_until = original_cooldown
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)
