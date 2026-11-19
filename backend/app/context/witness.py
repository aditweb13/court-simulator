"""Context filter and prompt builder for Witness agents.

The Witness receives ONLY:
- Their own persona (name, occupation, demeanor)
- Their private memory slice (first-person memories derived strictly from `saw_event_ids`)
- Their secrets/concealment tendencies (`hides` list)
- The single question currently addressed to them

Information Isolation Rule:
The witness NEVER receives:
- Hidden ground truth (`case.truth`) for events outside their `saw_event_ids`
- Statutory legal corpus / sections
- Other witnesses' memories or secrets
- Lawyer private notes or jury deliberations
- Struck turns from the record
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.case import Case
from app.db.models.trial import Agent, Trial

logger = logging.getLogger("app.context.witness")


async def build_witness_context(
    db: AsyncSession,
    trial_id: UUID,
    witness_name: str,
    question_text: str,
) -> Dict[str, Any]:
    """Assemble strictly isolated knowledge slice context for a testifying witness."""
    # 1. Load Trial and Case
    trial_stmt = select(Trial).where(Trial.id == trial_id)
    trial_res = await db.execute(trial_stmt)
    trial_row = trial_res.scalar_one_or_none()
    if trial_row is None:
        raise ValueError(f"Trial '{trial_id}' not found")

    # 2. Find Agent record for this witness to retrieve stored memory slice
    agent_stmt = select(Agent).where(Agent.trial_id == trial_id, Agent.role == "witness")
    agent_res = await db.execute(agent_stmt)
    agents = agent_res.scalars().all()
    matching_agent = next(
        (a for a in agents if str(a.persona.get("name", "")).lower() == witness_name.lower()),
        None,
    )

    # 3. Load Witness metadata from Case.witnesses
    case_stmt = (
        select(Case).options(selectinload(Case.witnesses)).where(Case.id == trial_row.case_id)
    )
    case_res = await db.execute(case_stmt)
    case_row = case_res.scalar_one_or_none()
    witness_meta = None
    if case_row:
        witness_meta = next(
            (w for w in case_row.witnesses if w.name.lower() == witness_name.lower()),
            None,
        )

    memories = matching_agent.memory if matching_agent else []
    hides = witness_meta.hides if witness_meta else []
    persona = (
        matching_agent.persona if matching_agent else (witness_meta.persona if witness_meta else {})
    )

    return {
        "name": witness_name,
        "persona": persona,
        "memories": memories,
        "hides": hides,
        "question": question_text,
    }


def build_witness_answer_prompt(
    ctx: Dict[str, Any],
) -> List[Dict[str, str]]:
    """Build the prompt for a witness answering a lawyer's question."""
    system_prompt = (
        f"You are {ctx['name']}, testifying under oath in an Indian Sessions Court.\n\n"
        f"Your Demeanor & Traits: {ctx.get('persona', {}).get('demeanor', 'Cooperative')}\n\n"
        "Your Personal Recollections (You ONLY know and experienced what is written below. "
        "If asked about anything outside these memories, you do NOT know or did not see it):\n"
        + "\n".join(
            f"- {m.get('text', str(m)) if isinstance(m, dict) else str(m)}"
            for m in ctx.get("memories", [])
        )
        + (
            "\n\nThings you are reluctant to mention unless directly and cornered into admitting:\n"
            + "\n".join(f"- {h}" for h in ctx.get("hides", []))
            if ctx.get("hides")
            else ""
        )
        + (
            "\n\nCRITICAL RULE: Answer truthfully according to your recollections. "
            "Stay strictly in character. Keep your answer concise and under 50 words."
        )
    )

    user_prompt = (
        f"The examining lawyer asks you:\n"
        f'"{ctx["question"]}"\n\n'
        "Give your spoken answer from the witness box."
    )

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
