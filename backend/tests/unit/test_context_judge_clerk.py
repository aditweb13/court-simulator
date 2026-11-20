"""Unit tests for judge and clerk context filters and prompt generators.

Tests information isolation, evidence admissibility filtering, and prompt shapes.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from app.context.clerk import build_clerk_context, build_clerk_opening_prompt
from app.context.judge import (
    build_judge_closing_prompt,
    build_judge_context,
    build_judge_opening_prompt,
)
from app.db.models.case import Case
from app.db.session import async_session_maker
from app.main import app
from app.rag.retriever import RetrievedChunk
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.orm import selectinload


@pytest.fixture
async def seeded_trial():
    """Create a trial via the API so all agents and case links are seeded."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post(
            "/api/v1/trials",
            json={"case_id": "state-v-malhotra-2024", "mode": "watch"},
        )
        assert res.status_code == 201
        data = res.json()["data"]
        return uuid.UUID(data["id"]), uuid.UUID(data["case_id"])


@pytest.mark.asyncio
async def test_judge_context_contains_admitted_evidence_and_public_facts(seeded_trial):
    """Judge context must contain public case details and only admissible evidence."""
    trial_id, case_id = seeded_trial

    async with async_session_maker() as db:
        ctx = await build_judge_context(db, trial_id, case_id)

        assert "case_title" in ctx
        assert "State of Maharashtra v. Vikram Malhotra" in ctx["case_title"]
        assert "charge" in ctx
        assert "103(1)" in ctx["charge"]
        assert "admitted_evidence" in ctx

        # Check evidence filtering: all items in ctx must have admissible exhibits
        stmt = select(Case).options(selectinload(Case.evidence)).where(Case.id == case_id)
        res = await db.execute(stmt)
        case_row = res.scalar_one_or_none()
        assert case_row is not None

        admitted_in_ctx = {ev["exhibit_no"] for ev in ctx["admitted_evidence"]}
        # In case 001, exhibit P-3 (unregistered diary) is inadmissible
        # Admissible exhibits should be present, inadmissible should not be in admitted_evidence
        for ev in case_row.evidence:
            if ev.admissible:
                assert ev.exhibit_no in admitted_in_ctx
            else:
                assert ev.exhibit_no not in admitted_in_ctx


@pytest.mark.asyncio
async def test_judge_context_isolation_no_hidden_truth_leaked(seeded_trial):
    """Isolation check: Judge context must never contain hidden ground truth."""
    trial_id, case_id = seeded_trial

    async with async_session_maker() as db:
        case_row = await db.get(Case, case_id)
        assert case_row is not None
        truth = case_row.truth
        timeline = truth.get("timeline", [])

        ctx = await build_judge_context(db, trial_id, case_id)

        # Context keys must never contain 'truth' or 'timeline'
        assert "truth" not in ctx
        assert "timeline" not in ctx

        # Verify none of the secret observation facts or timeline entries leaked
        prompt = build_judge_opening_prompt(ctx)
        full_prompt_text = " ".join(m["content"] for m in prompt)

        for event in timeline:
            observation = event.get("observation", "")
            if len(observation) > 20:
                # Secret observation must not appear in the judge prompt
                assert observation not in full_prompt_text


@pytest.mark.asyncio
async def test_judge_opening_and_closing_prompts(seeded_trial):
    """Verify prompt formatting for judge opening and closing statements."""
    trial_id, case_id = seeded_trial

    fake_chunks = [
        RetrievedChunk(
            id=1,
            act="BNS",
            section_no="103(1)",
            title="Punishment for murder",
            body="Whoever commits murder shall be punished with death or imprisonment for life.",
            domain="statute",
            audience=["judge", "lawyer"],
            score=0.95,
        )
    ]

    with patch("app.context.judge.retrieve", new_callable=AsyncMock) as mock_ret:
        mock_ret.return_value = fake_chunks
        async with async_session_maker() as db:
            ctx = await build_judge_context(db, trial_id, case_id)

            opening_msgs = build_judge_opening_prompt(
                ctx, {"title": "Sessions Judge", "style": "procedural"}
            )
            assert len(opening_msgs) == 2
            assert opening_msgs[0]["role"] == "system"
            assert "Sessions Judge" in opening_msgs[0]["content"]
            assert opening_msgs[1]["role"] == "user"
            assert "103(1)" in opening_msgs[1]["content"]

            closing_msgs = build_judge_closing_prompt(ctx, {"title": "Sessions Judge"})
            assert len(closing_msgs) == 2
            assert "reasonable doubt" in closing_msgs[0]["content"]
            assert ctx["case_title"] in closing_msgs[1]["content"]


@pytest.mark.asyncio
async def test_clerk_context_and_prompt(seeded_trial):
    """Verify clerk context contains case details and accused, but no secret truth."""
    trial_id, case_id = seeded_trial

    async with async_session_maker() as db:
        ctx = await build_clerk_context(db, trial_id, case_id)

        assert "case_title" in ctx
        assert "charge" in ctx
        assert "defendant_name" in ctx
        assert "truth" not in ctx
        assert "timeline" not in ctx

        prompt = build_clerk_opening_prompt(ctx, {"style": "formal"})
        assert len(prompt) == 2
        assert prompt[0]["role"] == "system"
        assert "Court Reader and Clerk" in prompt[0]["content"]
        assert prompt[1]["role"] == "user"
        assert ctx["case_title"] in prompt[1]["content"]
        assert ctx["charge"] in prompt[1]["content"]
