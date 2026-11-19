"""Context filter and prompt builders for Jurors during deliberation and voting.

Information Isolation Rules:
- Jurors receive ONLY admitted, NON-STRUCK turns (Turn.admitted == True AND Turn.struck == False).
- Jurors receive admitted evidence exhibits (Evidence.admissible == True).
- Jurors NEVER receive the hidden ground truth (case.truth).
- Jurors NEVER receive struck turns or private lawyer notes/memories.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.case import Case
from app.db.models.trial import Agent, Turn

logger = logging.getLogger("app.context.juror")


async def build_juror_context(
    db: AsyncSession,
    trial_id: UUID,
    case_id: UUID,
    juror_no: int,
) -> Dict[str, Any]:
    """Assemble isolated courtroom context for a single juror."""
    # 1. Public case facts (excluding hidden ground truth)
    case_stmt = select(Case).options(selectinload(Case.evidence)).where(Case.id == case_id)
    case_res = await db.execute(case_stmt)
    case_row = case_res.scalar_one_or_none()
    if case_row is None:
        raise ValueError(f"Case '{case_id}' not found")

    # 2. Admitted evidence only
    admitted_evidence = [
        {
            "exhibit_no": ev.exhibit_no,
            "type": ev.type,
            "description": ev.description,
        }
        for ev in case_row.evidence
        if ev.admissible
    ]

    # 3. Admitted, NON-STRUCK turns strictly (Clean Record Rule)
    turn_stmt = (
        select(Turn)
        .where(
            Turn.trial_id == trial_id,
            Turn.admitted == True,  # noqa: E712
            Turn.struck == False,  # noqa: E712
        )
        .order_by(Turn.seq.asc())
    )
    turn_res = await db.execute(turn_stmt)
    turns = turn_res.scalars().all()
    clean_record = [
        {
            "seq": t.seq,
            "speaker": t.speaker_role,
            "text": t.text,
            "id": str(t.id),
        }
        for t in turns
    ]

    # 4. Juror Agent Persona
    agent_stmt = select(Agent).where(Agent.trial_id == trial_id, Agent.role == "juror")
    agent_res = await db.execute(agent_stmt)
    juror_agents = agent_res.scalars().all()

    persona: Dict[str, Any] = {
        "juror_no": juror_no,
        "reasoning_style": "skeptical",
        "traits": "Evaluates facts objectively",
    }
    for ja in juror_agents:
        if isinstance(ja.persona, dict) and ja.persona.get("juror_no") == juror_no:
            persona = ja.persona
            break

    return {
        "case_title": case_row.title,
        "charge": case_row.charge,
        "jurisdiction": case_row.jurisdiction,
        "juror": persona,
        "evidence": admitted_evidence,
        "record": clean_record,
    }


def build_juror_vote_prompt(
    ctx: Dict[str, Any],
    stage: str = "pre",
) -> List[Dict[str, str]]:
    """Prompt for juror casting their private pre- or post-deliberation vote."""
    juror_info = ctx.get("juror", {})
    style = juror_info.get("reasoning_style", "balanced")
    traits = juror_info.get("traits", "Thoughtful citizen evaluating criminal charges")

    stage_title = (
        "Initial Pre-Deliberation Vote" if stage == "pre" else "Final Post-Deliberation Vote"
    )

    system_prompt = (
        f"You are Juror #{juror_info.get('juror_no', 1)} in an Indian courtroom trial simulation.\n"
        f"Your Reasoning Style: {style}\n"
        f"Your Orientation: {traits}\n\n"
        "Your solemn duty is to evaluate whether the prosecution has proven the charge "
        "beyond reasonable doubt. You must rely ONLY on the admitted evidence and clean record. "
        "Any testimony that was objected to and sustained has been struck and "
        "must not influence you."
    )

    user_prompt = (
        f"Stage: {stage_title}\n"
        f"Case: {ctx['case_title']}\n"
        f"Charge: {ctx['charge']}\n\n"
        "Admitted Exhibits:\n"
        + "\n".join(
            f"- Exhibit {e['exhibit_no']} ({e['type']}): {e['description']}"
            for e in ctx.get("evidence", [])
        )
        + "\n\nAdmitted Trial Record:\n"
        + "\n".join(f"[{r['seq']}] {r['speaker']}: {r['text']}" for r in ctx.get("record", []))
        + (
            "\n\nEvaluate the evidence step-by-step from your reasoning perspective.\n"
            "State whether you vote guilty (True) or not guilty (False), your assessed probability "
            "of guilt (0.0 to 1.0), your certainty confidence (0.0 to 1.0), your reasoning, and "
            "the specific turn sequence numbers that influenced your decision."
        )
    )

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def build_juror_deliberation_prompt(
    ctx: Dict[str, Any],
    previous_deliberation_turns: List[Dict[str, Any]],
    is_devil_advocate: bool = False,
) -> List[Dict[str, str]]:
    """Prompt for a juror speaking during a deliberation round."""
    juror_info = ctx.get("juror", {})
    style = juror_info.get("reasoning_style", "balanced")
    traits = juror_info.get("traits", "Thoughtful citizen")

    advocate_note = (
        "\n\nSPECIAL ROLE: You are acting as the DEVIL'S ADVOCATE for this round. "
        "You must actively test the emerging consensus. If fellow jurors are leaning guilty, "
        "vigorously point out reasonable doubts, gaps in physical evidence, or credibility issues. "
        "If they are leaning not guilty, emphasize incriminating evidence and timeline correlation."
        if is_devil_advocate
        else ""
    )

    juror_no = juror_info.get("juror_no", 1)
    system_prompt = (
        f"You are Juror #{juror_no} deliberating with your fellow jurors in the jury room.\n"
        f"Style: {style} ({traits}){advocate_note}\n\n"
        "Keep your contribution concise, focused, conversational, and under 60 words."
    )

    dialogue_summary = (
        "\n".join(
            f"Juror #{d.get('juror_no', '?')}: {d.get('statement', '')}"
            for d in previous_deliberation_turns[-6:]
        )
        if previous_deliberation_turns
        else "The foreman opens the discussion. No statements have been made yet."
    )

    user_prompt = (
        f"Case: {ctx['case_title']}\n"
        f"Charge: {ctx['charge']}\n\n"
        "Recent Deliberation Dialogue:\n"
        f"{dialogue_summary}\n\n"
        "Deliver your deliberation statement to the jury, stating your perspective, "
        "your current leaning (guilty, not_guilty, or undecided), and whether you are "
        "challenging consensus."
    )

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
