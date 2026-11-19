"""Unit and integration tests for /trials endpoints (POST /trials and GET /trials/{id})."""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_create_trial_default_config():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {
            "case_id": "state-v-malhotra-2024",
            "mode": "watch",
        }
        response = await client.post("/api/v1/trials", json=payload)
        assert response.status_code == 201
        body = response.json()

        assert "data" in body
        assert "meta" in body
        data = body["data"]

        assert "id" in data
        assert data["case_slug"] == "state-v-malhotra-2024"
        assert data["case_title"] == "State of Maharashtra v. Vikram Malhotra"
        assert data["state"] == "SETUP"
        assert data["mode"] == "watch"
        assert data["turns_count"] == 0

        # Check config defaults
        config = data["config"]
        assert config["juror_count"] == 3
        assert config["rounds"] == 1
        assert config["threshold"] == 0.75
        assert config["hung_band"] == 0.05

        # Check seeded agents
        agents = data["agents"]
        roles = [ag["role"] for ag in agents]
        assert "judge" in roles
        assert "clerk" in roles
        assert "prosecutor" in roles
        assert "defense" in roles
        assert "defendant" in roles
        assert roles.count("witness") == 3
        assert roles.count("juror") == 3
        assert roles.count("verdict_judge") == 3


@pytest.mark.asyncio
async def test_create_trial_custom_config():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {
            "case_id": "state-v-kapoor-2024",
            "mode": "lawyer",
            "human_role": "defense",
            "config": {
                "juror_count": 5,
                "rounds": 2,
                "threshold": 0.80,
                "hung_band": 0.04,
            },
        }
        response = await client.post("/api/v1/trials", json=payload)
        assert response.status_code == 201
        data = response.json()["data"]

        assert data["mode"] == "lawyer"
        assert data["human_role"] == "defense"
        assert data["config"]["juror_count"] == 5
        assert data["config"]["rounds"] == 2
        assert data["config"]["threshold"] == 0.80
        assert data["config"]["hung_band"] == 0.04

        roles = [ag["role"] for ag in data["agents"]]
        assert roles.count("juror") == 5


@pytest.mark.asyncio
async def test_create_trial_case_not_found():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {
            "case_id": "non-existent-case-slug",
            "mode": "watch",
        }
        response = await client.post("/api/v1/trials", json=payload)
        assert response.status_code == 404
        body = response.json()
        assert body["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_get_trial_by_id():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create trial first
        create_resp = await client.post(
            "/api/v1/trials",
            json={"case_id": "state-v-singh-2024", "mode": "watch"},
        )
        assert create_resp.status_code == 201
        trial_id = create_resp.json()["data"]["id"]

        # Fetch trial
        get_resp = await client.get(f"/api/v1/trials/{trial_id}")
        assert get_resp.status_code == 200
        data = get_resp.json()["data"]

        assert data["id"] == trial_id
        assert data["case_slug"] == "state-v-singh-2024"
        assert data["case_title"] == "State of Punjab v. Harpreet Singh"
        assert len(data["agents"]) >= 10
        assert data["turns_count"] == 0


@pytest.mark.asyncio
async def test_get_trial_not_found():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        random_id = str(uuid.uuid4())
        response = await client.get(f"/api/v1/trials/{random_id}")
        assert response.status_code == 404
        body = response.json()
        assert body["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_trials_root_alias():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/trials",
            json={"case_id": "state-v-malhotra-2024", "mode": "watch"},
        )
        assert response.status_code == 201
        assert response.json()["data"]["case_slug"] == "state-v-malhotra-2024"
