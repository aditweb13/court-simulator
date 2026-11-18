"""Key pool with per-key cooldown and escalating backoff.

Each provider maintains a pool of API keys. Keys are picked randomly from
the ``ready`` set. On failure the key is benched for an escalating duration
computed as ``min(60 * 2**fail_count, 86_400)`` seconds. A success resets
the fail count. Provider-specific status codes control benching behaviour.
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class AttemptOutcome(str, Enum):
    """Outcome of a single LLM attempt used by the router."""

    OK = "ok"
    QUOTA = "quota"
    ERROR = "error"
    TIMEOUT = "timeout"
    SKIP_PROVIDER = "skip_provider"


# Default bench durations (seconds).
_AUTH_BENCH_SECONDS = 86_400.0  # 401 / 403
_TIMEOUT_BENCH_SECONDS = 30.0
_MAX_BACKOFF_SECONDS = 86_400.0


@dataclass
class KeyState:
    """Mutable state for a single API key."""

    alias: str  # e.g. "gemini#1" — never the real key
    secret: str  # the actual API key (kept in memory, never logged)
    provider: str
    fail_count: int = 0
    cooldown_until: float = 0.0  # epoch seconds

    def is_ready(self, now: Optional[float] = None) -> bool:
        """Return *True* if the key's cooldown has expired."""
        return (now or time.monotonic()) >= self.cooldown_until

    def bench(
        self,
        *,
        seconds: Optional[float] = None,
        retry_after: Optional[float] = None,
        auth_failure: bool = False,
        now: Optional[float] = None,
    ) -> None:
        """Put the key on cooldown.

        Parameters
        ----------
        seconds:
            Explicit bench duration override.
        retry_after:
            Honour a ``Retry-After`` header value (seconds).
        auth_failure:
            If *True* the key is benched for 24 h regardless of the
            backoff schedule.
        now:
            Monotonic clock override for testing.
        """
        _now = now or time.monotonic()
        self.fail_count += 1

        if auth_failure:
            duration = _AUTH_BENCH_SECONDS
        elif retry_after is not None and retry_after > 0:
            duration = retry_after
        elif seconds is not None:
            duration = seconds
        else:
            duration = min(60.0 * (2 ** (self.fail_count - 1)), _MAX_BACKOFF_SECONDS)

        self.cooldown_until = _now + duration

    def reset(self) -> None:
        """Reset fail count and cooldown on success."""
        self.fail_count = 0
        self.cooldown_until = 0.0


@dataclass
class KeyPool:
    """Manages a list of :class:`KeyState` objects for one provider."""

    provider: str
    keys: List[KeyState] = field(default_factory=list)

    # --- mutation ----------------------------------------------------------

    def add_key(self, secret: str, alias: Optional[str] = None) -> KeyState:
        """Add a key to the pool and return its state."""
        idx = len(self.keys) + 1
        ks = KeyState(
            alias=alias or f"{self.provider}#{idx}",
            secret=secret,
            provider=self.provider,
        )
        self.keys.append(ks)
        return ks

    # --- selection ---------------------------------------------------------

    def pick(self, now: Optional[float] = None) -> Optional[KeyState]:
        """Return a random ready key, or ``None`` when all are cooling."""
        _now = now or time.monotonic()
        ready = [k for k in self.keys if k.is_ready(_now)]
        if not ready:
            return None
        return random.choice(ready)

    def all_cooling(self, now: Optional[float] = None) -> bool:
        """Return *True* when every key is on cooldown."""
        _now = now or time.monotonic()
        return all(not k.is_ready(_now) for k in self.keys)

    @property
    def size(self) -> int:
        return len(self.keys)


def classify_status(status_code: int) -> AttemptOutcome:
    """Map an HTTP status code to an :class:`AttemptOutcome`.

    Rules (from the ROUTER SPEC):
    - 200: success
    - 401 / 403: bench 24 h (returned as QUOTA so key is marked bad)
    - 400 / 404 / 422: skip to next provider WITHOUT benching the key
    - 429, 5xx, everything else: bench with Retry-After or escalation
    """
    if status_code == 200:
        return AttemptOutcome.OK
    if status_code in (401, 403):
        return AttemptOutcome.QUOTA
    if status_code in (400, 404, 422):
        return AttemptOutcome.SKIP_PROVIDER
    # 429, 5xx, or any other unexpected status
    return AttemptOutcome.ERROR

