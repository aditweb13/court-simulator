"""Unit tests for security, password hashing, and auth endpoints."""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.db.models.user import User
from app.db.session import get_db
from app.main import app
from httpx import ASGITransport, AsyncClient


def test_password_hashing():
    password = "CorrectHorseBatteryStaple123"
    hashed = hash_password(password)

    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False


def test_jwt_generation_and_decoding():
    user_id = uuid.uuid4()
    token = create_access_token(subject=user_id, is_guest=False)

    payload = decode_access_token(token)
    assert payload["sub"] == str(user_id)
    assert payload["is_guest"] is False
    assert "exp" in payload
    assert "iat" in payload


@pytest.mark.asyncio
async def test_register_endpoint_success():
    mock_session = AsyncMock()
    # Mock no existing user
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    # Mock user creation
    async def mock_refresh(user):
        user.id = uuid.uuid4()
        user.created_at = datetime.now(timezone.utc)

    mock_session.refresh.side_effect = mock_refresh

    app.dependency_overrides[get_db] = lambda: mock_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {
            "email": "lawyer@verdict.court",
            "password": "StrongPassword123!",
            "display_name": "Advocate Meera",
        }
        response = await client.post("/api/v1/auth/register", json=payload)
        assert response.status_code == 201

        data = response.json()
        assert "data" in data
        assert "meta" in data
        assert data["data"]["user"]["email"] == "lawyer@verdict.court"
        assert data["data"]["user"]["display_name"] == "Advocate Meera"
        assert "access_token" in data["data"]
        assert data["data"]["token_type"] == "bearer"

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_register_conflict_email():
    mock_session = AsyncMock()
    mock_result = MagicMock()
    existing_user = User(
        id=uuid.uuid4(),
        email="existing@verdict.court",
        display_name="Existing User",
        is_guest=False,
    )
    mock_result.scalar_one_or_none.return_value = existing_user
    mock_session.execute.return_value = mock_result

    app.dependency_overrides[get_db] = lambda: mock_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {
            "email": "existing@verdict.court",
            "password": "StrongPassword123!",
            "display_name": "New User",
        }
        response = await client.post("/api/v1/auth/register", json=payload)
        assert response.status_code == 409

        data = response.json()
        assert data["error"]["code"] == "CONFLICT"

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_login_success():
    pwd = "ValidPassword123!"
    mock_session = AsyncMock()
    mock_result = MagicMock()
    existing_user = User(
        id=uuid.uuid4(),
        email="user@verdict.court",
        password_hash=hash_password(pwd),
        display_name="Registered User",
        is_guest=False,
        created_at=datetime.now(timezone.utc),
    )
    mock_result.scalar_one_or_none.return_value = existing_user
    mock_session.execute.return_value = mock_result

    app.dependency_overrides[get_db] = lambda: mock_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {
            "email": "user@verdict.court",
            "password": pwd,
        }
        response = await client.post("/api/v1/auth/login", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert "access_token" in data["data"]
        assert data["data"]["user"]["email"] == "user@verdict.court"

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_login_invalid_password():
    mock_session = AsyncMock()
    mock_result = MagicMock()
    existing_user = User(
        id=uuid.uuid4(),
        email="user@verdict.court",
        password_hash=hash_password("RealPassword123!"),
        display_name="Registered User",
        is_guest=False,
        created_at=datetime.now(timezone.utc),
    )
    mock_result.scalar_one_or_none.return_value = existing_user
    mock_session.execute.return_value = mock_result

    app.dependency_overrides[get_db] = lambda: mock_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {
            "email": "user@verdict.court",
            "password": "WrongPassword123!",
        }
        response = await client.post("/api/v1/auth/login", json=payload)
        assert response.status_code == 401

        data = response.json()
        assert data["error"]["code"] == "UNAUTHENTICATED"

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_register_validation_error():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Invalid email and too short password
        payload = {
            "email": "not-an-email",
            "password": "short",
            "display_name": "Test",
        }
        response = await client.post("/api/v1/auth/register", json=payload)
        assert response.status_code == 422

        data = response.json()
        assert data["error"]["code"] == "VALIDATION_ERROR"
        assert "details" in data["error"]
