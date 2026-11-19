"""Cases REST routes."""

from __future__ import annotations

import uuid
from typing import List

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import AppException, ErrorCode, get_request_id
from app.db.models.case import Case, Evidence, Witness
from app.db.session import get_db
from app.schemas.case import CaseDetail, CaseRead, EvidenceRead, WitnessRead
from app.schemas.envelope import Meta, SuccessResponse

router = APIRouter(prefix="/cases", tags=["cases"])


@router.get("", response_model=SuccessResponse[List[CaseRead]])
async def list_cases(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[List[CaseRead]]:
    req_id = get_request_id(request)

    ev_count_sub = (
        select(func.count(Evidence.id)).where(Evidence.case_id == Case.id).scalar_subquery()
    )
    wit_count_sub = (
        select(func.count(Witness.id)).where(Witness.case_id == Case.id).scalar_subquery()
    )

    stmt = select(
        Case,
        ev_count_sub.label("evidence_count"),
        wit_count_sub.label("witness_count"),
    ).order_by(Case.created_at.desc())
    result = await db.execute(stmt)
    rows = result.all()

    cases_out: List[CaseRead] = []
    for case_row, ev_cnt, wit_cnt in rows:
        cases_out.append(
            CaseRead(
                id=case_row.id,
                slug=case_row.slug,
                title=case_row.title,
                jurisdiction=case_row.jurisdiction,
                charge=case_row.charge,
                difficulty=case_row.difficulty,
                source=case_row.source,
                evidence_count=ev_cnt or 0,
                witness_count=wit_cnt or 0,
            )
        )

    return SuccessResponse(data=cases_out, meta=Meta(request_id=req_id))


@router.get("/{case_id}", response_model=SuccessResponse[CaseDetail])
async def get_case(
    case_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[CaseDetail]:
    req_id = get_request_id(request)

    stmt = select(Case).options(selectinload(Case.evidence), selectinload(Case.witnesses))
    try:
        parsed_uuid = uuid.UUID(case_id)
        stmt = stmt.where(Case.id == parsed_uuid)
    except ValueError:
        stmt = stmt.where(Case.slug == case_id)

    result = await db.execute(stmt)
    case_row = result.scalar_one_or_none()
    if case_row is None:
        raise AppException(
            code=ErrorCode.NOT_FOUND,
            message=f"Case '{case_id}' not found",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    evidence_out = [
        EvidenceRead(
            id=ev.id,
            exhibit_no=ev.exhibit_no,
            type=ev.type,
            description=ev.description,
            admissible=ev.admissible,
            reason_inadmissible=ev.reason_inadmissible,
        )
        for ev in case_row.evidence
    ]

    witnesses_out = [
        WitnessRead(
            id=w.id,
            name=w.name,
            persona=w.persona or {},
        )
        for w in case_row.witnesses
    ]

    detail = CaseDetail(
        id=case_row.id,
        slug=case_row.slug,
        title=case_row.title,
        jurisdiction=case_row.jurisdiction,
        charge=case_row.charge,
        difficulty=case_row.difficulty,
        source=case_row.source,
        evidence=evidence_out,
        witnesses=witnesses_out,
    )

    return SuccessResponse(data=detail, meta=Meta(request_id=req_id))
