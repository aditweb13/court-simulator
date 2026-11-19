"""LangGraph node functions for the courtroom orchestrator.

Each node receives and returns a CourtroomState dict. Nodes call the LLM
router's ``chat()`` for dialogue generation, persist Turn rows to the DB,
and dispatch LineEvent / StateEvent over WebSocket.

Phase 5 implements: setup_node, openings_node, closings_node.
Phase 6 adds: examination_node.
Phase 7 adds: deliberation_node, verdict_node.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.context.clerk import build_clerk_context, build_clerk_opening_prompt
from app.context.defense import (
    build_defense_closing_prompt,
    build_defense_context,
    build_defense_examination_prompt,
    build_defense_objection_prompt,
)
from app.context.judge import (
    build_judge_closing_prompt,
    build_judge_context,
    build_judge_opening_prompt,
)
from app.context.prosecutor import (
    build_prosecutor_closing_prompt,
    build_prosecutor_context,
    build_prosecutor_examination_prompt,
    build_prosecutor_objection_prompt,
)
from app.context.witness import build_witness_answer_prompt, build_witness_context
from app.db.models.case import Case
from app.db.models.trial import Agent, Trial, Turn, TurnEmbedding
from app.llm.router import chat
from app.orchestrator.schemas import (
    ClerkAnnouncementOutput,
    ClosingArgumentOutput,
    ExaminationQuestionOutput,
    JudgeClosingOutput,
    JudgeOpeningOutput,
    ObjectionOutput,
    WitnessAnswerOutput,
)
from app.orchestrator.state import CourtroomState, TrialPhase
from app.rag.embeddings import get_embedder
from app.rules import (
    check_objection_quota,
    get_statutory_basis,
    is_leading_question_permitted,
    is_valid_objection_ground,
)
from app.ws.connection import manager as ws_manager
from app.ws.schemas import LineEvent, RulingEvent, StateEvent

logger = logging.getLogger("app.orchestrator")


async def _get_agent_by_role(
    db: AsyncSession,
    trial_id: UUID,
    role: str,
    name: Optional[str] = None,
) -> Optional[Agent]:
    """Fetch an agent row by trial and role.

    If name is provided, matches persona['name'] (for multi-agent roles like witness/juror).
    Otherwise returns the first matching agent.
    """
    stmt = select(Agent).where(Agent.trial_id == trial_id, Agent.role == role)
    result = await db.execute(stmt)
    agents = result.scalars().all()
    if not agents:
        return None
    if name:
        for a in agents:
            if isinstance(a.persona, dict) and a.persona.get("name") == name:
                return a
    return agents[0]


async def _persist_turn(
    db: AsyncSession,
    trial_id: UUID,
    seq: int,
    agent_id: Optional[UUID],
    speaker_role: str,
    text: str,
    action: Optional[str] = None,
    emotion: Optional[str] = None,
    camera: Optional[str] = "wide",
    objection: Optional[Dict[str, Any]] = None,
    admitted: bool = True,
    struck: bool = False,
) -> Turn:
    """Create, flush, and embed a Turn row."""
    turn = Turn(
        trial_id=trial_id,
        seq=seq,
        agent_id=agent_id,
        speaker_role=speaker_role,
        text=text,
        action=action,
        emotion=emotion,
        camera=camera,
        objection=objection,
        admitted=admitted,
        struck=struck,
    )
    db.add(turn)
    await db.flush()

    # Persist vector embedding for juror retrieval
    try:
        embedder = get_embedder()
        emb_vec = embedder.embed_query(text)
        turn_emb = TurnEmbedding(
            turn_id=turn.id,
            trial_id=trial_id,
            embedding=emb_vec,
        )
        db.add(turn_emb)
        await db.flush()
    except Exception as exc:
        logger.warning("Failed to store embedding for turn %d: %s", seq, exc)

    return turn


async def mark_turn_struck(
    db: AsyncSession,
    trial_id: UUID,
    seq: int,
) -> None:
    """Flag a turn as struck from the court record following a sustained objection."""
    stmt = select(Turn).where(Turn.trial_id == trial_id, Turn.seq == seq)
    res = await db.execute(stmt)
    turn_row = res.scalar_one_or_none()
    if turn_row:
        turn_row.struck = True
        await db.flush()
        logger.info("Marked turn seq %d struck for trial %s", seq, trial_id)


async def _send_line(
    trial_id: UUID,
    seq: int,
    speaker: str,
    text: str,
    action: Optional[str] = None,
    emotion: Optional[str] = None,
    camera: Optional[str] = "wide",
) -> None:
    """Dispatch a LineEvent to all connected WebSocket clients."""
    event = LineEvent(
        seq=seq,
        speaker=speaker,
        text=text,
        action=action,
        emotion=emotion,
        camera=camera,
    )
    await ws_manager.send_event(trial_id, event)


async def _send_state(
    trial_id: UUID,
    new_state: str,
    previous_state: Optional[str] = None,
) -> None:
    """Dispatch a StateEvent to all connected WebSocket clients."""
    event = StateEvent(
        state=new_state,
        previous_state=previous_state,
    )
    await ws_manager.send_event(trial_id, event)


async def _update_trial_state(
    db: AsyncSession,
    trial_id: UUID,
    new_state: str,
) -> None:
    """Update the trial's state column in the database."""
    stmt = select(Trial).where(Trial.id == trial_id)
    result = await db.execute(stmt)
    trial = result.scalar_one_or_none()
    if trial:
        trial.state = new_state
        await db.flush()


