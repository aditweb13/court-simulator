"""Trials REST routes for creating and querying trial simulations."""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agents.witness_memory import build_witness_memory
from app.api.deps import get_optional_current_user
from app.config import settings
from app.core.errors import AppException, ErrorCode, get_request_id
from app.db.models.case import Case
from app.db.models.trial import Agent, Trial, Turn, Verdict, Vote
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.envelope import Meta, SuccessResponse
from app.schemas.trial import (
    AgentSummary,
    HumanActionRequest,
    TrialCreate,
    TrialDetail,
    TurnSummary,
    VerdictDetail,
    VerdictVoteDetail,
)
from app.voting import calculate_bns_sentence_range

router = APIRouter(prefix="/trials", tags=["trials"])


JUROR_PERSONAS = [
    {
        "style": "skeptical",
        "description": "Demands strong physical corroboration; distrusts emotional appeals.",
    },
    {
        "style": "empathetic",
        "description": "Attentive to witness stress and human motivations; seeks fair justice.",
    },
    {
        "style": "procedural",
        "description": "Focuses strictly on statutory compliance and chain of custody rules.",
    },
    {
        "style": "statistical",
        "description": "Evaluates probability of events and forensic reliability metrics.",
    },
]


def _build_default_trial_config() -> Dict[str, Any]:
    juror_count = settings.default_juror_count if settings.dev_mode else 7
    rounds = settings.default_deliberation_rounds if settings.dev_mode else 3
    return {
        "juror_count": juror_count,
        "rounds": rounds,
        "threshold": 0.75,
        "hung_band": 0.05,
    }


def _seed_trial_agents(
    case: Case,
    config: Dict[str, Any],
    custom_juror_personas: Optional[List[Dict[str, Any]]] = None,
) -> List[Agent]:
    agents: List[Agent] = []

    # 1. Judge
    agents.append(
        Agent(
            role="judge",
            tier="strong",
            persona={
                "style": "procedural",
                "temperament": "neutral",
                "title": "Presiding Sessions Judge",
            },
            memory=[],
        )
    )

    # 2. Clerk
    agents.append(
        Agent(
            role="clerk",
            tier="mid",
            persona={"style": "formal", "function": "Court Reader & Officer"},
            memory=[],
        )
    )

    # 3. Prosecutor
    agents.append(
        Agent(
            role="prosecutor",
            tier="strong",
            persona={
                "style": "adversarial",
                "tenor": "assertive",
                "goal": "Prove guilt beyond reasonable doubt",
            },
            memory=[],
        )
    )

    # 4. Defense Counsel
    agents.append(
        Agent(
            role="defense",
            tier="strong",
            persona={
                "style": "adversarial",
                "tenor": "vigilant",
                "goal": "Protect accused rights and reveal reasonable doubt",
            },
            memory=[],
        )
    )

    # 5. Defendant
    defendant_name = "The Accused"
    if isinstance(case.truth, dict) and "culprit" in case.truth:
        defendant_name = str(case.truth["culprit"])
    agents.append(
        Agent(
            role="defendant",
            tier="mid",
            persona={"name": defendant_name, "demeanor": "Anxious", "status": "Under Trial"},
            memory=[],
        )
    )

    # 6. Witnesses
    timeline = case.truth.get("timeline", []) if isinstance(case.truth, dict) else []
    for w in case.witnesses:
        w_memory = build_witness_memory(w, timeline)
        agents.append(
            Agent(
                role="witness",
                tier="mid",
                persona={"name": w.name, **(w.persona or {})},
                memory=[m.__dict__ for m in w_memory.memories],
            )
        )

    # 7. Jurors
    juror_count = int(config.get("juror_count", 3))
    personas_source = custom_juror_personas or JUROR_PERSONAS
    for i in range(1, juror_count + 1):
        persona_template = personas_source[(i - 1) % len(personas_source)]
        style = persona_template.get("reasoning_style") or persona_template.get("style", "balanced")
        traits = persona_template.get("traits") or persona_template.get("description", "")
        occupation = persona_template.get("occupation")
        persona_dict: Dict[str, Any] = {
            "juror_no": i,
            "reasoning_style": style,
            "traits": traits,
        }
        if occupation:
            persona_dict["occupation"] = occupation
        agents.append(
            Agent(
                role="juror",
                tier="small",
                persona=persona_dict,
                memory=[],
            )
        )

    # 8. Verdict Judges (3 judicial philosophies)
    verdict_judge_philosophies = [
        (
            "textualist",
            "Strict statutory adherence and literal interpretation of enacted penal texts",
        ),
        (
            "precedent",
            "Doctrinal consistency rooted in landmark Supreme Court precedents and ratio decidendi",
        ),
        (
            "fairness",
            "Substantive justice, constitutional fundamental rights, and equitable fairness",
        ),
    ]
    for philosophy, desc in verdict_judge_philosophies:
        agents.append(
            Agent(
                role="verdict_judge",
                tier="strong",
                persona={"philosophy": philosophy, "orientation": desc},
                memory=[],
            )
        )

    return agents


