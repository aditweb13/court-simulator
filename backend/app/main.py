"""FastAPI application factory and middleware setup."""

import uuid
from typing import Callable

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.cases import router as cases_router
from app.api.v1.health import router as health_router
from app.api.v1.router import api_v1_router
from app.api.v1.trials import router as trials_router
from app.config import settings
from app.core.errors import (
    AppException,
    app_exception_handler,
    generic_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from app.ws.router import router as ws_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="Verdict API",
        description="3D Courtroom Simulator Multi-Agent Backend",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    # Request ID Middleware
    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next: Callable) -> Response:
        req_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = req_id
        response: Response = await call_next(request)
        response.headers["X-Request-ID"] = req_id
        return response

    # Exception Handlers
    app.add_exception_handler(AppException, app_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, generic_exception_handler)

    # Routers
    app.include_router(health_router)  # Mounted at /health
    app.include_router(cases_router)  # Mounted at /cases
    app.include_router(trials_router)  # Mounted at /trials
    app.include_router(api_v1_router, prefix="/api/v1")
    app.include_router(ws_router)

    return app


app = create_app()
