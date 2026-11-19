"""Context filter and prompt builder for the Defendant / Accused agent.

The Defendant receives ONLY:
- Their persona (name, status, demeanor)
- Personal recollections from their perspective
- Defense theory and guidance
- The question directly addressed to them

Information Isolation Rule:
The defendant NEVER receives judicial deliberative notes, jury votes, or
case ground truth outside their personal perspective.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.trial import Agent

logger = logging.getLogger("app.context.defendant")


async def build_defendant_context(
    db: AsyncSession,
    trial_id: UUID,
    question_text: str,
) -> Dict[str, Any]:
    """Assemble isolated context for the Accused / Defendant."""
    agent_stmt = select(Agent).where(Agent.trial_id == trial_id, Agent.role == "defendant")
    agent_res = await db.execute(agent_stmt)
    defendant_agent = agent_res.scalar_one_or_none()

    persona = defendant_agent.persona if defendant_agent else {"name": "The Accused"}
    memories = defendant_agent.memory if defendant_agent else []

    return {
        "name": persona.get("name", "The Accused"),
        "persona": persona,
        "memories": memories,
        "question": question_text,
    }


def build_defendant_answer_prompt(
    ctx: Dict[str, Any],
) -> List[Dict[str, str]]:
    """Build prompt for defendant answering from the stand."""
    system_prompt = (
        f"You are {ctx['name']}, the accused person on trial in an Indian Sessions Court.\n"
        f"Demeanor: {ctx.get('persona', {}).get('demeanor', 'Anxious but steadfast')}\n\n"
        "You maintain your innocence and speak from your personal experience.\n"
        "Keep your answer under 50 words."
    )

    user_prompt = f'You are asked:\n"{ctx["question"]}"\n\nState your response.'

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