async def _send_and_wait_ack(
    trial_id: UUID,
    seq: int,
    speaker: str,
    text: str,
    action: Optional[str] = None,
    emotion: Optional[str] = None,
    camera: Optional[str] = "wide",
    timeout: Optional[float] = None,
) -> bool:
    """Send a line event and await client acknowledgment if connected.

    Returns True if ack was received or no client is connected (headless mode).
    Returns False if client timed out or died.
    """
    await _send_line(
        trial_id=trial_id,
        seq=seq,
        speaker=speaker,
        text=text,
        action=action,
        emotion=emotion,
        camera=camera,
    )

    if not ws_manager.is_connected(trial_id):
        return True

    ack_timeout = timeout if timeout is not None else settings.ack_timeout_seconds
    ack_received = await ws_manager.wait_for_ack(trial_id, seq, timeout=ack_timeout)
    if not ack_received:
        logger.warning(
            "Trial %s: client ack timeout (%.1fs) on seq %d. Pausing trial.",
            trial_id,
            ack_timeout,
            seq,
        )
        return False
    return True


async def _pause_trial(
    db: AsyncSession,
    state: CourtroomState,
    trial_id: UUID,
) -> CourtroomState:
    """Transition trial to PAUSED state on dead client or ack timeout."""
    previous = state["current_phase"]
    await _update_trial_state(db, trial_id, "PAUSED")
    await _send_state(trial_id, "PAUSED", previous)
    await db.commit()
    return {
        **state,
        "is_paused": True,
        "previous_phase": previous,
    }


# ---------------------------------------------------------------------------
# Node: SETUP
# ---------------------------------------------------------------------------


async def setup_node(
    state: CourtroomState,
    db: AsyncSession,
) -> CourtroomState:
    """Load case metadata and agents, transition to OPENINGS.

    This node does not generate any dialogue — it prepares the state
    for the openings node by confirming the trial and case exist.
    """
    trial_id = state["trial_id"]
    logger.info("setup_node: initializing trial %s", trial_id)

    # Verify trial exists and load case
    stmt = (
        select(Trial)
        .options(selectinload(Trial.case), selectinload(Trial.agents))
        .where(Trial.id == trial_id)
    )
    result = await db.execute(stmt)
    trial = result.scalar_one_or_none()

    if trial is None:
        return {
            **state,
            "error": f"Trial {trial_id} not found",
            "current_phase": TrialPhase.FINISHED.value,
        }

    # Transition to OPENINGS
    previous = state["current_phase"]
    new_phase = TrialPhase.OPENINGS.value

    await _update_trial_state(db, trial_id, new_phase)
    await _send_state(trial_id, new_phase, previous)
    await db.commit()

    logger.info("setup_node: trial %s transitioning %s → %s", trial_id, previous, new_phase)

    return {
        **state,
        "case_id": trial.case_id,
        "current_phase": new_phase,
        "previous_phase": previous,
    }


# ---------------------------------------------------------------------------
# Node: OPENINGS
# ---------------------------------------------------------------------------


