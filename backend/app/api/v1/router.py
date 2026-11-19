"""API v1 root router."""

from fastapi import APIRouter

from app.api.v1 import auth, cases, health, trials

api_v1_router = APIRouter()
api_v1_router.include_router(health.router)
api_v1_router.include_router(auth.router)
api_v1_router.include_router(cases.router)
api_v1_router.include_router(trials.router)
