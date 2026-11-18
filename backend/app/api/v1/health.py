"""Health check endpoint."""

from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.schemas.envelope import Meta, SuccessResponse


class HealthData(BaseModel):
    status: str


router = APIRouter(tags=["health"])


@router.get("/health", response_model=SuccessResponse[HealthData])
async def get_health(request: Request) -> SuccessResponse[HealthData]:
    req_id = getattr(request.state, "request_id", "health-check")
    return SuccessResponse(
        data=HealthData(status="ok"),
        meta=Meta(request_id=req_id),
    )

