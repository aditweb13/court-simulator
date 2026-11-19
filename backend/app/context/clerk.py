"""Context filter and prompt builder for the Court Clerk.

The clerk receives:
- Case public facts (title, formal charge text)
- Accused party name (from case title or defendant persona)
- Current procedural phase

Information Isolation Rule:
The clerk NEVER receives evidence details, witness memories, or the hidden
ground truth (`case.truth`).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.case import Case
from app.db.models.trial import Agent


async def build_clerk_context(
    db: AsyncSession,
    trial_id: UUID,
    case_id: UUID,
) -> Dict[str, Any]:
    """Assemble minimal procedural context for the clerk."""
    case_stmt = select(Case).where(Case.id == case_id)
    case_res = await db.execute(case_stmt)
    case_row = case_res.scalar_one_or_none()
    if case_row is None:
        raise ValueError(f"Case '{case_id}' not found")

    # Get defendant name if available from defendant agent persona
    def_stmt = select(Agent).where(Agent.trial_id == trial_id, Agent.role == "defendant")
    def_res = await db.execute(def_stmt)
    def_agent = def_res.scalar_one_or_none()

    defendant_name = "The Accused"
    if def_agent and isinstance(def_agent.persona, dict):
        defendant_name = def_agent.persona.get("name", "The Accused")

    return {
        "case_title": case_row.title,
        "charge": case_row.charge,
        "defendant_name": defendant_name,
    }


def build_clerk_opening_prompt(
    context: Dict[str, Any],
    clerk_persona: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, str]]:
    """Generate messages for the clerk reading the charges."""
    system_prompt = (
        "You are the Court Reader and Clerk in an Indian Sessions Court. "
        "Your duty is to formally and solemnly read out the charges framed against "
        "the accused before the court. Use standard court language, be precise, "
        "and keep it under 100 words."
    )

    user_prompt = (
        f"Case: {context['case_title']}\n"
        f"Accused: {context['defendant_name']}\n"
        f"Charge: {context['charge']}\n\n"
        "Read the formal charge to the court."
    )

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
