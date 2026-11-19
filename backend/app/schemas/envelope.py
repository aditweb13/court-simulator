"""Standard API request and response envelopes."""

from typing import Any, Dict, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class Meta(BaseModel):
    request_id: str = Field(description="Unique request tracing ID")


class SuccessResponse(BaseModel, Generic[T]):
    data: T
    meta: Meta


class ErrorDetail(BaseModel):
    code: str = Field(description="Standardized error code")
    message: str = Field(description="Human readable description")
    details: Dict[str, Any] = Field(
        default_factory=dict, description="Additional context or validation errors"
    )


class ErrorResponse(BaseModel):
    error: ErrorDetail
    meta: Meta
