import pytest
from app.main import app
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_health_check_returns_ok_in_envelope():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()

        assert "data" in data
        assert "meta" in data
        assert data["data"] == {"status": "ok"}
        assert "request_id" in data["meta"]
        assert response.headers.get("X-Request-ID") == data["meta"]["request_id"]


@pytest.mark.asyncio
async def test_api_v1_health_check():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["data"] == {"status": "ok"}


@pytest.mark.asyncio
async def test_404_error_envelope():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/non-existent-route")
        assert response.status_code == 404
        data = response.json()
        assert "error" in data
        assert "meta" in data
        assert data["error"]["code"] == "NOT_FOUND"
        assert "request_id" in data["meta"]
        assert response.headers.get("X-Request-ID") == data["meta"]["request_id"]