async def openings_node(
    state: CourtroomState,
    db: AsyncSession,
) -> CourtroomState:
    """Generate judge opening statement and clerk charge reading.

    Flow:
    1. Judge delivers opening statement (LLM call, strong tier)
    2. Clerk reads the charges (LLM call, mid tier)
    Both are persisted as Turn rows and dispatched as LineEvents.
    """
    trial_id = state["trial_id"]
    case_id = state["case_id"]
    seq = state["turn_seq"]
    logger.info("openings_node: trial %s, starting at seq %d", trial_id, seq)

    # Load case for charge text
    case_stmt = select(Case).where(Case.id == case_id)
    case_result = await db.execute(case_stmt)
    case_row = case_result.scalar_one_or_none()
    if case_row is None:
        return {**state, "error": f"Case {case_id} not found"}

    # Fetch judge and clerk agents
    judge_agent = await _get_agent_by_role(db, trial_id, "judge")
    clerk_agent = await _get_agent_by_role(db, trial_id, "clerk")

    turns_generated: List[Dict[str, Any]] = list(state.get("turns", []))

    # --- 1. Judge opening statement ---
    judge_context = await build_judge_context(db, trial_id, case_id)
    judge_messages = build_judge_opening_prompt(
        judge_context,
        judge_agent.persona if judge_agent else None,
    )

    judge_output: JudgeOpeningOutput = await chat(
        tier="strong",
        messages=judge_messages,
        response_model=JudgeOpeningOutput,
        trial_id=trial_id,
        agent_role="judge",
    )

    # Persist judge turn
    await _persist_turn(
        db=db,
        trial_id=trial_id,
        seq=seq,
        agent_id=judge_agent.id if judge_agent else None,
        speaker_role="judge",
        text=judge_output.text,
        action=judge_output.action,
        emotion=judge_output.emotion,
        camera=judge_output.camera,
    )
    ack_ok = await _send_and_wait_ack(
        trial_id=trial_id,
        seq=seq,
        speaker="judge",
        text=judge_output.text,
        action=judge_output.action,
        emotion=judge_output.emotion,
        camera=judge_output.camera,
    )
    turns_generated.append({"seq": seq, "speaker": "judge", "text": judge_output.text})
    seq += 1

    if not ack_ok:
        return await _pause_trial(
            db,
            {**state, "turns": turns_generated, "turn_seq": seq},
            trial_id,
        )

    # --- 2. Clerk reads charges ---
    clerk_context = await build_clerk_context(db, trial_id, case_id)
    clerk_messages = build_clerk_opening_prompt(
        clerk_context,
        clerk_agent.persona if clerk_agent else None,
    )

    clerk_output: ClerkAnnouncementOutput = await chat(
        tier="mid",
        messages=clerk_messages,
        response_model=ClerkAnnouncementOutput,
        trial_id=trial_id,
        agent_role="clerk",
    )

    # Persist clerk turn
    await _persist_turn(
        db=db,
        trial_id=trial_id,
        seq=seq,
        agent_id=clerk_agent.id if clerk_agent else None,
        speaker_role="clerk",
        text=clerk_output.text,
        action=clerk_output.action,
        emotion=clerk_output.emotion,
        camera=clerk_output.camera,
    )
    clerk_ack_ok = await _send_and_wait_ack(
        trial_id=trial_id,
        seq=seq,
        speaker="clerk",
        text=clerk_output.text,
        action=clerk_output.action,
        emotion=clerk_output.emotion,
        camera=clerk_output.camera,
    )
    turns_generated.append({"seq": seq, "speaker": "clerk", "text": clerk_output.text})
    seq += 1

    if not clerk_ack_ok:
        return await _pause_trial(
            db,
            {**state, "turns": turns_generated, "turn_seq": seq},
            trial_id,
        )

    await db.commit()

    # Transition to next phase (EXAMINATION)
    previous = state["current_phase"]
    new_phase = TrialPhase.EXAMINATION.value
    await _update_trial_state(db, trial_id, new_phase)
    await _send_state(trial_id, new_phase, previous)
    await db.commit()

    logger.info(
        "openings_node: trial %s generated %d turns, transitioning to %s",
        trial_id,
        2,
        new_phase,
    )

    return {
        **state,
        "current_phase": new_phase,
        "previous_phase": previous,
        "turn_seq": seq,
        "turns": turns_generated,
        "active_speaker": "clerk",
    }


# ---------------------------------------------------------------------------
# Node: EXAMINATION
# ---------------------------------------------------------------------------


