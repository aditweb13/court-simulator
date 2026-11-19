"""Three-stage statutory courtroom case generator with caching and validation."""

from __future__ import annotations

import hashlib
import logging
import uuid
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agents.witness_memory import build_witness_memory
from app.casegen.schemas import (
    CaseGenerateRequest,
    Stage1TruthOutput,
    Stage2EvidenceOutput,
    Stage3WitnessesOutput,
)
from app.cases.validator import CaseValidationError, assert_case_valid
from app.db.models.case import Case, Evidence, Witness
from app.llm.router import chat
from app.rag.retriever import RetrievedChunk, retrieve
from app.schemas.case import CaseSchema, TruthData

logger = logging.getLogger("app.casegen")


def compute_generation_hash(req: CaseGenerateRequest) -> str:
    """Compute a deterministic 12-char hex hash from generation parameters."""
    norm = f"{req.topic.strip().lower()}:{req.difficulty}:{req.jurisdiction.strip().lower()}"
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()[:12]


async def generate_case(
    db: AsyncSession,
    request: CaseGenerateRequest,
    user_id: Optional[UUID] = None,
) -> Case:
    """Generate a valid courtroom case across three staged LLM inferences.

    Flow:
    1. Check parameter cache: return existing case if hash matches.
    2. Retrieve statutory context from the knowledge base using topic query.
    3. Stage 1: Generate objective ground truth, timeline (>= 2024-07-01), and charge.
       Enforces that cited section was genuinely retrieved.
    4. Stage 2: Generate admitted and inadmissible evidence exhibits.
    5. Stage 3: Generate witnesses with bounded memory slices (saw_event_ids).
    6. Validate cross-entity integrity rules.
    7. Persist to PostgreSQL under source='generated' and return Case.
    """
    cache_hash = compute_generation_hash(request)
    slug = f"gen-{cache_hash}"

    # 1. Cache lookup
    stmt = (
        select(Case)
        .options(selectinload(Case.evidence), selectinload(Case.witnesses))
        .where(Case.slug == slug)
    )
    res = await db.execute(stmt)
    cached_case = res.scalar_one_or_none()
    if cached_case is not None:
        logger.info("Casegen: cache hit for slug '%s' (hash: %s)", slug, cache_hash)
        return cached_case

    logger.info("Casegen: generating new case for topic '%s' (slug: %s)", request.topic, slug)

    # 2. Retrieve statutory grounding
    retrieved_chunks: List[RetrievedChunk] = []
    try:
        retrieved_chunks = await retrieve(
            query=request.topic,
            role="judge",
            k=5,
            session=db,
        )
    except Exception as exc:
        logger.warning("Statutory retrieval failed during case generation: %s", exc)

    retrieved_sections = {
        chunk.section_no.strip()
        for chunk in retrieved_chunks
        if getattr(chunk, "section_no", None) and chunk.section_no.strip()
    }
    retrieved_texts = [
        f"[{c.act} Section {c.section_no}] {c.title}: "
        f"{(getattr(c, 'body', '') or getattr(c, 'content', ''))[:160]}..."
        for c in retrieved_chunks
    ]

    statute_context_block = (
        "Statutory Knowledge Chunks Retrieved:\n" + "\n".join(retrieved_texts)
        if retrieved_texts
        else "No specific statutory chunks found."
    )

    # 3. Stage 1: Ground Truth, Timeline & Offence
    s1_system_prompt = (
        "You are an Indian criminal jurisprudence case architect. "
        "Create the objective ground truth and timeline for a trial under BNS, 2023. "
        "CRITICAL RULES:\n"
        "1. Offence dates MUST be on or after 2024-07-01 (when BNS took effect).\n"
        "2. The charged section MUST be selected directly from the retrieved sections.\n"
        "3. The culprit MUST be an actor who actively appears in the timeline events.\n"
        "4. Provide at least 3 chronological timeline events."
    )
    s1_user_prompt = (
        f"Topic / Scenario: {request.topic}\n"
        f"Difficulty: {request.difficulty} of 5\n"
        f"Jurisdiction: {request.jurisdiction}\n\n"
        f"{statute_context_block}\n\n"
        "Generate Stage 1 truth: title, slug, charge description, cited_section, "
        "culprit, motive, summary, and timeline."
    )

    s1_output: Stage1TruthOutput = await chat(
        tier="strong",
        messages=[
            {"role": "system", "content": s1_system_prompt},
            {"role": "user", "content": s1_user_prompt},
        ],
        response_model=Stage1TruthOutput,
    )

    # Statutory citation gate: cited section must be in retrieved sections
    cleaned_section = s1_output.cited_section.strip().replace("Section", "").strip()
    section_matched = any(
        cleaned_section == sec or cleaned_section in sec or sec in cleaned_section
        for sec in retrieved_sections
    )
    if retrieved_sections and not section_matched:
        raise CaseValidationError(
            f"Statutory citation violation: cited section '{s1_output.cited_section}' "
            f"was not present in retrieved knowledge sections {list(retrieved_sections)}."
        )

    # 4. Stage 2: Evidence List
    s2_system_prompt = (
        "You are an Indian criminal evidentiary architect. "
        "Based on the objective ground truth timeline, create physical and documentary evidence. "
        "CRITICAL RULE: At least ONE exhibit MUST be legally inadmissible under BSA, 2023 "
        "(e.g., Section 23 confession to police, Section 63 electronic record without certificate, "
        "or Section 55 hearsay), complete with the legal reason_inadmissible."
    )
    timeline_summary = "\n".join(
        f"Event {e.id} [{e.time}] ({e.location}): {e.description} (Actors: {', '.join(e.actors)})"
        for e in s1_output.timeline
    )
    s2_user_prompt = (
        f"Case: {s1_output.title}\n"
        f"Charge: {s1_output.charge}\n"
        f"Culprit: {s1_output.culprit}\n\n"
        f"Timeline:\n{timeline_summary}\n\n"
        "Generate Stage 2 evidence exhibits list (at least 2 exhibits, at least 1 inadmissible)."
    )

    s2_output: Stage2EvidenceOutput = await chat(
        tier="strong",
        messages=[
            {"role": "system", "content": s2_system_prompt},
            {"role": "user", "content": s2_user_prompt},
        ],
        response_model=Stage2EvidenceOutput,
    )

    # 5. Stage 3: Witnesses
    s3_system_prompt = (
        "You are an Indian criminal witness architect. "
        "Create witnesses for this trial. "
        "CRITICAL RULES:\n"
        "1. Every saw_event_ids list MUST only contain event IDs that exist in the timeline.\n"
        "2. Reliability score must be between 0.0 and 1.0.\n"
        "3. Hides list specifies lies or sensitive facts the witness withholds unless pressed.\n"
        "4. Witnesses must have distinct personas."
    )
    timeline_ids_str = ", ".join(str(e.id) for e in s1_output.timeline)
    s3_user_prompt = (
        f"Case: {s1_output.title}\n"
        f"Valid Timeline Event IDs: [{timeline_ids_str}]\n\n"
        f"Timeline:\n{timeline_summary}\n\n"
        "Generate Stage 3 witnesses (at least 2 witnesses)."
    )

    s3_output: Stage3WitnessesOutput = await chat(
        tier="strong",
        messages=[
            {"role": "system", "content": s3_system_prompt},
            {"role": "user", "content": s3_user_prompt},
        ],
        response_model=Stage3WitnessesOutput,
    )

    # 6. Assemble Full Case Schema & Validate
    case_schema = CaseSchema(
        slug=slug,
        title=s1_output.title,
        jurisdiction=request.jurisdiction,
        charge=s1_output.charge,
        difficulty=request.difficulty,
        source="generated",
        truth=TruthData(
            culprit=s1_output.culprit,
            motive=s1_output.motive,
            timeline=s1_output.timeline,
            summary=s1_output.summary,
        ),
        evidence=s2_output.evidence,
        witnesses=s3_output.witnesses,
    )

    # Run complete integrity validation
    assert_case_valid(case_schema)

    # Verify witness memory slice isolation
    for w in case_schema.witnesses:
        w_mem = build_witness_memory(w, case_schema.truth.timeline)
        saw_set = set(w.saw_event_ids)
        for mem_ev in w_mem.memories:
            if mem_ev.event_id not in saw_set:
                raise CaseValidationError(
                    f"Isolation breach: witness '{w.name}' memory contains event "
                    f"{mem_ev.event_id} outside saw_event_ids {w.saw_event_ids}."
                )

    # 7. Persist to Database
    case_row = Case(
        id=uuid.uuid4(),
        slug=slug,
        title=case_schema.title,
        jurisdiction=case_schema.jurisdiction,
        charge=case_schema.charge,
        difficulty=case_schema.difficulty,
        truth=case_schema.truth.model_dump(),
        source="generated",
    )
    db.add(case_row)
    await db.flush()

    for ev in case_schema.evidence:
        ev_row = Evidence(
            id=uuid.uuid4(),
            case_id=case_row.id,
            exhibit_no=ev.exhibit_no,
            type=ev.type,
            description=ev.description,
            admissible=ev.admissible,
            reason_inadmissible=ev.reason_inadmissible,
        )
        db.add(ev_row)

    for wit in case_schema.witnesses:
        wit_row = Witness(
            id=uuid.uuid4(),
            case_id=case_row.id,
            name=wit.name,
            saw_event_ids=wit.saw_event_ids,
            reliability=wit.reliability,
            hides=wit.hides,
            persona=wit.persona,
        )
        db.add(wit_row)

    await db.commit()

    # Re-query with eager loads
    stmt = (
        select(Case)
        .options(selectinload(Case.evidence), selectinload(Case.witnesses))
        .where(Case.id == case_row.id)
    )
    res = await db.execute(stmt)
    persisted = res.scalar_one()
    return persisted
