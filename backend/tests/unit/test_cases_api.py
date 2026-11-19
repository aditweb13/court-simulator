"""Unit and integration tests for /cases and /cases/{id} endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_list_cases_returns_cases_in_envelope():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/cases")
        assert response.status_code == 200
        body = response.json()

        assert "data" in body
        assert "meta" in body
        assert "request_id" in body["meta"]
        assert isinstance(body["data"], list)
        assert len(body["data"]) >= 3

        # Check fields of first item
        case = body["data"][0]
        assert "id" in case
        assert "slug" in case
        assert "title" in case
        assert "charge" in case
        assert "difficulty" in case
        assert "evidence_count" in case
        assert "witness_count" in case
        assert case["evidence_count"] > 0
        assert case["witness_count"] > 0
        # Truth must NOT be exposed
        assert "truth" not in case


@pytest.mark.asyncio
async def test_list_cases_root_alias():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/cases")
        assert response.status_code == 200
        body = response.json()
        assert "data" in body
        assert isinstance(body["data"], list)
        assert len(body["data"]) >= 3


@pytest.mark.asyncio
async def test_get_case_by_slug():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/cases/state-v-malhotra-2024")
        assert response.status_code == 200
        body = response.json()

        data = body["data"]
        assert data["slug"] == "state-v-malhotra-2024"
        assert data["title"] == "State of Maharashtra v. Vikram Malhotra"
        assert len(data["evidence"]) >= 4
        assert len(data["witnesses"]) >= 3

        # Check evidence structure
        ev = data["evidence"][0]
        assert "exhibit_no" in ev
        assert "type" in ev
        assert "description" in ev
        assert "admissible" in ev

        # Check witness structure (must not leak hides or saw_event_ids)
        wit = data["witnesses"][0]
        assert "name" in wit
        assert "persona" in wit
        assert "hides" not in wit
        assert "saw_event_ids" not in wit
        assert "truth" not in data


@pytest.mark.asyncio
async def test_get_case_by_uuid():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # First get list to find UUID
        list_resp = await client.get("/api/v1/cases")
        assert list_resp.status_code == 200
        first_case = list_resp.json()["data"][0]
        case_uuid = first_case["id"]

        # Fetch by UUID
        response = await client.get(f"/api/v1/cases/{case_uuid}")
        assert response.status_code == 200
        body = response.json()
        assert body["data"]["id"] == case_uuid
        assert body["data"]["slug"] == first_case["slug"]


@pytest.mark.asyncio
async def test_get_case_not_found():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/cases/non-existent-case-slug")
        assert response.status_code == 404
        body = response.json()
        assert "error" in body
        assert body["error"]["code"] == "NOT_FOUND"
        assert "not found" in body["error"]["message"].lower()