@router.post("", response_model=SuccessResponse[TrialDetail], status_code=status.HTTP_201_CREATED)
async def create_trial(
    body: TrialCreate,
    request: Request,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[TrialDetail]:
    req_id = get_request_id(request)

    # 1. Look up Case
    stmt = select(Case).options(selectinload(Case.witnesses))
    try:
        parsed_uuid = uuid.UUID(body.case_id)
        stmt = stmt.where(Case.id == parsed_uuid)
    except ValueError:
        stmt = stmt.where(Case.slug == body.case_id)

    result = await db.execute(stmt)
    case_row = result.scalar_one_or_none()
    if case_row is None:
        raise AppException(
            code=ErrorCode.NOT_FOUND,
            message=f"Case '{body.case_id}' not found",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    # 2. Prepare Config
    merged_config = _build_default_trial_config()
    if body.config is not None:
        merged_config.update(body.config.model_dump())

    # 3. Create Trial
    trial_row = Trial(
        case_id=case_row.id,
        user_id=current_user.id if current_user else None,
        mode=body.mode,
        human_role=body.human_role,
        state="SETUP",
        config=merged_config,
    )
    db.add(trial_row)
    await db.flush()

    # 4. Seed participating Agents
    agents = _seed_trial_agents(case_row, merged_config)
    for agent in agents:
        agent.trial_id = trial_row.id
        db.add(agent)

    await db.commit()
    await db.refresh(trial_row)

    # 5. Return TrialDetail
    agent_summaries = [
        AgentSummary(
            id=ag.id,
            role=ag.role,
            tier=ag.tier,
            persona=ag.persona,
        )
        for ag in agents
    ]

    detail = TrialDetail(
        id=trial_row.id,
        case_id=case_row.id,
        case_title=case_row.title,
        case_slug=case_row.slug,
        user_id=trial_row.user_id,
        mode=trial_row.mode,
        human_role=trial_row.human_role,
        state=trial_row.state,
        config=trial_row.config,
        started_at=trial_row.started_at,
        finished_at=trial_row.finished_at,
        agents=agent_summaries,
        turns_count=0,
    )

    return SuccessResponse(data=detail, meta=Meta(request_id=req_id))


@router.get("/{trial_id}", response_model=SuccessResponse[TrialDetail])
async def get_trial(
    trial_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[TrialDetail]:
    req_id = get_request_id(request)

    stmt = (
        select(Trial)
        .options(selectinload(Trial.case), selectinload(Trial.agents))
        .where(Trial.id == trial_id)
    )
    result = await db.execute(stmt)
    trial_row = result.scalar_one_or_none()
    if trial_row is None:
        raise AppException(
            code=ErrorCode.NOT_FOUND,
            message=f"Trial '{trial_id}' not found",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    # Count turns
    turns_cnt_stmt = select(func.count(Turn.id)).where(Turn.trial_id == trial_id)
    turns_res = await db.execute(turns_cnt_stmt)
    turns_count = turns_res.scalar() or 0

    agent_summaries = [
        AgentSummary(
            id=ag.id,
            role=ag.role,
            tier=ag.tier,
            persona=ag.persona,
        )
        for ag in trial_row.agents
    ]

    detail = TrialDetail(
        id=trial_row.id,
        case_id=trial_row.case_id,
        case_title=trial_row.case.title if trial_row.case else "Unknown Case",
        case_slug=trial_row.case.slug if trial_row.case else "unknown",
        user_id=trial_row.user_id,
        mode=trial_row.mode,
        human_role=trial_row.human_role,
        state=trial_row.state,
        config=trial_row.config,
        started_at=trial_row.started_at,
        finished_at=trial_row.finished_at,
        agents=agent_summaries,
        turns_count=turns_count,
    )

    return SuccessResponse(data=detail, meta=Meta(request_id=req_id))


@router.get("/{trial_id}/verdict", response_model=SuccessResponse[VerdictDetail])
async def get_trial_verdict(
    trial_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[VerdictDetail]:
    """Retrieve the aggregated verdict, judicial breakdown, and revealed ground truth."""
    req_id = get_request_id(request)

    verdict_row = await db.get(Verdict, trial_id)
    if verdict_row is None:
        raise AppException(
            code=ErrorCode.NOT_FOUND,
            message=f"Verdict for trial '{trial_id}' has not been resolved yet",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    stmt = select(Trial).options(selectinload(Trial.case)).where(Trial.id == trial_id)
    trial_row = (await db.execute(stmt)).scalar_one_or_none()
    case_row = trial_row.case if trial_row else None

    # Load all votes for this trial
    vote_stmt = (
        select(Vote)
        .options(selectinload(Vote.agent))
        .where(Vote.trial_id == trial_id)
        .order_by(Vote.id.asc())
    )
    votes_res = await db.execute(vote_stmt)
    votes = list(votes_res.scalars().all())

    judge_votes: List[VerdictVoteDetail] = []
    juror_final_votes: List[VerdictVoteDetail] = []
    juror_pre_votes: List[VerdictVoteDetail] = []

    for v in votes:
        vote_detail = VerdictVoteDetail(
            agent_id=v.agent_id,
            role=v.agent.role if v.agent else "unknown",
            kind=v.kind,
            guilty=v.guilty,
            guilt_probability=(
                float(v.guilt_probability) if v.guilt_probability is not None else None
            ),
            confidence=float(v.confidence) if v.confidence is not None else None,
            reasoning=v.reasoning,
            cited_turn_ids=v.cited_turn_ids or [],
        )
        if v.kind == "judge":
            judge_votes.append(vote_detail)
        elif v.kind == "juror_final":
            juror_final_votes.append(vote_detail)
        elif v.kind == "juror_pre":
            juror_pre_votes.append(vote_detail)

    sentence = None
    if verdict_row.outcome == "guilty" and case_row:
        sentence = calculate_bns_sentence_range(case_row.charge, case_row.title)

    verdict_detail = VerdictDetail(
        trial_id=verdict_row.trial_id,
        outcome=verdict_row.outcome,
        score=float(verdict_row.score),
        j=float(verdict_row.j),
        p=float(verdict_row.p),
        threshold=float(verdict_row.threshold),
        disagreement=float(verdict_row.disagreement),
        matches_truth=verdict_row.matches_truth,
        truth=case_row.truth if case_row else None,
        sentence=sentence,
        judge_votes=judge_votes,
        juror_final_votes=juror_final_votes,
        juror_pre_votes=juror_pre_votes,
    )

    return SuccessResponse(data=verdict_detail, meta=Meta(request_id=req_id))


@router.get(
    "/{trial_id}/turns",
    response_model=SuccessResponse[List[TurnSummary]],
    summary="Paginated list of persisted turns for a trial",
)
async def get_trial_turns(
    trial_id: UUID,
    request: Request,
    speaker: Optional[str] = None,
    struck: Optional[bool] = None,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[List[TurnSummary]]:
    """Return persisted dialogue turns for a trial, optionally filtered by speaker/struck."""
    req_id = get_request_id(request)

    # Verify trial exists
    trial_exists = await db.get(Trial, trial_id)
    if trial_exists is None:
        raise AppException(
            code=ErrorCode.NOT_FOUND,
            message=f"Trial '{trial_id}' not found",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    stmt = select(Turn).where(Turn.trial_id == trial_id).order_by(Turn.seq.asc())
    if speaker is not None:
        stmt = stmt.where(Turn.speaker_role == speaker)
    if struck is not None:
        stmt = stmt.where(Turn.struck.is_(struck))
    stmt = stmt.offset(offset).limit(max(1, min(limit, 500)))

    result = await db.execute(stmt)
    turns = list(result.scalars().all())

    summaries: List[TurnSummary] = [
        TurnSummary(
            id=t.id,
            seq=t.seq,
            speaker=t.speaker_role,
            text=t.text,
            phase=None,
            action=t.action,
            emotion=t.emotion,
            struck=bool(t.struck),
            objection_type=(
                t.objection.get("ground") if isinstance(t.objection, dict) else None
            ),
            created_at=t.created_at,
        )
        for t in turns
    ]

    return SuccessResponse(data=summaries, meta=Meta(request_id=req_id))


_INTERACTIVE_MODES = {"lawyer", "judge", "juror"}


@router.post(
    "/{trial_id}/actions",
    response_model=SuccessResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Submit a human action or objection to an active trial (REST alternative to WS)",
)
async def post_trial_action(
    trial_id: UUID,
    body: HumanActionRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[dict]:
    """Enqueue a human action or objection into the trial's input queue.

    This is a REST-based alternative to sending the action over the WebSocket.
    The trial must be in an interactive mode (lawyer, judge, or juror).
    """
    from app.orchestrator.human_input import post_human_action

    req_id = get_request_id(request)

    trial_row = await db.get(Trial, trial_id)
    if trial_row is None:
        raise AppException(
            code=ErrorCode.NOT_FOUND,
            message=f"Trial '{trial_id}' not found",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    if trial_row.mode not in _INTERACTIVE_MODES:
        raise AppException(
            code=ErrorCode.FORBIDDEN,
            message=(
                f"Trial '{trial_id}' is in mode '{trial_row.mode}' "
                "which does not accept human actions"
            ),
            status_code=status.HTTP_403_FORBIDDEN,
        )

    post_human_action(trial_id, body.model_dump(exclude_none=True))

    return SuccessResponse(
        data={"queued": True, "trial_id": str(trial_id)},
        meta=Meta(request_id=req_id),
    )