async def examination_node(
    state: CourtroomState,
    db: AsyncSession,
) -> CourtroomState:
    """Orchestrate witness examination (direct, cross, redirect), objections, and rulings.

    Under the Bharatiya Sakshya Adhiniyam, 2023 (BSA Section 142):
    1. Direct examination (examination-in-chief) by the calling party (Prosecutor).
       Leading questions are prohibited under BSA Section 146.
    2. Objection evaluation by opposing counsel (Defense). If an objection is raised:
       - Objection turn is persisted and broadcast to clients.
       - Judge evaluates and delivers formal Ruling (sustained or overruled).
       - If sustained, the impermissible question is marked struck from the record.
    3. Witness testifies from their personal memory slice (derived from saw_event_ids).
    4. Cross-examination by opposing counsel (Defense).
       Leading questions are permitted under BSA Section 146(3).
    5. Re-examination (Redirect) by calling party (Prosecutor).
    """
    trial_id = state["trial_id"]
    case_id = state["case_id"]
    seq = state["turn_seq"]
    logger.info("examination_node: trial %s, starting at seq %d", trial_id, seq)

    # 1. Load case with witnesses and evidence
    case_stmt = (
        select(Case)
        .options(selectinload(Case.witnesses), selectinload(Case.evidence))
        .where(Case.id == case_id)
    )
    case_result = await db.execute(case_stmt)
    case_row = case_result.scalar_one_or_none()
    if case_row is None:
        return {**state, "error": f"Case {case_id} not found"}

    # 2. Fetch participating agents
    prosecutor_agent = await _get_agent_by_role(db, trial_id, "prosecutor")
    defense_agent = await _get_agent_by_role(db, trial_id, "defense")
    judge_agent = await _get_agent_by_role(db, trial_id, "judge")

    turns_generated: List[Dict[str, Any]] = list(state.get("turns", []))
    defense_objections_count = 0
    prosecutor_objections_count = 0

    # 3. Examine witnesses (examine first available witness)
    witnesses = case_row.witnesses or []
    if not witnesses:
        logger.warning(
            "examination_node: trial %s has no witnesses, skipping to closings", trial_id
        )
    else:
        witness = witnesses[0]
        witness_name = witness.name
        witness_agent = await _get_agent_by_role(db, trial_id, "witness", name=witness_name)

        # --- A. DIRECT EXAMINATION (Prosecution) ---
        pros_ctx = await build_prosecutor_context(db, trial_id, case_id, witness_name=witness_name)
        pros_messages = build_prosecutor_examination_prompt(pros_ctx, witness_name, stage="direct")

        direct_q: ExaminationQuestionOutput = await chat(
            tier="strong",
            messages=pros_messages,
            response_model=ExaminationQuestionOutput,
            trial_id=trial_id,
            agent_role="prosecutor",
        )

        await _persist_turn(
            db=db,
            trial_id=trial_id,
            seq=seq,
            agent_id=prosecutor_agent.id if prosecutor_agent else None,
            speaker_role="prosecutor",
            text=direct_q.text,
            action=direct_q.action,
            emotion=direct_q.emotion,
            camera="prosecution",
        )
        ack_ok = await _send_and_wait_ack(
            trial_id=trial_id,
            seq=seq,
            speaker="prosecutor",
            text=direct_q.text,
            action=direct_q.action,
            emotion=direct_q.emotion,
            camera="prosecution",
        )
        turns_generated.append({"seq": seq, "speaker": "prosecutor", "text": direct_q.text})
        direct_q_seq = seq
        seq += 1

        if not ack_ok:
            return await _pause_trial(
                db, {**state, "turns": turns_generated, "turn_seq": seq}, trial_id
            )

        # --- B. DEFENSE OBJECTION EVALUATION ---
        def_ctx = await build_defense_context(db, trial_id, case_id, witness_name=witness_name)
        obj_messages = build_defense_objection_prompt(def_ctx, direct_q.text, stage="direct")

        obj_output: ObjectionOutput = await chat(
            tier="strong",
            messages=obj_messages,
            response_model=ObjectionOutput,
            trial_id=trial_id,
            agent_role="defense",
        )

        objection_sustained = False
        if obj_output.raise_objection and check_objection_quota(defense_objections_count):
            defense_objections_count += 1
            objection_ground = obj_output.objection_type or "hearsay"
            statutory_basis = (
                obj_output.legal_basis or get_statutory_basis(objection_ground) or "BSA 2023"
            )
            objection_text = (
                obj_output.argument
                or f"Objection, Your Honour! Impermissible under {statutory_basis}."
            )

            # Persist defense objection turn
            await _persist_turn(
                db=db,
                trial_id=trial_id,
                seq=seq,
                agent_id=defense_agent.id if defense_agent else None,
                speaker_role="defense",
                text=objection_text,
                action="stand",
                emotion="firm",
                camera="defense",
                objection={"type": objection_ground, "basis": statutory_basis},
            )
            ack_ok = await _send_and_wait_ack(
                trial_id=trial_id,
                seq=seq,
                speaker="defense",
                text=objection_text,
                action="stand",
                emotion="firm",
                camera="defense",
            )
            turns_generated.append({"seq": seq, "speaker": "defense", "text": objection_text})
            seq += 1

            if not ack_ok:
                return await _pause_trial(
                    db, {**state, "turns": turns_generated, "turn_seq": seq}, trial_id
                )

            # --- JUDGE RULES ON OBJECTION ---
            is_valid = is_valid_objection_ground(objection_ground)
            # Under Indian Law, leading questions on direct are strictly sustained
            if objection_ground == "leading" and not is_leading_question_permitted("direct"):
                objection_sustained = True
            elif is_valid:
                objection_sustained = True
            else:
                objection_sustained = False

            ruling_decision = "sustained" if objection_sustained else "overruled"
            ruling_text = f"Objection {ruling_decision.upper()}. " + (
                f"Under {statutory_basis}, question is improper; witness will not answer."
                if objection_sustained
                else "The question is permissible. The witness shall answer."
            )

            await _persist_turn(
                db=db,
                trial_id=trial_id,
                seq=seq,
                agent_id=judge_agent.id if judge_agent else None,
                speaker_role="judge",
                text=ruling_text,
                action="gavel",
                emotion="neutral",
                camera="judge",
                objection={
                    "ruling": ruling_decision,
                    "ground": objection_ground,
                    "struck": objection_sustained,
                },
            )
            # Broadcast official RulingEvent
            await ws_manager.send_event(
                trial_id,
                RulingEvent(
                    seq=seq,
                    objection_type=objection_ground,
                    ruling="sustained" if objection_sustained else "overruled",
                    struck=objection_sustained,
                    reason=ruling_text,
                ),
            )
            ack_ok = await _send_and_wait_ack(
                trial_id=trial_id,
                seq=seq,
                speaker="judge",
                text=ruling_text,
                action="gavel",
                emotion="neutral",
                camera="judge",
            )
            turns_generated.append({"seq": seq, "speaker": "judge", "text": ruling_text})
            seq += 1

            if objection_sustained:
                await mark_turn_struck(db, trial_id, direct_q_seq)

            if not ack_ok:
                return await _pause_trial(
                    db, {**state, "turns": turns_generated, "turn_seq": seq}, trial_id
                )

        # --- C. WITNESS ANSWERS DIRECT ---
        # If objection was sustained on the question, counsel asks a rephrased foundation question
        direct_question_for_witness = direct_q.text
        if objection_sustained:
            direct_question_for_witness = (
                f"Please tell the Court what you personally saw at the scene, {witness_name}."
            )

        w_ctx = await build_witness_context(db, trial_id, witness_name, direct_question_for_witness)
        w_messages = build_witness_answer_prompt(w_ctx)

        witness_answer: WitnessAnswerOutput = await chat(
            tier="mid",
            messages=w_messages,
            response_model=WitnessAnswerOutput,
            trial_id=trial_id,
            agent_role="witness",
        )

        await _persist_turn(
            db=db,
            trial_id=trial_id,
            seq=seq,
            agent_id=witness_agent.id if witness_agent else None,
            speaker_role="witness",
            text=witness_answer.text,
            action=witness_answer.action,
            emotion=witness_answer.emotion,
            camera="witness",
        )
        ack_ok = await _send_and_wait_ack(
            trial_id=trial_id,
            seq=seq,
            speaker="witness",
            text=witness_answer.text,
            action=witness_answer.action,
            emotion=witness_answer.emotion,
            camera="witness",
        )
        turns_generated.append({"seq": seq, "speaker": "witness", "text": witness_answer.text})
        seq += 1

        if not ack_ok:
            return await _pause_trial(
                db, {**state, "turns": turns_generated, "turn_seq": seq}, trial_id
            )

        # --- D. CROSS-EXAMINATION (Defense) ---
        def_ctx = await build_defense_context(db, trial_id, case_id, witness_name=witness_name)
        cross_messages = build_defense_examination_prompt(def_ctx, witness_name, stage="cross")

        cross_q: ExaminationQuestionOutput = await chat(
            tier="strong",
            messages=cross_messages,
            response_model=ExaminationQuestionOutput,
            trial_id=trial_id,
            agent_role="defense",
        )

        await _persist_turn(
            db=db,
            trial_id=trial_id,
            seq=seq,
            agent_id=defense_agent.id if defense_agent else None,
            speaker_role="defense",
            text=cross_q.text,
            action=cross_q.action,
            emotion=cross_q.emotion,
            camera="defense",
        )
        ack_ok = await _send_and_wait_ack(
            trial_id=trial_id,
            seq=seq,
            speaker="defense",
            text=cross_q.text,
            action=cross_q.action,
            emotion=cross_q.emotion,
            camera="defense",
        )
        turns_generated.append({"seq": seq, "speaker": "defense", "text": cross_q.text})
        cross_q_seq = seq
        seq += 1

        if not ack_ok:
            return await _pause_trial(
                db, {**state, "turns": turns_generated, "turn_seq": seq}, trial_id
            )

        # Prosecution evaluates objection to cross-examination question
        pros_ctx = await build_prosecutor_context(db, trial_id, case_id, witness_name=witness_name)
        pros_obj_messages = build_prosecutor_objection_prompt(pros_ctx, cross_q.text, stage="cross")
        pros_obj_output: ObjectionOutput = await chat(
            tier="strong",
            messages=pros_obj_messages,
            response_model=ObjectionOutput,
            trial_id=trial_id,
            agent_role="prosecutor",
        )

        objection_sustained = False
        if pros_obj_output.raise_objection and check_objection_quota(prosecutor_objections_count):
            prosecutor_objections_count += 1
            objection_ground = pros_obj_output.objection_type or "relevance"
            statutory_basis = (
                pros_obj_output.legal_basis or get_statutory_basis(objection_ground) or "BSA 2023"
            )
            objection_text = (
                pros_obj_output.argument
                or f"Objection, Your Honour! Impermissible under {statutory_basis}."
            )

            await _persist_turn(
                db=db,
                trial_id=trial_id,
                seq=seq,
                agent_id=prosecutor_agent.id if prosecutor_agent else None,
                speaker_role="prosecutor",
                text=objection_text,
                action="stand",
                emotion="firm",
                camera="prosecution",
                objection={"type": objection_ground, "basis": statutory_basis},
            )
            ack_ok = await _send_and_wait_ack(
                trial_id=trial_id,
                seq=seq,
                speaker="prosecutor",
                text=objection_text,
                action="stand",
                emotion="firm",
                camera="prosecution",
            )
            turns_generated.append({"seq": seq, "speaker": "prosecutor", "text": objection_text})
            seq += 1

            if not ack_ok:
                return await _pause_trial(
                    db, {**state, "turns": turns_generated, "turn_seq": seq}, trial_id
                )

            # Judge rules on prosecution objection
            if objection_ground == "leading" and is_leading_question_permitted("cross"):
                objection_sustained = False
            elif is_valid_objection_ground(objection_ground):
                objection_sustained = True
            else:
                objection_sustained = False

            ruling_decision = "sustained" if objection_sustained else "overruled"
            ruling_text = f"Objection {ruling_decision.upper()}. " + (
                f"Under {statutory_basis}, question is improper; counsel will rephrase."
                if objection_sustained
                else (
                    "Under Section 146(3) of BSA 2023, "
                    "leading questions are permitted on cross-examination."
                    if objection_ground == "leading"
                    else "The question is permissible. The witness shall answer."
                )
            )

            await _persist_turn(
                db=db,
                trial_id=trial_id,
                seq=seq,
                agent_id=judge_agent.id if judge_agent else None,
                speaker_role="judge",
                text=ruling_text,
                action="gavel",
                emotion="neutral",
                camera="judge",
                objection={
                    "ruling": ruling_decision,
                    "ground": objection_ground,
                    "struck": objection_sustained,
                },
            )
            await ws_manager.send_event(
                trial_id,
                RulingEvent(
                    seq=seq,
                    objection_type=objection_ground,
                    ruling="sustained" if objection_sustained else "overruled",
                    struck=objection_sustained,
                    reason=ruling_text,
                ),
            )
            ack_ok = await _send_and_wait_ack(
                trial_id=trial_id,
                seq=seq,
                speaker="judge",
                text=ruling_text,
                action="gavel",
                emotion="neutral",
                camera="judge",
            )
            turns_generated.append({"seq": seq, "speaker": "judge", "text": ruling_text})
            seq += 1

            if objection_sustained:
                await mark_turn_struck(db, trial_id, cross_q_seq)

            if not ack_ok:
                return await _pause_trial(
                    db, {**state, "turns": turns_generated, "turn_seq": seq}, trial_id
                )

        # Witness answers cross-examination
        w_cross_ctx = await build_witness_context(db, trial_id, witness_name, cross_q.text)
        w_cross_messages = build_witness_answer_prompt(w_cross_ctx)

        witness_cross_ans: WitnessAnswerOutput = await chat(
            tier="mid",
            messages=w_cross_messages,
            response_model=WitnessAnswerOutput,
            trial_id=trial_id,
            agent_role="witness",
        )

        await _persist_turn(
            db=db,
            trial_id=trial_id,
            seq=seq,
            agent_id=witness_agent.id if witness_agent else None,
            speaker_role="witness",
            text=witness_cross_ans.text,
            action="talk",
            emotion=witness_cross_ans.emotion,
            camera="witness",
        )
        ack_ok = await _send_and_wait_ack(
            trial_id=trial_id,
            seq=seq,
            speaker="witness",
            text=witness_cross_ans.text,
            action="talk",
            emotion=witness_cross_ans.emotion,
            camera="witness",
        )
        turns_generated.append({"seq": seq, "speaker": "witness", "text": witness_cross_ans.text})
        seq += 1

        if not ack_ok:
            return await _pause_trial(
                db, {**state, "turns": turns_generated, "turn_seq": seq}, trial_id
            )

        # --- E. REDIRECT EXAMINATION (Prosecution) ---
        pros_redirect_ctx = await build_prosecutor_context(
            db, trial_id, case_id, witness_name=witness_name
        )
        redirect_messages = build_prosecutor_examination_prompt(
            pros_redirect_ctx, witness_name, stage="redirect"
        )

        redirect_q: ExaminationQuestionOutput = await chat(
            tier="strong",
            messages=redirect_messages,
            response_model=ExaminationQuestionOutput,
            trial_id=trial_id,
            agent_role="prosecutor",
        )

        await _persist_turn(
            db=db,
            trial_id=trial_id,
            seq=seq,
            agent_id=prosecutor_agent.id if prosecutor_agent else None,
            speaker_role="prosecutor",
            text=redirect_q.text,
            action=redirect_q.action,
            emotion=redirect_q.emotion,
            camera="prosecution",
        )
        ack_ok = await _send_and_wait_ack(
            trial_id=trial_id,
            seq=seq,
            speaker="prosecutor",
            text=redirect_q.text,
            action=redirect_q.action,
            emotion=redirect_q.emotion,
            camera="prosecution",
        )
        turns_generated.append({"seq": seq, "speaker": "prosecutor", "text": redirect_q.text})
        redirect_q_seq = seq
        seq += 1

        if not ack_ok:
            return await _pause_trial(
                db, {**state, "turns": turns_generated, "turn_seq": seq}, trial_id
            )

        # Defense evaluates objection to redirect question
        def_redirect_ctx = await build_defense_context(
            db, trial_id, case_id, witness_name=witness_name
        )
        def_obj_messages = build_defense_objection_prompt(
            def_redirect_ctx, redirect_q.text, stage="redirect"
        )
        def_obj_output: ObjectionOutput = await chat(
            tier="strong",
            messages=def_obj_messages,
            response_model=ObjectionOutput,
            trial_id=trial_id,
            agent_role="defense",
        )

        objection_sustained = False
        if def_obj_output.raise_objection and check_objection_quota(defense_objections_count):
            defense_objections_count += 1
            objection_ground = def_obj_output.objection_type or "relevance"
            statutory_basis = (
                def_obj_output.legal_basis or get_statutory_basis(objection_ground) or "BSA 2023"
            )
            objection_text = (
                def_obj_output.argument
                or f"Objection, Your Honour! Impermissible under {statutory_basis}."
            )

            await _persist_turn(
                db=db,
                trial_id=trial_id,
                seq=seq,
                agent_id=defense_agent.id if defense_agent else None,
                speaker_role="defense",
                text=objection_text,
                action="stand",
                emotion="firm",
                camera="defense",
                objection={"type": objection_ground, "basis": statutory_basis},
            )
            ack_ok = await _send_and_wait_ack(
                trial_id=trial_id,
                seq=seq,
                speaker="defense",
                text=objection_text,
                action="stand",
                emotion="firm",
                camera="defense",
            )
            turns_generated.append({"seq": seq, "speaker": "defense", "text": objection_text})
            seq += 1

            if not ack_ok:
                return await _pause_trial(
                    db, {**state, "turns": turns_generated, "turn_seq": seq}, trial_id
                )

            # Judge rules on defense objection during redirect
            # Leading questions on redirect are PROHIBITED under BSA 146(1)
            if objection_ground == "leading" and not is_leading_question_permitted("redirect"):
                objection_sustained = True
            elif is_valid_objection_ground(objection_ground):
                objection_sustained = True
            else:
                objection_sustained = False

            ruling_decision = "sustained" if objection_sustained else "overruled"
            ruling_text = f"Objection {ruling_decision.upper()}. " + (
                f"Under {statutory_basis}, question is improper; counsel will rephrase."
                if objection_sustained
                else "The question is permissible. The witness shall answer."
            )

            await _persist_turn(
                db=db,
                trial_id=trial_id,
                seq=seq,
                agent_id=judge_agent.id if judge_agent else None,
                speaker_role="judge",
                text=ruling_text,
                action="gavel",
                emotion="neutral",
                camera="judge",
                objection={
                    "ruling": ruling_decision,
                    "ground": objection_ground,
                    "struck": objection_sustained,
                },
            )
            await ws_manager.send_event(
                trial_id,
                RulingEvent(
                    seq=seq,
                    objection_type=objection_ground,
                    ruling="sustained" if objection_sustained else "overruled",
                    struck=objection_sustained,
                    reason=ruling_text,
                ),
            )
            ack_ok = await _send_and_wait_ack(
                trial_id=trial_id,
                seq=seq,
                speaker="judge",
                text=ruling_text,
                action="gavel",
                emotion="neutral",
                camera="judge",
            )
            turns_generated.append({"seq": seq, "speaker": "judge", "text": ruling_text})
            seq += 1

            if objection_sustained:
                await mark_turn_struck(db, trial_id, redirect_q_seq)

            if not ack_ok:
                return await _pause_trial(
                    db, {**state, "turns": turns_generated, "turn_seq": seq}, trial_id
                )

        # Witness answers redirect
        w_redir_ctx = await build_witness_context(db, trial_id, witness_name, redirect_q.text)
        w_redir_messages = build_witness_answer_prompt(w_redir_ctx)

        witness_redir_ans: WitnessAnswerOutput = await chat(
            tier="mid",
            messages=w_redir_messages,
            response_model=WitnessAnswerOutput,
            trial_id=trial_id,
            agent_role="witness",
        )

        await _persist_turn(
            db=db,
            trial_id=trial_id,
            seq=seq,
            agent_id=witness_agent.id if witness_agent else None,
            speaker_role="witness",
            text=witness_redir_ans.text,
            action="talk",
            emotion=witness_redir_ans.emotion,
            camera="witness",
        )
        ack_ok = await _send_and_wait_ack(
            trial_id=trial_id,
            seq=seq,
            speaker="witness",
            text=witness_redir_ans.text,
            action="talk",
            emotion=witness_redir_ans.emotion,
            camera="witness",
        )
        turns_generated.append({"seq": seq, "speaker": "witness", "text": witness_redir_ans.text})
        seq += 1

        if not ack_ok:
            return await _pause_trial(
                db, {**state, "turns": turns_generated, "turn_seq": seq}, trial_id
            )

    # 4. Transition to CLOSINGS phase
    await db.commit()
    previous = TrialPhase.EXAMINATION.value
    new_phase = TrialPhase.CLOSINGS.value
    await _update_trial_state(db, trial_id, new_phase)
    await _send_state(trial_id, new_phase, previous)
    await db.commit()

    logger.info(
        "examination_node: trial %s finished examination, transitioning to %s (turn seq: %d)",
        trial_id,
        new_phase,
        seq,
    )

    return {
        **state,
        "current_phase": new_phase,
        "previous_phase": previous,
        "turn_seq": seq,
        "turns": turns_generated,
        "active_speaker": "witness",
    }


