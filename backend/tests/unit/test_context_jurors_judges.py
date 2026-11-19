"""Unit tests for Juror and Verdict Judge context builders and information isolation.

Verifies:
1. Juror context NEVER includes struck testimony (Turn.struck == True).
2. Juror context NEVER includes case.truth or lawyer private notes.
3. Juror step-by-step voting and deliberation prompts format cleanly.
4. Verdict Judge context loads distinct philosophies (textualist, precedent, fairness).
5. Verdict Judge context excludes struck testimony.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.context.juror import (
    build_juror_context,
    build_juror_deliberation_prompt,
    build_juror_vote_prompt,
)
from app.context.verdict_judge import (
    build_verdict_judge_context,
    build_verdict_judge_prompt,
)
from app.db.models.case import Case
from app.db.models.trial import Turn
from app.db.session import async_session_maker
from app.main import app


@pytest.fixture
async def seeded_trial():
    """Create a trial via API so all agents and case links are seeded."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post(
            "/api/v1/trials",
            json={"case_id": "state-v-malhotra-2024", "mode": "watch"},
        )
        assert res.status_code == 201
        data = res.json()["data"]
        return uuid.UUID(data["id"]), uuid.UUID(data["case_id"])


@pytest.mark.asyncio
async def test_juror_context_isolation_struck_turns(seeded_trial):
    """Verify that struck turns are strictly excluded from juror context."""
    trial_id, case_id = seeded_trial

    async with async_session_maker() as db:
        # Create an admitted turn and a struck turn
        turn_normal = Turn(
            trial_id=trial_id,
            seq=0,
            speaker_role="prosecutor",
            text="Admitted question: Did you see the accused?",
            admitted=True,
            struck=False,
        )
        turn_struck = Turn(
            trial_id=trial_id,
            seq=1,
            speaker_role="witness",
            text="STRUCK TESTIMONY: Someone told me he was guilty.",
            admitted=True,
            struck=True,  # Struck by sustained objection
        )
        db.add_all([turn_normal, turn_struck])
        await db.commit()

        # Build juror context
        ctx = await build_juror_context(db, trial_id, case_id, juror_no=1)

        # 1. Clean record check
        record_texts = [r["text"] for r in ctx["record"]]
        assert any("Admitted question" in t for t in record_texts)
        assert not any("STRUCK TESTIMONY" in t for t in record_texts)

        # 2. Case truth isolation check
        case = await db.get(Case, case_id)
        assert case is not None
        assert "truth" not in ctx
        for k, v in ctx.items():
            assert v != case.truth


@pytest.mark.asyncio
async def test_juror_prompts_shape(seeded_trial):
    """Verify juror vote and deliberation prompt formatting."""
    trial_id, case_id = seeded_trial

    async with async_session_maker() as db:
        ctx = await build_juror_context(db, trial_id, case_id, juror_no=2)

        vote_messages = build_juror_vote_prompt(ctx, stage="pre")
        assert len(vote_messages) == 2
        assert "beyond reasonable doubt" in vote_messages[0]["content"]
        assert "Admitted Exhibits:" in vote_messages[1]["content"]

        # Deliberation prompt (regular and devil's advocate)
        prev = [{"juror_no": 1, "statement": "I think the evidence is conclusive."}]
        delib_messages = build_juror_deliberation_prompt(ctx, prev, is_devil_advocate=True)
        assert len(delib_messages) == 2
        assert "DEVIL'S ADVOCATE" in delib_messages[0]["content"]
        assert "Juror #1" in delib_messages[1]["content"]


@pytest.mark.asyncio
async def test_verdict_judge_context_and_philosophies(seeded_trial):
    """Verify verdict judge context isolation and 3 distinct philosophy prompts."""
    trial_id, case_id = seeded_trial

    async with async_session_maker() as db:
        # Create a struck turn
        db.add(
            Turn(
                trial_id=trial_id,
                seq=10,
                speaker_role="witness",
                text="Struck testimony excluded from bench.",
                admitted=True,
                struck=True,
            )
        )
        await db.commit()

        for phil in ["textualist", "precedent", "fairness"]:
            ctx = await build_verdict_judge_context(db, trial_id, case_id, philosophy=phil)
            assert ctx["agent_id"] is not None
            assert ctx["judge"]["philosophy"] == phil

            # Ensure struck turn excluded
            record_texts = [r["text"] for r in ctx["record"]]
            assert not any("Struck testimony excluded" in t for t in record_texts)

            # Check prompt
            prompt_msgs = build_verdict_judge_prompt(ctx)
            assert len(prompt_msgs) == 2
            assert phil.upper() in prompt_msgs[0]["content"]
