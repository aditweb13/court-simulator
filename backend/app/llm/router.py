"""Unified LLM router with multi-provider failover, cooldown, and JSON validation.

This module is the SINGLE public entry point for all model inferences across
the application: ``chat(tier, messages, response_model=None, timeout=60)``.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional, Type, TypeVar
from uuid import UUID

from pydantic import BaseModel, ValidationError

from app.core.errors import LLMUnavailable
from app.llm.chains import get_tier_chain, pool_registry
from app.llm.client import call_provider
from app.llm.pool import AttemptOutcome

logger = logging.getLogger("app.llm")

T = TypeVar("T", bound=BaseModel)


def _extract_json_string(text: str) -> str:
    """Extract raw JSON substring from potentially markdown-wrapped text."""
    stripped = text.strip()
    if stripped.startswith("```"):
        # Match ```json ... ``` or ``` ... ```
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", stripped, re.DOTALL)
        if match:
            return match.group(1).strip()
    return stripped


async def _log_attempt(
    provider: str,
    model: str,
    key_alias: str,
    tokens_in: Optional[int],
    tokens_out: Optional[int],
    latency_ms: int,
    status: str,
    trial_id: Optional[UUID] = None,
    agent_role: Optional[str] = None,
) -> None:
    """Record attempt metrics without ever logging API keys or prompt text."""
    logger.info(
        "LLM attempt: provider=%s model=%s key=%s latency=%dms in=%s out=%s status=%s",
        provider,
        model,
        key_alias,
        latency_ms,
        tokens_in,
        tokens_out,
        status,
    )
    # Task 17 will record this into the database llm_calls table if available.
    try:
        from app.llm.logger import record_llm_call

        await record_llm_call(
            provider=provider,
            model=model,
            key_alias=key_alias,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            latency_ms=latency_ms,
            status=status,
            trial_id=trial_id,
            agent_role=agent_role,
        )
    except ImportError:
        pass
    except Exception as exc:  # pragma: no cover
        logger.debug("Optional llm_calls DB logging skipped: %s", exc)


async def chat(
    tier: str,
    messages: List[Dict[str, str]],
    *,
    response_model: Optional[Type[T]] = None,
    timeout: float = 60.0,
    max_attempts: int = 8,
    trial_id: Optional[UUID] = None,
    agent_role: Optional[str] = None,
) -> Any:
    """Send chat messages through the tier's provider chain with automatic failover.

    Parameters
    ----------
    tier:
        Chain tier: 'strong', 'mid', or 'small'.
    messages:
        Standard list of chat message dicts with 'role' and 'content'.
    response_model:
        Optional Pydantic model class. When provided, model output is parsed
        and validated. On validation failure, one retry is performed before
        falling through to the next provider.
    timeout:
        Timeout in seconds per HTTP attempt (default 60).
    max_attempts:
        Hard cap on total provider requests across the entire call (default 8).
    trial_id:
        Optional UUID of the trial for call attribution in DB logs.
    agent_role:
        Optional role identifier (e.g. 'judge', 'prosecutor') for DB logs.

    Returns
    -------
    str | T:
        The raw response string if response_model is None, otherwise an
        instance of response_model.

    Raises
    ------
    LLMUnavailable:
        If all providers in the chain fail or max_attempts is exceeded.
    """
    chain = get_tier_chain(tier)
    attempts = 0

    for link in chain:
        if attempts >= max_attempts:
            break

        pool = pool_registry.get_pool(link.provider)
        if pool is None:
            continue

        while attempts < max_attempts:
            # Pick a ready key from the provider's pool
            key = pool.pick()
            if key is None:
                # All keys for this provider are on cooldown -> move to next provider
                break

            attempts += 1
            resp = await call_provider(
                provider=link.provider,
                model=link.model,
                messages=messages,
                key=key,
                timeout=timeout,
            )

            status_str = resp.outcome.value
            await _log_attempt(
                provider=link.provider,
                model=link.model,
                key_alias=key.alias,
                tokens_in=resp.tokens_in,
                tokens_out=resp.tokens_out,
                latency_ms=resp.latency_ms,
                status=status_str,
                trial_id=trial_id,
                agent_role=agent_role,
            )

            if resp.outcome == AttemptOutcome.OK and resp.content is not None:
                key.reset()

                if response_model is None:
                    return resp.content

                # Validate structured JSON output
                parsed_model = _try_parse_model(resp.content, response_model)
                if parsed_model is not None:
                    return parsed_model

                # Invalid JSON/schema: retry ONCE asking for valid JSON only
                if attempts < max_attempts:
                    attempts += 1
                    retry_messages = list(messages) + [
                        {"role": "assistant", "content": resp.content},
                        {
                            "role": "user",
                            "content": (
                                "Your previous response was not valid JSON conforming to "
                                "the requested schema. Respond with ONLY a valid raw JSON "
                                "object matching the schema. No markdown, no code blocks."
                            ),
                        },
                    ]
                    retry_resp = await call_provider(
                        provider=link.provider,
                        model=link.model,
                        messages=retry_messages,
                        key=key,
                        timeout=timeout,
                    )
                    retry_status = retry_resp.outcome.value
                    await _log_attempt(
                        provider=link.provider,
                        model=link.model,
                        key_alias=key.alias,
                        tokens_in=retry_resp.tokens_in,
                        tokens_out=retry_resp.tokens_out,
                        latency_ms=retry_resp.latency_ms,
                        status=retry_status,
                        trial_id=trial_id,
                        agent_role=agent_role,
                    )
                    if retry_resp.outcome == AttemptOutcome.OK and retry_resp.content:
                        retry_parsed = _try_parse_model(retry_resp.content, response_model)
                        if retry_parsed is not None:
                            return retry_parsed

                # Fall through to next provider if validation retry failed
                break

            elif resp.outcome == AttemptOutcome.QUOTA:
                # 401 or 403: bench the key for 24h
                key.bench(auth_failure=True)
                # Loop continues to pick next key or move on if pool exhausted

            elif resp.outcome == AttemptOutcome.SKIP_PROVIDER:
                # 400, 404, 422: bad model or unsupported request format
                # Skip to next provider WITHOUT benching key
                break

            elif resp.outcome == AttemptOutcome.TIMEOUT:
                # Timeout or transport error: bench key for 30s
                key.bench(seconds=30.0)

            else:
                # 429, 5xx: bench using Retry-After or escalation
                key.bench(retry_after=resp.retry_after)

    raise LLMUnavailable("All LLM providers in the chain exhausted or max attempts reached")


def _try_parse_model(raw_content: str, model_cls: Type[T]) -> Optional[T]:
    """Attempt to parse and validate JSON text against a Pydantic model."""
    try:
        clean_json = _extract_json_string(raw_content)
        data = json.loads(clean_json)
        if isinstance(data, dict):
            return model_cls.model_validate(data)
        return None
    except (json.JSONDecodeError, ValidationError, TypeError):
        return None
