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
from app.db.models.trial import Agent, Trial, Turn
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.envelope import Meta, SuccessResponse
from app.schemas.trial import AgentSummary, TrialCreate, TrialDetail

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


def _seed_trial_agents(case: Case, config: Dict[str, Any]) -> List[Agent]:
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
    for i in range(1, juror_count + 1):
        persona_template = JUROR_PERSONAS[(i - 1) % len(JUROR_PERSONAS)]
        agents.append(
            Agent(
                role="juror",
                tier="small",
                persona={
                    "juror_no": i,
                    "reasoning_style": persona_template["style"],
                    "traits": persona_template["description"],
                },
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
