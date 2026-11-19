"""Context filter and prompt builder for the Defense Counsel.

The Defense Counsel receives:
- Case public facts (title, jurisdiction, charges, summary)
- Admitted evidence exhibits
- Admitted turns / trial record (omitting struck turns)
- Defendant persona & defense theory
- Private defense strategy notes (raising reasonable doubt, challenging credibility)
- Retrieved statutory law chunks (with role='lawyer')

Information Isolation Rule:
The defense counsel NEVER receives the hidden ground truth (`case.truth`), prosecution's
private notes/memories, or struck testimony.
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

logger = logging.getLogger("app.context.defense")


async def build_defense_context(
    db: AsyncSession,
    trial_id: UUID,
    case_id: UUID,
    witness_name: Optional[str] = None,
    query_topic: Optional[str] = None,
) -> Dict[str, Any]:
    """Assemble isolated adversarial context for the Defense Advocate."""
    # 1. Load case public facts and evidence (excluding hidden truth!)
    case_stmt = (
        select(Case)
        .options(selectinload(Case.evidence), selectinload(Case.witnesses))
        .where(Case.id == case_id)
    )
    case_res = await db.execute(case_stmt)
    case_row = case_res.scalar_one_or_none()
    if case_row is None:
        raise ValueError(f"Case '{case_id}' not found")

    # 2. Filter admitted evidence
    admitted_evidence = [
        {
            "exhibit_no": ev.exhibit_no,
            "type": ev.type,
            "description": ev.description,
        }
        for ev in case_row.evidence
        if ev.admissible
    ]

    # 3. Load Defendant Persona from Agents
    defendant_stmt = select(Agent).where(Agent.trial_id == trial_id, Agent.role == "defendant")
    def_res = await db.execute(defendant_stmt)
    defendant_agent = def_res.scalar_one_or_none()
    defendant_info = defendant_agent.persona if defendant_agent else {"name": "The Accused"}

    # 4. Retrieve relevant statutory law chunks with role='lawyer'
    retrieval_query = (
        query_topic or f"{case_row.charge} defense exceptions reasonable doubt BSA 2023"
    )
    try:
        retrieved_chunks = await retrieve(
            query=retrieval_query,
            role="lawyer",
            k=5,
            session=db,
        )
    except Exception as exc:
        logger.warning("Statutory retrieval for defense failed, falling back to empty: %s", exc)
        retrieved_chunks = []

    # 5. Fetch admitted, non-struck turns (clean court record)
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
    record = [{"speaker": t.speaker_role, "text": t.text} for t in turns]

    # 6. Synthesize adversarial defense strategy notes
    private_notes = [
        "Presumption of Innocence: The accused is presumed innocent until proven guilty.",
        "Highlight gaps in prosecution timeline and lack of corroboration.",
        "Object if prosecution asks leading questions on direct or lacks BSA 63 certificate.",
    ]
    if witness_name:
        private_notes.append(
            f"Target Witness: {witness_name}. Probe discrepancies with earlier statements."
        )

    return {
        "case_title": case_row.title,
        "charge": case_row.charge,
        "jurisdiction": case_row.jurisdiction,
        "defendant": defendant_info,
        "evidence": admitted_evidence,
        "statutes": [getattr(c, "content", str(c)) for c in retrieved_chunks],
        "record": record,
        "private_notes": private_notes,
    }


def build_defense_examination_prompt(
    ctx: Dict[str, Any],
    witness_name: str,
    stage: str,
) -> List[Dict[str, str]]:
    """Prompt for defense counsel conducting cross-examination or direct examination."""
    system_prompt = (
        "You are the Defense Counsel in an Indian Sessions Court governed by the Bharatiya "
        "Nagarik Suraksha Sanhita (BNSS), 2023 and Bharatiya Sakshya Adhiniyam (BSA), 2023.\n\n"
        f"Case: {ctx['case_title']}\n"
        f"Charge: {ctx['charge']}\n"
        f"Defendant: {ctx.get('defendant', {}).get('name', 'The Accused')}\n\n"
        "Defense Strategy & Private Notes:\n"
        + "\n".join(f"- {n}" for n in ctx.get("private_notes", []))
        + "\n\nAdmitted Evidence:\n"
        + "\n".join(
            f"- Exhibit {e['exhibit_no']} ({e['type']}): {e['description']}"
            for e in ctx.get("evidence", [])
        )
    )

    stage_desc = (
        "Cross-Examination. Under Section 146(3) of the Bharatiya Sakshya Adhiniyam, 2023, "
        "leading questions ARE PERMITTED. Use sharp, leading, closed questions to test veracity, "
        "expose contradictions, and elicit reasonable doubt."
        if stage == "cross"
        else "Examination-in-Chief. Leading questions are PROHIBITED under BSA Section 146. "
        "Guide the witness naturally to establish the defense case."
    )

    user_prompt = (
        f"You are examining witness {witness_name}.\n"
        f"Stage: {stage_desc}\n\n"
        "Recent Court Record:\n"
        + "\n".join(f"{r['speaker']}: {r['text']}" for r in ctx.get("record", [])[-6:])
        + (
            "\n\nFormulate your next single spoken question to the witness, "
            "along with your tactical private note."
        )
    )

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def build_defense_objection_prompt(
    ctx: Dict[str, Any],
    opposing_question: str,
    stage: str,
) -> List[Dict[str, str]]:
    """Prompt for defense counsel evaluating an objection to a prosecutor question."""
    system_prompt = (
        "You are the Defense Counsel in an Indian criminal trial. "
        "Your duty is to protect the accused's constitutional and statutory rights "
        "under the Bharatiya Sakshya Adhiniyam, 2023 (BSA).\n"
        "Grounds: hearsay (BSA 55), leading in direct (BSA 146), relevance (BSA 3-14), "
        "badgering/annoying (BSA 154), speculation (BSA 39), character (BSA 50-52).\n"
        "Only raise an objection if there is a clear statutory violation."
    )

    user_prompt = (
        f"The Prosecutor just asked this question during {stage} examination:\n"
        f'"{opposing_question}"\n\n'
        "Evaluate whether this question violates courtroom rules under the BSA 2023.\n"
        "Respond with structured output indicating whether to raise an objection, "
        "the ground, the statutory section, and your argument."
    )

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def build_defense_closing_prompt(
    ctx: Dict[str, Any],
) -> List[Dict[str, str]]:
    """Prompt for the defense counsel delivering final closing arguments."""
    system_prompt = (
        "You are the Defense Counsel delivering closing arguments in an Indian Sessions Court. "
        "Your duty is to argue that the prosecution has failed to eliminate reasonable doubt."
    )

    user_prompt = (
        f"Case: {ctx['case_title']}\n"
        f"Charge: {ctx['charge']}\n"
        f"Defendant: {ctx.get('defendant', {}).get('name', 'The Accused')}\n\n"
        "Private Strategy Notes:\n"
        + "\n".join(f"- {n}" for n in ctx.get("private_notes", []))
        + "\n\nDeliver a compelling, formal closing argument under 150 words urging an acquittal."
    )

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
