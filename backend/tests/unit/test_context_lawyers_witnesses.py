"""Unit tests for prosecutor, defense, and witness context filters and prompts.

Validates information isolation:
- Prosecutor and Defense never see `case.truth`
- Witness only receives their `saw_event_ids` memory slice
- Struck turns are omitted from lawyer context records
"""

from __future__ import annotations

import uuid

import pytest
from app.context.defense import (
    build_defense_closing_prompt,
    build_defense_context,
    build_defense_examination_prompt,
)
from app.context.prosecutor import (
    build_prosecutor_closing_prompt,
    build_prosecutor_context,
    build_prosecutor_examination_prompt,
    build_prosecutor_objection_prompt,
)
from app.context.witness import build_witness_answer_prompt, build_witness_context
from app.db.models.trial import Turn
from app.db.session import async_session_maker
from app.main import app
from httpx import ASGITransport, AsyncClient


@pytest.fixture
async def seeded_trial():
    """Create a trial via the API so case, agents, and witness memories are seeded."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post(
            "/api/v1/trials",
            json={"case_id": "state-v-malhotra-2024", "mode": "watch"},
        )
        assert res.status_code == 201
        data = res.json()["data"]
        return uuid.UUID(data["id"]), uuid.UUID(data["case_id"])


@pytest.mark.asyncio
async def test_prosecutor_context_isolation_and_private_notes(seeded_trial):
    """Prosecutor context contains case facts, evidence, private notes, and omits case.truth."""
    trial_id, case_id = seeded_trial

    async with async_session_maker() as db:
        # Add an admitted turn and a struck turn to verify struck turn exclusion
        turn_normal = Turn(
            trial_id=trial_id,
            seq=10,
            speaker_role="clerk",
            text="Admitted proceeding turn.",
            admitted=True,
            struck=False,
        )
        turn_struck = Turn(
            trial_id=trial_id,
            seq=11,
            speaker_role="witness",
            text="Hearsay testimony that was struck.",
            admitted=True,
            struck=True,
        )
        db.add_all([turn_normal, turn_struck])
        await db.commit()

        ctx = await build_prosecutor_context(db, trial_id, case_id, witness_name="Sunita Bai")

        # 1. Must contain public facts
        assert "State of Maharashtra v. Vikram Malhotra" in ctx["case_title"]
        assert "103(1)" in ctx["charge"]

        # 2. Must contain private notes
        assert len(ctx["private_notes"]) >= 3
        assert any("Burden of Proof" in n for n in ctx["private_notes"])
        assert any("Sunita Bai" in n for n in ctx["private_notes"])

        # 3. Admitted non-struck turns only
        turn_texts = [r["text"] for r in ctx["record"]]
        assert "Admitted proceeding turn." in turn_texts
        assert "Hearsay testimony that was struck." not in turn_texts

        # 4. STRICT ISOLATION: No case.truth
        assert "truth" not in ctx
        assert "timeline" not in ctx


@pytest.mark.asyncio
async def test_defense_context_isolation_and_persona(seeded_trial):
    """Defense context contains case facts, defendant info, private notes, and omits case.truth."""
    trial_id, case_id = seeded_trial

    async with async_session_maker() as db:
        ctx = await build_defense_context(db, trial_id, case_id, witness_name="Sunita Bai")

        assert "case_title" in ctx
        assert "defendant" in ctx
        assert "name" in ctx["defendant"]

        # Private notes
        assert any("Presumption of Innocence" in n for n in ctx["private_notes"])
        assert any("Sunita Bai" in n for n in ctx["private_notes"])

        # STRICT ISOLATION: No case.truth
        assert "truth" not in ctx


@pytest.mark.asyncio
async def test_witness_context_isolation(seeded_trial):
    """Witness context contains memories, demeanor, and hides, but zero case.truth."""
    trial_id, _ = seeded_trial

    async with async_session_maker() as db:
        ctx = await build_witness_context(
            db,
            trial_id,
            witness_name="Sunita Bai",
            question_text="Did you see the accused at the godown?",
        )

        assert ctx["name"] == "Sunita Bai"
        assert ctx["question"] == "Did you see the accused at the godown?"
        assert isinstance(ctx["memories"], list)
        assert len(ctx["memories"]) > 0

        # STRICT ISOLATION
        assert "truth" not in ctx
        assert "statutes" not in ctx


def test_prompts_shape():
    """Verify prompt formatting for examination, objections, and closings."""
    ctx = {
        "case_title": "State v. Test",
        "charge": "BNS 103(1)",
        "jurisdiction": "Mumbai",
        "private_notes": ["Prove motive."],
        "evidence": [{"exhibit_no": "A-1", "type": "physical", "description": "Knife"}],
        "record": [{"speaker": "clerk", "text": "Court in session."}],
        "defendant": {"name": "Vikram"},
        "name": "Dr. Nair",
        "memories": ["I performed the post-mortem."],
        "question": "What was the cause of death?",
    }

    # Prosecutor examination
    p_exam = build_prosecutor_examination_prompt(ctx, "Dr. Nair", "direct")
    assert len(p_exam) == 2
    assert "PROHIBITED" in p_exam[1]["content"]  # Leading prohibited in direct

    p_cross = build_prosecutor_examination_prompt(ctx, "Dr. Nair", "cross")
    assert "PERMITTED" in p_cross[1]["content"]  # Leading permitted in cross

    # Objection prompt
    p_obj = build_prosecutor_objection_prompt(ctx, "Isn't it true you hated him?", "direct")
    assert len(p_obj) == 2
    assert "BSA 2023" in p_obj[0]["content"]

    # Defense examination
    d_exam = build_defense_examination_prompt(ctx, "Dr. Nair", "cross")
    assert len(d_exam) == 2

    # Closing prompts
    p_close = build_prosecutor_closing_prompt(ctx)
    assert len(p_close) == 2

    d_close = build_defense_closing_prompt(ctx)
    assert len(d_close) == 2

    # Witness answer prompt
    w_prompt = build_witness_answer_prompt(ctx)
    assert len(w_prompt) == 2
    assert "post-mortem" in w_prompt[0]["content"]
