"""Error codes, exceptions, and FastAPI exception handlers."""

import uuid
from enum import Enum
from typing import Any, Dict, Optional

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.schemas.envelope import ErrorDetail, ErrorResponse, Meta


class ErrorCode(str, Enum):
    VALIDATION_ERROR = "VALIDATION_ERROR"
    UNAUTHENTICATED = "UNAUTHENTICATED"
    FORBIDDEN = "FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    RULE_VIOLATION = "RULE_VIOLATION"
    RATE_LIMITED = "RATE_LIMITED"
    LLM_UNAVAILABLE = "LLM_UNAVAILABLE"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class AppException(Exception):
    def __init__(
        self,
        code: ErrorCode,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class LLMUnavailable(AppException):
    def __init__(
        self,
        message: str = "All LLM providers in the chain exhausted",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            code=ErrorCode.LLM_UNAVAILABLE,
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details=details,
        )


def get_request_id(request: Request) -> str:
    req_id = getattr(request.state, "request_id", None)
    if not req_id:
        req_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = req_id
    return req_id


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    req_id = get_request_id(request)
    envelope = ErrorResponse(
        error=ErrorDetail(code=exc.code.value, message=exc.message, details=exc.details),
        meta=Meta(request_id=req_id),
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=envelope.model_dump(),
        headers={"X-Request-ID": req_id},
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    req_id = get_request_id(request)
    details = {"errors": exc.errors()}
    envelope = ErrorResponse(
        error=ErrorDetail(
            code=ErrorCode.VALIDATION_ERROR.value,
            message="Request validation failed",
            details=details,
        ),
        meta=Meta(request_id=req_id),
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=envelope.model_dump(),
        headers={"X-Request-ID": req_id},
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    req_id = get_request_id(request)
    code_map = {
        status.HTTP_401_UNAUTHORIZED: ErrorCode.UNAUTHENTICATED,
        status.HTTP_403_FORBIDDEN: ErrorCode.FORBIDDEN,
        status.HTTP_404_NOT_FOUND: ErrorCode.NOT_FOUND,
        status.HTTP_409_CONFLICT: ErrorCode.CONFLICT,
        status.HTTP_422_UNPROCESSABLE_ENTITY: ErrorCode.VALIDATION_ERROR,
        status.HTTP_429_TOO_MANY_REQUESTS: ErrorCode.RATE_LIMITED,
        status.HTTP_503_SERVICE_UNAVAILABLE: ErrorCode.LLM_UNAVAILABLE,
    }
    code = code_map.get(exc.status_code, ErrorCode.INTERNAL_ERROR)
    message = str(exc.detail) if exc.detail else "An error occurred"

    envelope = ErrorResponse(
        error=ErrorDetail(code=code.value, message=message, details={}),
        meta=Meta(request_id=req_id),
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=envelope.model_dump(),
        headers={"X-Request-ID": req_id},
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    req_id = get_request_id(request)
    envelope = ErrorResponse(
        error=ErrorDetail(
            code=ErrorCode.INTERNAL_ERROR.value,
            message="Internal server error",
            details={},
        ),
        meta=Meta(request_id=req_id),
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=envelope.model_dump(),
        headers={"X-Request-ID": req_id},
    )

