"""Context filter and prompt builder for the Three Verdict Judges.

Each verdict judge represents a distinct judicial philosophy:
1. Textualist: Strict statutory adherence and literal interpretation of enacted penal texts.
2. Precedent: Doctrinal consistency rooted in landmark Supreme Court precedents and ratio decidendi.
3. Fairness: Substantive justice, constitutional protections, and equity.

Isolation Rules:
- Receives admitted, non-struck turns only.
- Receives admitted evidence only.
- Does NOT receive hidden ground truth or lawyer private notes.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.case import Case
from app.db.models.trial import Agent, Turn
from app.rag.retriever import retrieve
from app.verdict.philosophies import format_philosophy_prompt_guidance

logger = logging.getLogger("app.context.verdict_judge")


async def build_verdict_judge_context(
    db: AsyncSession,
    trial_id: UUID,
    case_id: UUID,
    philosophy: str,
    query_topic: Optional[str] = None,
) -> Dict[str, Any]:
    """Assemble isolated judicial evaluation context for a verdict judge."""
    # 1. Public case facts
    case_stmt = select(Case).options(selectinload(Case.evidence)).where(Case.id == case_id)
    case_res = await db.execute(case_stmt)
    case_row = case_res.scalar_one_or_none()
    if case_row is None:
        raise ValueError(f"Case '{case_id}' not found")

    # 2. Admitted evidence
    admitted_evidence = [
        {
            "exhibit_no": ev.exhibit_no,
            "type": ev.type,
            "description": ev.description,
        }
        for ev in case_row.evidence
        if ev.admissible
    ]

    # 3. Clean trial record (omitting struck testimony)
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
    clean_record = [{"seq": t.seq, "speaker": t.speaker_role, "text": t.text} for t in turns]

    # 4. Judicial Agent Persona matching philosophy
    agent_stmt = select(Agent).where(Agent.trial_id == trial_id, Agent.role == "verdict_judge")
    agent_res = await db.execute(agent_stmt)
    judge_agents = agent_res.scalars().all()

    persona: Dict[str, Any] = {
        "philosophy": philosophy,
        "orientation": f"Judicial analysis based on {philosophy}",
    }
    agent_id: Optional[UUID] = None
    for ja in judge_agents:
        if isinstance(ja.persona, dict) and ja.persona.get("philosophy") == philosophy:
            persona = ja.persona
            agent_id = ja.id
            break

    # 5. Retrieve statutory chunks with role='judge'
    retrieval_query = (
        query_topic or f"{case_row.charge} Indian statutory elements precedent standard of proof"
    )
    try:
        retrieved_chunks = await retrieve(
            query=retrieval_query,
            role="judge",
            k=5,
            session=db,
        )
    except Exception as exc:
        logger.warning("Statutory retrieval for verdict judge failed: %s", exc)
        retrieved_chunks = []

    return {
        "agent_id": agent_id,
        "case_title": case_row.title,
        "charge": case_row.charge,
        "jurisdiction": case_row.jurisdiction,
        "judge": persona,
        "evidence": admitted_evidence,
        "record": clean_record,
        "statutes": [getattr(c, "content", str(c)) for c in retrieved_chunks],
    }


def build_verdict_judge_prompt(
    ctx: Dict[str, Any],
) -> List[Dict[str, str]]:
    """Prompt for a verdict judge rendering an independent judicial decision."""
    judge_info = ctx.get("judge", {})
    philosophy = judge_info.get("philosophy", "textualist")
    orientation = judge_info.get("orientation", "Statutory analysis")

    philosophy_guidance = format_philosophy_prompt_guidance(philosophy)

    system_prompt = (
        f"You are a Learned Sessions Judge on the Verdict Bench in an Indian criminal trial.\n"
        f"Orientation: {orientation}\n\n"
        f"{philosophy_guidance}\n\n"
        "You must base your ruling SOLELY on the admitted record and evidence. Struck turns have "
        "been legally excluded from consideration."
    )

    user_prompt = (
        f"Case: {ctx['case_title']}\n"
        f"Charge: {ctx['charge']}\n"
        f"Jurisdiction: {ctx['jurisdiction']}\n\n"
        "Admitted Evidence:\n"
        + "\n".join(
            f"- Exhibit {e['exhibit_no']} ({e['type']}): {e['description']}"
            for e in ctx.get("evidence", [])
        )
        + "\n\nAdmitted Trial Proceedings:\n"
        + "\n".join(f"[{r['seq']}] {r['speaker']}: {r['text']}" for r in ctx.get("record", []))
        + "\n\nRelevant Statutory Texts:\n"
        + "\n".join(f"- {s[:250]}..." for s in ctx.get("statutes", [])[:3])
        + (
            "\n\nRender your formal judicial verdict.\n"
            "State whether you find the accused guilty (True) or not guilty (False), "
            "your assessed guilt probability (0.0 to 1.0), your judicial confidence (0.0 to 1.0), "
            "your formal reasoning applying your philosophy, and the statutory sections cited."
        )
    )

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
