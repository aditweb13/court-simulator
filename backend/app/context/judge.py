"""Context filter and prompt builder for the Presiding Sessions Judge.

The judge receives:
- Case public facts (title, slug, jurisdiction, charges)
- Admitted evidence exhibits
- Admitted turns / trial record
- Retrieved statutory chunks (with role='judge')

Information Isolation Rule:
The judge NEVER receives the hidden ground truth (`case.truth`), culprit
identity outside the formal charges, or secret witness observations.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.case import Case
from app.db.models.trial import Turn
from app.rag.retriever import retrieve

logger = logging.getLogger("app.context.judge")


async def build_judge_context(
    db: AsyncSession,
    trial_id: UUID,
    case_id: UUID,
    query_topic: Optional[str] = None,
) -> Dict[str, Any]:
    """Assemble isolated courtroom context for the judge."""
    # 1. Load case (excluding truth!)
    case_stmt = (
        select(Case)
        .options(selectinload(Case.evidence))
        .where(Case.id == case_id)
    )
    case_res = await db.execute(case_stmt)
    case_row = case_res.scalar_one_or_none()
    if case_row is None:
        raise ValueError(f"Case '{case_id}' not found")

    # 2. Extract admitted evidence only
    admitted_evidence = [
        {
            "exhibit_no": ev.exhibit_no,
            "type": ev.type,
            "description": ev.description,
        }
        for ev in case_row.evidence
        if ev.admissible
    ]

    # 3. Retrieve relevant statutory law chunks
    retrieval_query = query_topic or f"{case_row.charge} procedure evidence"
    try:
        retrieved_chunks = await retrieve(
            query=retrieval_query,
            role="judge",
            k=5,
            session=db,
        )
    except Exception as exc:
        logger.warning("Statutory retrieval for judge failed, falling back to empty: %s", exc)
        retrieved_chunks = []

    # 4. Fetch admitted turns from trial record (if any)
    turns_stmt = (
        select(Turn)
        .where(Turn.trial_id == trial_id, Turn.admitted.is_(True), Turn.struck.is_(False))
        .order_by(Turn.seq)
    )
    turns_res = await db.execute(turns_stmt)
    turns = turns_res.scalars().all()

    trial_record = [
        {
            "seq": t.seq,
            "speaker": t.speaker_role,
            "text": t.text,
        }
        for t in turns
    ]

    return {
        "case_title": case_row.title,
        "case_slug": case_row.slug,
        "jurisdiction": case_row.jurisdiction,
        "charge": case_row.charge,
        "admitted_evidence": admitted_evidence,
        "statutory_provisions": [
            {
                "act": c.act,
                "section_no": c.section_no,
                "title": c.title,
                "body": c.body,
            }
            for c in retrieved_chunks
        ],
        "trial_record": trial_record,
    }


def build_judge_opening_prompt(
    context: Dict[str, Any],
    judge_persona: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, str]]:
    """Generate messages for the judge's formal opening statement."""
    title = (
        judge_persona.get("title", "Presiding Sessions Judge")
        if judge_persona
        else "Presiding Sessions Judge"
    )
    style = judge_persona.get("style", "procedural") if judge_persona else "procedural"

    statutes_str = ""
    if context.get("statutory_provisions"):
        items = [
            f"- {s['act']} Section/Article {s['section_no']}: {s['title']}\n  {s['body'][:200]}"
            for s in context["statutory_provisions"][:3]
        ]
        statutes_str = "\nApplicable Legal Provisions:\n" + "\n".join(items)

    system_prompt = (
        f"You are the {title} presiding over an Indian Sessions Court. "
        f"Your judicial style is {style}. Maintain strict courtroom decorum, procedural fairness, "
        "and statutory neutrality. Deliver the opening remarks to commence the proceedings. "
        "Keep your statement clear, formal, authoritative, and under 150 words."
    )

    user_prompt = (
        f"Courtroom: Sessions Court\n"
        f"Case: {context['case_title']}\n"
        f"Charges Under Consideration: {context['charge']}\n"
        f"{statutes_str}\n\n"
        "Call the court to order, announce the matter, and direct the clerk to read charges."
    )

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def build_judge_closing_prompt(
    context: Dict[str, Any],
    judge_persona: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, str]]:
    """Generate messages for the judge's pre-deliberation charge to the jury."""
    title = (
        judge_persona.get("title", "Presiding Sessions Judge")
        if judge_persona
        else "Presiding Sessions Judge"
    )

    system_prompt = (
        f"You are the {title}. You have heard the evidence and closing arguments. "
        "Summarize the legal standard for the jury. Remind them that the burden of proof "
        "rests solely on the prosecution to establish guilt beyond reasonable doubt, "
        "and instruct them to retire for deliberation. Impartial and under 120 words."
    )

    user_prompt = (
        f"Case: {context['case_title']}\n"
        f"Charge: {context['charge']}\n\n"
        "Deliver your closing charge and instructions to the jury."
    )

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
