"""Context filter and prompt builder for the Public Prosecutor.

The Public Prosecutor receives:
- Case public facts (title, jurisdiction, charges, summary)
- Admitted prosecution evidence exhibits
- Admitted turns / trial record (omitting struck turns)
- Private prosecution strategy notes (proof of statutory elements beyond reasonable doubt)
- Retrieved statutory law chunks (with role='lawyer')

Information Isolation Rule:
The prosecutor NEVER receives the hidden ground truth (`case.truth`), defense's
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
from app.db.models.trial import Turn
from app.rag.retriever import retrieve

logger = logging.getLogger("app.context.prosecutor")


async def build_prosecutor_context(
    db: AsyncSession,
    trial_id: UUID,
    case_id: UUID,
    witness_name: Optional[str] = None,
    query_topic: Optional[str] = None,
) -> Dict[str, Any]:
    """Assemble isolated adversarial context for the Public Prosecutor."""
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

    # 3. Retrieve relevant statutory law chunks with role='lawyer'
    retrieval_query = query_topic or f"{case_row.charge} prosecution elements evidence BSA 2023"
    try:
        retrieved_chunks = await retrieve(
            query=retrieval_query,
            role="lawyer",
            k=5,
            session=db,
        )
    except Exception as exc:
        logger.warning("Statutory retrieval for prosecutor failed, falling back to empty: %s", exc)
        retrieved_chunks = []

    # 4. Fetch admitted, non-struck turns (the clean court record)
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

    # 5. Witness roster for reference
    witness_roster = [{"name": w.name, "persona": w.persona} for w in case_row.witnesses]

    # 6. Synthesize adversarial private strategy notes
    private_notes = [
        f"Burden of Proof: Establish every element of {case_row.charge} beyond reasonable doubt.",
        "Maintain focus on physical corroboration, witness demeanor, and timeline consistency.",
        "Object under BSA 2023 if defense asks leading questions on direct or offers hearsay.",
    ]
    if witness_name:
        private_notes.append(
            f"Target Witness: {witness_name}. Anchor their testimony to admitted exhibits."
        )

    return {
        "case_title": case_row.title,
        "charge": case_row.charge,
        "jurisdiction": case_row.jurisdiction,
        "evidence": admitted_evidence,
        "statutes": [getattr(c, "content", str(c)) for c in retrieved_chunks],
        "record": record,
        "witnesses": witness_roster,
        "private_notes": private_notes,
    }


def build_prosecutor_examination_prompt(
    ctx: Dict[str, Any],
    witness_name: str,
    stage: str,
) -> List[Dict[str, str]]:
    """Prompt for the prosecutor conducting direct or cross examination."""
    system_prompt = (
        "You are the Public Prosecutor in an Indian Sessions Court governed by the Bharatiya "
        "Nagarik Suraksha Sanhita (BNSS), 2023 and the Bharatiya Sakshya Adhiniyam (BSA), 2023.\n\n"
        f"Case: {ctx['case_title']}\n"
        f"Charge: {ctx['charge']}\n"
        f"Jurisdiction: {ctx['jurisdiction']}\n\n"
        "Prosecution Theory & Strategy Notes:\n"
        + "\n".join(f"- {n}" for n in ctx.get("private_notes", []))
        + "\n\nAdmitted Evidence:\n"
        + "\n".join(
            f"- Exhibit {e['exhibit_no']} ({e['type']}): {e['description']}"
            for e in ctx.get("evidence", [])
        )
    )

    stage_desc = (
        "Examination-in-Chief (Direct Examination). "
        "Leading questions are PROHIBITED under BSA Section 146. "
        "Ask open-ended questions allowing the witness to state what they observed."
        if stage == "direct"
        else (
            "Cross-Examination. Leading questions ARE PERMITTED under BSA Section 146(3). "
            "Probe inconsistencies and secure admissions supporting the prosecution."
        )
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


def build_prosecutor_objection_prompt(
    ctx: Dict[str, Any],
    opposing_question: str,
    stage: str,
) -> List[Dict[str, str]]:
    """Prompt for the prosecutor evaluating an objection to a defense question."""
    system_prompt = (
        "You are the Public Prosecutor in an Indian criminal trial.\n"
        "You must protect the record and object to improper defense questions under BSA 2023.\n"
        "Grounds: hearsay (BSA 55), leading in direct (BSA 146), relevance (BSA 3-14), "
        "badgering/annoying (BSA 154), speculation (BSA 39), character (BSA 50-52).\n"
        "Only raise an objection if there is a genuine, clear statutory violation."
    )

    user_prompt = (
        f"Defense counsel just asked this question during {stage} examination:\n"
        f'"{opposing_question}"\n\n'
        "Evaluate whether this question violates courtroom rules under the BSA 2023.\n"
        "Respond with structured output indicating whether to raise an objection, "
        "the ground, the statutory section, and your argument."
    )

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def build_prosecutor_closing_prompt(
    ctx: Dict[str, Any],
) -> List[Dict[str, str]]:
    """Prompt for the prosecutor delivering final closing arguments."""
    system_prompt = (
        "You are the Public Prosecutor delivering closing arguments in an Indian Sessions Court. "
        "Argue that the prosecution proved guilt beyond reasonable doubt under BNS."
    )

    user_prompt = (
        f"Case: {ctx['case_title']}\n"
        f"Charge: {ctx['charge']}\n\n"
        "Admitted Exhibits:\n"
        + "\n".join(
            f"- Exhibit {e['exhibit_no']}: {e['description']}" for e in ctx.get("evidence", [])
        )
        + "\n\nPrivate Strategy Notes:\n"
        + "\n".join(f"- {n}" for n in ctx.get("private_notes", []))
        + "\n\nDeliver a formal closing argument under 150 words summing up culpability."
    )

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
