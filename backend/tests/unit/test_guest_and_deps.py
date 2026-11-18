"""Unit tests for guest login and auth dependency."""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.security import create_access_token
from app.db.models.user import User
from app.db.session import get_db
from app.main import app


@pytest.mark.asyncio
async def test_guest_endpoint_creates_guest_user():
    mock_session = AsyncMock()

    async def mock_refresh(user):
        user.id = uuid.uuid4()
        user.created_at = datetime.now(timezone.utc)

    mock_session.refresh.side_effect = mock_refresh
    app.dependency_overrides[get_db] = lambda: mock_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/auth/guest", json={"display_name": "Juror 4"})
        assert response.status_code == 201

        data = response.json()
        assert data["data"]["user"]["is_guest"] is True
        assert data["data"]["user"]["display_name"] == "Juror 4"
        assert data["data"]["user"]["email"] is None
        assert "access_token" in data["data"]

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_me_endpoint_with_valid_token():
    user_id = uuid.uuid4()
    mock_user = User(
        id=user_id,
        email="meera@verdict.court",
        display_name="Meera",
        is_guest=False,
        created_at=datetime.now(timezone.utc),
    )

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_user
    mock_session.execute.return_value = mock_result

    app.dependency_overrides[get_db] = lambda: mock_session

    token = create_access_token(subject=user_id, is_guest=False)
    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/auth/me", headers=headers)
        assert response.status_code == 200

        data = response.json()
        assert data["data"]["id"] == str(user_id)
        assert data["data"]["display_name"] == "Meera"
        assert data["data"]["email"] == "meera@verdict.court"

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_me_endpoint_without_token():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/auth/me")
        assert response.status_code == 401

        data = response.json()
        assert data["error"]["code"] == "UNAUTHENTICATED"


@pytest.mark.asyncio
async def test_me_endpoint_with_invalid_token():
    headers = {"Authorization": "Bearer invalid.fake.token"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/auth/me", headers=headers)
        assert response.status_code == 401

        data = response.json()
        assert data["error"]["code"] == "UNAUTHENTICATED"
