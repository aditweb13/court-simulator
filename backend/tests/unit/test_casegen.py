"""Unit tests for staged case generator, caching, statutory grounding, and validation."""

from __future__ import annotations

import uuid
from typing import Any, List
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.casegen import (
    CaseGenerateRequest,
    Stage1TruthOutput,
    Stage2EvidenceOutput,
    Stage3WitnessesOutput,
    generate_case,
)
from app.cases.validator import CaseValidationError
from app.db.models.user import User
from app.db.session import async_session_maker, get_db
from app.main import app
from app.rag.retriever import RetrievedChunk
from app.schemas.case import EvidenceData, TimelineEvent, WitnessData


@pytest.fixture
async def db_session():
    async with async_session_maker() as session:
        yield session


def _sample_stage1() -> Stage1TruthOutput:
    return Stage1TruthOutput(
        title="State of Maharashtra v. Rohan Mehta",
        slug="state-v-mehta-2024",
        charge="Cheating under Section 318(4) of BNS, 2023",
        cited_section="318(4)",
        culprit="Rohan Mehta",
        motive="Unlawful diversion of corporate funds into offshore shell accounts",
        summary="Rohan Mehta forged board resolutions and siphoned 10 crore INR from Apex Tech.",
        timeline=[
            TimelineEvent(
                id=0,
                time="2024-08-10T11:00:00",
                description="Rohan Mehta attends secret meeting at Apex Tech HQ.",
                location="Apex Tech Boardroom, Mumbai",
                actors=["Rohan Mehta", "Pooja Desai"],
            ),
            TimelineEvent(
                id=1,
                time="2024-08-12T15:30:00",
                description="Rohan Mehta transmits forged resolution to Reserve Bank.",
                location="Private Office, Bandra",
                actors=["Rohan Mehta"],
            ),
            TimelineEvent(
                id=2,
                time="2024-08-15T09:00:00",
                description="Funds credited to offshore entity; whistleblower flags irregularity.",
                location="Cyber Cell, Mumbai",
                actors=["Inspector Rao", "Pooja Desai"],
            ),
        ],
    )


def _sample_stage2() -> Stage2EvidenceOutput:
    return Stage2EvidenceOutput(
        evidence=[
            EvidenceData(
                exhibit_no="Exhibit P-1",
                type="documentary",
                description="Forged board resolution dated 12 August 2024.",
                admissible=True,
                reason_inadmissible=None,
            ),
            EvidenceData(
                exhibit_no="Exhibit P-2",
                type="documentary",
                description="Uncertified CCTV server log printout without certificate.",
                admissible=False,
                reason_inadmissible="Inadmissible under Section 63 of BSA for lack of certificate.",
            ),
        ]
    )


def _sample_stage3() -> Stage3WitnessesOutput:
    return Stage3WitnessesOutput(
        witnesses=[
            WitnessData(
                name="Pooja Desai",
                saw_event_ids=[0, 2],
                reliability=0.9,
                hides=["Was promised promotion by Rohan Mehta"],
                persona={"role": "Whistleblower", "vocal": "nervous but precise"},
            ),
            WitnessData(
                name="Inspector Rao",
                saw_event_ids=[2],
                reliability=0.95,
                hides=[],
                persona={"role": "Investigating Officer", "vocal": "authoritative"},
            ),
        ]
    )


def _mock_chunk(section_no: str = "318(4)") -> RetrievedChunk:
    return RetrievedChunk(
        id=101,
        act="Bharatiya Nyaya Sanhita, 2023",
        section_no=section_no,
        title="Cheating and dishonestly inducing delivery of property",
        body="Whoever cheats and thereby dishonestly induces the person deceived...",
        domain="statute",
        audience=["judge"],
        score=0.95,
    )


@pytest.mark.asyncio
async def test_casegen_successful_flow(db_session: AsyncSession):
    """Test full 3-stage case generation and persistence."""
    req = CaseGenerateRequest(topic="corporate fraud and money diversion", difficulty=2)

    s1 = _sample_stage1()
    s2 = _sample_stage2()
    s3 = _sample_stage3()

    async def fake_chat(tier: str, messages: List[Any], response_model: Any = None, **kwargs):
        if response_model is Stage1TruthOutput:
            return s1
        elif response_model is Stage2EvidenceOutput:
            return s2
        elif response_model is Stage3WitnessesOutput:
            return s3
        raise ValueError(f"Unexpected response_model: {response_model}")

    with (
        patch(
            "app.casegen.generator.retrieve", new=AsyncMock(return_value=[_mock_chunk("318(4)")])
        ),
        patch("app.casegen.generator.chat", side_effect=fake_chat),
    ):
        persisted = await generate_case(db=db_session, request=req)

        assert persisted.id is not None
        assert persisted.source == "generated"
        assert persisted.slug.startswith("gen-")
        assert len(persisted.evidence) == 2
        assert len(persisted.witnesses) == 2
        assert any(not ev.admissible for ev in persisted.evidence)