# ---------------------------------------------------------------------------
# Node: CLOSINGS
# ---------------------------------------------------------------------------


async def closings_node(
    state: CourtroomState,
    db: AsyncSession,
) -> CourtroomState:
    """Generate prosecution closing, defense closing, and judge summary.

    Phase 5 skeleton: uses generic prompts. Phase 6 will replace
    prosecution/defense with their full adversarial agent prompts.
    """
    trial_id = state["trial_id"]
    case_id = state["case_id"]
    seq = state["turn_seq"]
    logger.info("closings_node: trial %s, starting at seq %d", trial_id, seq)

    # Load case
    case_stmt = select(Case).where(Case.id == case_id)
    case_result = await db.execute(case_stmt)
    case_row = case_result.scalar_one_or_none()
    if case_row is None:
        return {**state, "error": f"Case {case_id} not found"}

    # Fetch agents
    prosecutor_agent = await _get_agent_by_role(db, trial_id, "prosecutor")
    defense_agent = await _get_agent_by_role(db, trial_id, "defense")
    judge_agent = await _get_agent_by_role(db, trial_id, "judge")

    turns_generated: List[Dict[str, Any]] = list(state.get("turns", []))

    # --- 1. Prosecution closing ---
    pros_closing_ctx = await build_prosecutor_context(db, trial_id, case_id)
    prosecution_messages = build_prosecutor_closing_prompt(pros_closing_ctx)

    prosecution_output: ClosingArgumentOutput = await chat(
        tier="strong",
        messages=prosecution_messages,
        response_model=ClosingArgumentOutput,
        trial_id=trial_id,
        agent_role="prosecutor",
    )

    await _persist_turn(
        db=db,
        trial_id=trial_id,
        seq=seq,
        agent_id=prosecutor_agent.id if prosecutor_agent else None,
        speaker_role="prosecutor",
        text=prosecution_output.text,
        action=prosecution_output.action,
        emotion=prosecution_output.emotion,
        camera=prosecution_output.camera,
    )
    pros_ack_ok = await _send_and_wait_ack(
        trial_id=trial_id,
        seq=seq,
        speaker="prosecutor",
        text=prosecution_output.text,
        action=prosecution_output.action,
        emotion=prosecution_output.emotion,
        camera=prosecution_output.camera,
    )
    turns_generated.append({"seq": seq, "speaker": "prosecutor", "text": prosecution_output.text})
    seq += 1

    if not pros_ack_ok:
        return await _pause_trial(
            db,
            {**state, "turns": turns_generated, "turn_seq": seq},
            trial_id,
        )

    # --- 2. Defense closing ---
    def_closing_ctx = await build_defense_context(db, trial_id, case_id)
    defense_messages = build_defense_closing_prompt(def_closing_ctx)

    defense_output: ClosingArgumentOutput = await chat(
        tier="strong",
        messages=defense_messages,
        response_model=ClosingArgumentOutput,
        trial_id=trial_id,
        agent_role="defense",
    )

    await _persist_turn(
        db=db,
        trial_id=trial_id,
        seq=seq,
        agent_id=defense_agent.id if defense_agent else None,
        speaker_role="defense",
        text=defense_output.text,
        action=defense_output.action,
        emotion=defense_output.emotion,
        camera=defense_output.camera,
    )
    def_ack_ok = await _send_and_wait_ack(
        trial_id=trial_id,
        seq=seq,
        speaker="defense",
        text=defense_output.text,
        action=defense_output.action,
        emotion=defense_output.emotion,
        camera=defense_output.camera,
    )
    turns_generated.append({"seq": seq, "speaker": "defense", "text": defense_output.text})
    seq += 1

    if not def_ack_ok:
        return await _pause_trial(
            db,
            {**state, "turns": turns_generated, "turn_seq": seq},
            trial_id,
        )

    # --- 3. Judge closing summary ---
    judge_context = await build_judge_context(db, trial_id, case_id)
    judge_close_messages = build_judge_closing_prompt(
        judge_context,
        judge_agent.persona if judge_agent else None,
    )

    judge_close_output: JudgeClosingOutput = await chat(
        tier="strong",
        messages=judge_close_messages,
        response_model=JudgeClosingOutput,
        trial_id=trial_id,
        agent_role="judge",
    )

    await _persist_turn(
        db=db,
        trial_id=trial_id,
        seq=seq,
        agent_id=judge_agent.id if judge_agent else None,
        speaker_role="judge",
        text=judge_close_output.text,
        action=judge_close_output.action,
        emotion=judge_close_output.emotion,
        camera=judge_close_output.camera,
    )
    judge_ack_ok = await _send_and_wait_ack(
        trial_id=trial_id,
        seq=seq,
        speaker="judge",
        text=judge_close_output.text,
        action=judge_close_output.action,
        emotion=judge_close_output.emotion,
        camera=judge_close_output.camera,
    )
    turns_generated.append({"seq": seq, "speaker": "judge", "text": judge_close_output.text})
    seq += 1

    if not judge_ack_ok:
        return await _pause_trial(
            db,
            {**state, "turns": turns_generated, "turn_seq": seq},
            trial_id,
        )

    await db.commit()

    # Transition to FINISHED (DELIBERATION/VERDICT in Phase 7)
    previous = state["current_phase"]
    new_phase = TrialPhase.FINISHED.value
    await _update_trial_state(db, trial_id, new_phase)
    await _send_state(trial_id, new_phase, previous)
    await db.commit()

    logger.info(
        "closings_node: trial %s generated %d turns, transitioning to %s",
        trial_id,
        3,
        new_phase,
    )

    return {
        **state,
        "current_phase": new_phase,
        "previous_phase": previous,
        "turn_seq": seq,
        "turns": turns_generated,
        "active_speaker": "judge",
    }
