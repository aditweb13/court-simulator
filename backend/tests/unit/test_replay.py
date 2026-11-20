"""Unit tests for the trial replay SSE streaming endpoint."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.db.models.trial import Trial, Turn
from app.main import create_app
from httpx import ASGITransport, AsyncClient


@pytest.fixture
def test_app():
    return create_app()


@pytest.mark.asyncio
async def test_replay_trial_not_found(test_app):
    """GET /trials/{id}/replay returns 404 when trial does not exist."""
    fake_id = uuid.uuid4()
    async with AsyncClient(
        transport=ASGITransport(app=test_app), base_url="http://test"
    ) as ac:
        response = await ac.get(f"/api/v1/trials/{fake_id}/replay")
        assert response.status_code == 404
        data = response.json()
        assert data["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_replay_trial_streams_turns(test_app):
    """GET /trials/{id}/replay streams SSE events (state, line, finished)."""
    trial_id = uuid.uuid4()

    mock_trial = MagicMock(spec=Trial)
    mock_trial.id = trial_id

    mock_turn_1 = MagicMock(spec=Turn)
    mock_turn_1.id = uuid.uuid4()
    mock_turn_1.seq = 1
    mock_turn_1.speaker_role = "judge"
    mock_turn_1.text = "Court is in session."
    mock_turn_1.action = "gavel"
    mock_turn_1.emotion = "neutral"
    mock_turn_1.camera = "judge"
    mock_turn_1.struck = False
    mock_turn_1.objection = None

    mock_turn_2 = MagicMock(spec=Turn)
    mock_turn_2.id = uuid.uuid4()
    mock_turn_2.seq = 2
    mock_turn_2.speaker_role = "prosecutor"
    mock_turn_2.text = "We call our first witness."
    mock_turn_2.action = "stand"
    mock_turn_2.emotion = "firm"
    mock_turn_2.camera = "close"
    mock_turn_2.struck = False
    mock_turn_2.objection = None

    mock_db = AsyncMock()

    # db.get(Trial, trial_id) -> mock_trial; db.get(Verdict, trial_id) -> None
    async def mock_get(entity, ident):
        if entity == Trial and ident == trial_id:
            return mock_trial
        return None

    mock_db.get = mock_get

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_turn_1, mock_turn_2]
    mock_db.execute.return_value = mock_result

    from app.db.session import get_db

    test_app.dependency_overrides[get_db] = lambda: mock_db

    try:
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as ac:
            response = await ac.get(f"/api/v1/trials/{trial_id}/replay?instant=true")
            assert response.status_code == 200
            assert "text/event-stream" in response.headers["content-type"]

            content = response.text
            assert "event: state" in content
            assert '"SETUP"' in content
            assert "event: line" in content
            assert "Court is in session." in content
            assert "We call our first witness." in content
            assert '"FINISHED"' in content
    finally:
        test_app.dependency_overrides.pop(get_db, None)

