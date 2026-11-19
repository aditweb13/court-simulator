"""Admin REST endpoints for LLM pool status and observability."""

from __future__ import annotations

import time
from typing import Dict, List

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin_user
from app.core.errors import get_request_id
from app.db.models.llm_call import LLMCall
from app.db.models.user import User
from app.db.session import get_db
from app.llm.chains import pool_registry
from app.schemas.admin import KeyStatusRead, ProviderStatusRead
from app.schemas.envelope import Meta, SuccessResponse

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/llm-status", response_model=SuccessResponse[List[ProviderStatusRead]])
async def get_llm_status(
    request: Request,
    _admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[List[ProviderStatusRead]]:
    """Return health and status for all LLM providers and key pools.

    Only accessible to authenticated users whose email appears in ADMIN_EMAILS.
    Never returns raw API keys or secrets.
    """
    req_id = get_request_id(request)

    alias_call_counts: Dict[str, int] = {}
    alias_last_status: Dict[str, str] = {}

    try:
        # Aggregated call count per key_alias
        counts_stmt = select(
            LLMCall.key_alias,
            func.count(LLMCall.id),
        ).group_by(LLMCall.key_alias)
        counts_res = await db.execute(counts_stmt)
        for alias, count in counts_res.all():
            if alias:
                alias_call_counts[alias] = int(count)

        # Most recent call status per key_alias
        subq = select(
            LLMCall.key_alias,
            LLMCall.status,
            func.row_number()
            .over(
                partition_by=LLMCall.key_alias,
                order_by=LLMCall.id.desc(),
            )
            .label("rn"),
        ).subquery()
        latest_stmt = select(subq.c.key_alias, subq.c.status).where(subq.c.rn == 1)
        latest_res = await db.execute(latest_stmt)
        for alias, st in latest_res.all():
            if alias:
                alias_last_status[alias] = str(st)
    except Exception:
        # If DB query fails or table is empty in testing, fallback to empty metrics
        pass

    now_mono = time.monotonic()
    provider_results: List[ProviderStatusRead] = []

    for prov_name, pool in pool_registry._pools.items():
        key_statuses: List[KeyStatusRead] = []
        ready_count = 0
        cooling_count = 0

        for key in pool.keys:
            ready = key.is_ready(now_mono)
            if ready:
                ready_count += 1
                rem_cooldown = 0.0
            else:
                cooling_count += 1
                rem_cooldown = max(0.0, round(key.cooldown_until - now_mono, 1))

            key_statuses.append(
                KeyStatusRead(
                    key_alias=key.alias,
                    provider=prov_name,
                    is_ready=ready,
                    cooling_down_seconds=rem_cooldown,
                    fail_count=key.fail_count,
                    last_status=alias_last_status.get(key.alias),
                    recent_call_count=alias_call_counts.get(key.alias, 0),
                )
            )

        provider_results.append(
            ProviderStatusRead(
                provider=prov_name,
                total_keys=len(pool.keys),
                ready_keys=ready_count,
                cooling_keys=cooling_count,
                keys=key_statuses,
            )
        )

    return SuccessResponse(data=provider_results, meta=Meta(request_id=req_id))
