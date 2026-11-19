"""Schemas for Admin LLM status endpoints."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class KeyStatusRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key_alias: str = Field(description="Sanitized key identifier (never the secret key)")
    provider: str = Field(description="LLM provider name")
    is_ready: bool = Field(description="Whether key is ready for requests")
    cooling_down_seconds: float = Field(
        description="Remaining cooldown seconds, 0.0 if ready",
    )
    fail_count: int = Field(description="Consecutive failure count")
    last_status: Optional[str] = Field(
        default=None,
        description="Outcome of the most recent call for this key",
    )
    recent_call_count: int = Field(
        default=0,
        description="Total calls recorded in llm_calls",
    )


class ProviderStatusRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str = Field(description="LLM provider name")
    total_keys: int = Field(description="Total keys registered in pool")
    ready_keys: int = Field(description="Number of keys ready")
    cooling_keys: int = Field(description="Number of keys currently on cooldown")
    keys: List[KeyStatusRead] = Field(
        default_factory=list,
        description="Per-key breakdown",
    )
