"""Tier chain parser and provider key registry.

Parses CHAIN_STRONG, CHAIN_MID, and CHAIN_SMALL configuration strings
into ordered lists of (provider, model) links. Ensures Ollama is always
the terminal link in every tier chain.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from app.config import settings
from app.llm.pool import KeyPool


@dataclass(frozen=True)
class ChainLink:
    """A single link in a tier fallback chain."""

    provider: str
    model: str


_DEFAULT_CHAINS: Dict[str, str] = {
    "strong": (
        "groq|llama-3.3-70b-versatile,"
        "gemini|gemini-2.0-flash,"
        "openrouter|meta-llama/llama-3.3-70b-instruct"
    ),
    "mid": "groq|llama-3.1-8b-instant,gemini|gemini-2.0-flash",
    "small": "groq|llama-3.1-8b-instant",
}


def parse_chain(chain_str: str) -> List[ChainLink]:
    """Parse a comma-separated 'provider|model' string into ChainLinks.

    Parses the chain string into ordered links. Ollama is NOT automatically
    appended — it must be explicitly configured in the chain string since
    Ollama is not installed locally. If Ollama is configured but not
    available, it will fail and the chain will exhaust without it.
    """
    links: List[ChainLink] = []
    if chain_str and chain_str.strip():
        for item in chain_str.split(","):
            part = item.strip()
            if not part or "|" not in part:
                continue
            provider, model = part.split("|", 1)
            provider = provider.strip().lower()
            model = model.strip()
            if provider and model:
                links.append(ChainLink(provider=provider, model=model))

    return links


def get_tier_chain(tier: str) -> List[ChainLink]:
    """Return the configured ChainLinks for strong, mid, or small tier."""
    t = tier.lower().strip()
    raw = ""
    if t == "strong":
        raw = settings.chain_strong
    elif t == "mid":
        raw = settings.chain_mid
    elif t == "small":
        raw = settings.chain_small

    if not raw or not raw.strip():
        raw = _DEFAULT_CHAINS.get(t, _DEFAULT_CHAINS["mid"])

    return parse_chain(raw)


class PoolRegistry:
    """Holds KeyPool instances for all configured providers."""

    def __init__(self) -> None:
        self._pools: Dict[str, KeyPool] = {}
        self.reload_pools()

    def reload_pools(self) -> None:
        """Initialize or reload key pools from environment settings."""
        self._pools = {
            "gemini": KeyPool(provider="gemini"),
            "groq": KeyPool(provider="groq"),
            "openrouter": KeyPool(provider="openrouter"),
            "ollama": KeyPool(provider="ollama"),
        }

        # Populate Gemini keys
        if settings.gemini_api_keys:
            for k in settings.gemini_api_keys.split(","):
                if k.strip():
                    self._pools["gemini"].add_key(k.strip())

        # Populate Groq keys
        if settings.groq_api_keys:
            for k in settings.groq_api_keys.split(","):
                if k.strip():
                    self._pools["groq"].add_key(k.strip())

        # Populate OpenRouter keys
        if settings.openrouter_api_keys:
            for k in settings.openrouter_api_keys.split(","):
                if k.strip():
                    self._pools["openrouter"].add_key(k.strip())

        # Ollama local key (always available by default)
        self._pools["ollama"].add_key(secret="", alias="ollama#local")

    def get_pool(self, provider: str) -> Optional[KeyPool]:
        """Return the KeyPool for a given provider name."""
        return self._pools.get(provider.lower().strip())


# Global singleton registry
pool_registry = PoolRegistry()