@pytest.mark.asyncio
async def test_casegen_cache_hit_makes_no_llm_call(db_session: AsyncSession):
    """Test that requesting an already generated hash returns cached case without calling LLM."""
    req = CaseGenerateRequest(topic="intellectual property theft", difficulty=1)

    s1 = _sample_stage1()
    s2 = _sample_stage2()
    s3 = _sample_stage3()

    async def fake_chat(tier: str, messages: List[Any], response_model: Any = None, **kwargs):
        if response_model is Stage1TruthOutput:
            return s1
        elif response_model is Stage2EvidenceOutput:
            return s2
        elif response_model is Stage3WitnessesOutput:
            return s3
        raise ValueError(f"Unexpected: {response_model}")

    # First call: populates cache
    with (
        patch(
            "app.casegen.generator.retrieve", new=AsyncMock(return_value=[_mock_chunk("318(4)")])
        ),
        patch("app.casegen.generator.chat", side_effect=fake_chat),
    ):
        c1 = await generate_case(db=db_session, request=req)
        assert c1 is not None

    # Second call: must hit cache and NOT invoke chat
    llm_spy = AsyncMock(side_effect=RuntimeError("LLM should not be called on cache hit!"))
    with patch("app.casegen.generator.chat", new=llm_spy):
        c2 = await generate_case(db=db_session, request=req)
        assert c2.id == c1.id
        assert c2.slug == c1.slug
        llm_spy.assert_not_called()


@pytest.mark.asyncio
async def test_casegen_rejected_if_statutory_section_not_retrieved(db_session: AsyncSession):
    """Test rejection if cited statutory section was not among retrieved legal chunks."""
    req = CaseGenerateRequest(topic="culpable homicide", difficulty=3)

    s1 = _sample_stage1()
    s1.cited_section = "103(1)"  # Murder, but retriever will return only 318(4)

    with (
        patch(
            "app.casegen.generator.retrieve", new=AsyncMock(return_value=[_mock_chunk("318(4)")])
        ),
        patch("app.casegen.generator.chat", new=AsyncMock(return_value=s1)),
    ):
        with pytest.raises(CaseValidationError, match="Statutory citation violation"):
            await generate_case(db=db_session, request=req)


@pytest.mark.asyncio
async def test_casegen_rejected_if_culprit_not_in_timeline(db_session: AsyncSession):
    """Test rejection if the culprit never appears in the timeline events."""
    req = CaseGenerateRequest(topic="insider trading", difficulty=1)

    s1 = _sample_stage1()
    s1.culprit = "Phantom Suspect"  # Not present in any actor or description
    s2 = _sample_stage2()
    s3 = _sample_stage3()

    async def fake_chat(tier: str, messages: List[Any], response_model: Any = None, **kwargs):
        if response_model is Stage1TruthOutput:
            return s1
        elif response_model is Stage2EvidenceOutput:
            return s2
        elif response_model is Stage3WitnessesOutput:
            return s3

    with (
        patch(
            "app.casegen.generator.retrieve", new=AsyncMock(return_value=[_mock_chunk("318(4)")])
        ),
        patch("app.casegen.generator.chat", side_effect=fake_chat),
    ):
        with pytest.raises(CaseValidationError, match="must appear in the timeline events"):
            await generate_case(db=db_session, request=req)


@pytest.mark.asyncio
async def test_casegen_rejected_if_date_before_bns_effective_date(db_session: AsyncSession):
    """Test rejection if an event date precedes BNS enactment date (2024-07-01)."""
    req = CaseGenerateRequest(topic="wire fraud", difficulty=2)

    s1 = _sample_stage1()
    s1.timeline[0].time = "2024-05-15T10:00:00"  # Pre-BNS date
    s2 = _sample_stage2()
    s3 = _sample_stage3()

    async def fake_chat(tier: str, messages: List[Any], response_model: Any = None, **kwargs):
        if response_model is Stage1TruthOutput:
            return s1
        elif response_model is Stage2EvidenceOutput:
            return s2
        elif response_model is Stage3WitnessesOutput:
            return s3

    with (
        patch(
            "app.casegen.generator.retrieve", new=AsyncMock(return_value=[_mock_chunk("318(4)")])
        ),
        patch("app.casegen.generator.chat", side_effect=fake_chat),
    ):
        with pytest.raises(CaseValidationError, match="before BNS effective date"):
            await generate_case(db=db_session, request=req)


@pytest.mark.asyncio
async def test_casegen_api_endpoint_auth_and_daily_cap(db_session: AsyncSession):
    """Test POST /cases/generate authentication and daily limit enforcement."""
    mock_user = User(
        id=uuid.uuid4(),
        email="testlawyer@example.com",
        display_name="Test Lawyer",
        is_guest=False,
    )

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        s1 = _sample_stage1()
        s2 = _sample_stage2()
        s3 = _sample_stage3()

        async def fake_chat(tier: str, messages: List[Any], response_model: Any = None, **kwargs):
            if response_model is Stage1TruthOutput:
                return s1
            elif response_model is Stage2EvidenceOutput:
                return s2
            elif response_model is Stage3WitnessesOutput:
                return s3

        with (
            patch(
                "app.casegen.generator.retrieve",
                new=AsyncMock(return_value=[_mock_chunk("318(4)")]),
            ),
            patch("app.casegen.generator.chat", side_effect=fake_chat),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                # 1. Successful generation
                res = await client.post(
                    "/api/v1/cases/generate",
                    json={"topic": "financial scam via fictitious invoices", "difficulty": 2},
                )
                assert res.status_code == 201
                body = res.json()
                assert "data" in body
                assert body["data"]["source"] == "generated"

                # 2. Daily limit exhaustion: simulate exceeding cap
                import datetime

                from app.api.v1.cases import _user_generation_history
                from app.config import settings

                now = datetime.datetime.now(datetime.timezone.utc)
                _user_generation_history[mock_user.id] = [now] * settings.casegen_daily_user_cap

                res_limited = await client.post(
                    "/api/v1/cases/generate",
                    json={"topic": "another case topic", "difficulty": 2},
                )
                assert res_limited.status_code == 429
                err = res_limited.json()
                assert err["error"]["code"] == "RATE_LIMITED"
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)
