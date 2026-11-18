"""HTTP client for OpenAI-compatible LLM provider chat completion endpoints.

Supports Gemini, Groq, OpenRouter, and local Ollama via standardized
OpenAI-compatible `/chat/completions` REST endpoints.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import httpx

from app.config import settings
from app.llm.pool import AttemptOutcome, KeyState, classify_status


@dataclass
class ProviderResponse:
    """Detailed result of a single provider HTTP chat completion call."""

    outcome: AttemptOutcome
    content: Optional[str] = None
    status_code: Optional[int] = None
    tokens_in: Optional[int] = None
    tokens_out: Optional[int] = None
    latency_ms: int = 0
    retry_after: Optional[float] = None
    error_message: Optional[str] = None


def get_provider_endpoint(provider: str) -> str:
    """Return the full chat completions URL for the specified provider."""
    p = provider.lower()
    if p == "gemini":
        base = settings.gemini_base_url.rstrip("/")
        return f"{base}/chat/completions"
    elif p == "groq":
        base = settings.groq_base_url.rstrip("/")
        return f"{base}/chat/completions"
    elif p == "openrouter":
        base = settings.openrouter_base_url.rstrip("/")
        return f"{base}/chat/completions"
    elif p == "ollama":
        base = settings.ollama_base_url.rstrip("/")
        if not base.endswith("/v1"):
            base = f"{base}/v1"
        return f"{base}/chat/completions"
    else:
        # Default fallback if a custom provider URL is configured
        return f"{p.rstrip('/')}/chat/completions"


def _parse_retry_after(headers: httpx.Headers) -> Optional[float]:
    """Extract Retry-After header as seconds if present."""
    val = headers.get("retry-after")
    if not val:
        return None
    try:
        return float(val.strip())
    except ValueError:
        return None


async def call_provider(
    provider: str,
    model: str,
    messages: List[Dict[str, str]],
    key: Optional[KeyState] = None,
    *,
    timeout: float = 60.0,
    temperature: float = 0.7,
    response_format: Optional[Dict[str, Any]] = None,
    client: Optional[httpx.AsyncClient] = None,
) -> ProviderResponse:
    """Send a chat completion request to an OpenAI-compatible provider endpoint.

    Parameters
    ----------
    provider:
        Provider name: 'gemini', 'groq', 'openrouter', or 'ollama'.
    model:
        Model identifier (read from chain config, never hardcoded).
    messages:
        Standard chat messages list of dicts with 'role' and 'content'.
    key:
        The KeyState providing the secret token. May be None for Ollama.
    timeout:
        HTTP request timeout in seconds (default 60.0).
    temperature:
        Sampling temperature (default 0.7).
    response_format:
        Optional schema or type specifier (e.g. ``{"type": "json_object"}``).
    client:
        Optional custom httpx.AsyncClient for connection reuse or testing.
    """
    url = get_provider_endpoint(provider)
    headers = {
        "Content-Type": "application/json",
    }

    token = key.secret if key else ""
    if token:
        headers["Authorization"] = f"Bearer {token}"

    if provider.lower() == "openrouter":
        headers["HTTP-Referer"] = "https://verdict.local"
        headers["X-Title"] = "Verdict"

    payload: Dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }
    if response_format:
        payload["response_format"] = response_format

    start_time = time.perf_counter()

    async def _send(c: httpx.AsyncClient) -> ProviderResponse:
        try:
            resp = await c.post(url, json=payload, headers=headers, timeout=timeout)
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            status_code = resp.status_code

            if status_code == 200:
                data = resp.json()
                choices = data.get("choices", [])
                content = None
                if choices:
                    content = choices[0].get("message", {}).get("content")

                usage = data.get("usage", {})
                tokens_in = usage.get("prompt_tokens")
                tokens_out = usage.get("completion_tokens")

                return ProviderResponse(
                    outcome=AttemptOutcome.OK,
                    content=content,
                    status_code=status_code,
                    tokens_in=tokens_in,
                    tokens_out=tokens_out,
                    latency_ms=latency_ms,
                )

            # Non-200 response
            outcome = classify_status(status_code)
            retry_after = _parse_retry_after(resp.headers)
            error_text = resp.text[:500] if resp.text else f"HTTP {status_code}"

            return ProviderResponse(
                outcome=outcome,
                status_code=status_code,
                latency_ms=latency_ms,
                retry_after=retry_after,
                error_message=error_text,
            )

        except httpx.TimeoutException as exc:
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            return ProviderResponse(
                outcome=AttemptOutcome.TIMEOUT,
                latency_ms=latency_ms,
                error_message=f"Timeout after {timeout}s: {exc}",
            )
        except httpx.RequestError as exc:
            # Transport errors (connection refused, DNS fail, etc.) bench for 30s like timeouts
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            return ProviderResponse(
                outcome=AttemptOutcome.TIMEOUT,
                latency_ms=latency_ms,
                error_message=f"Transport error: {exc}",
            )

    if client is not None:
        return await _send(client)

    async with httpx.AsyncClient() as new_client:
        return await _send(new_client)

