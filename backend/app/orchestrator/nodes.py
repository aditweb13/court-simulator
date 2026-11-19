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

from app.context.clerk import build_clerk_context, build_clerk_opening_prompt
from app.context.judge import (
    build_judge_closing_prompt,
    build_judge_context,
    build_judge_opening_prompt,
)
from app.db.models.case import Case
from app.db.models.trial import Agent, Trial, Turn
from app.llm.router import chat
from app.orchestrator.schemas import (
    ClerkAnnouncementOutput,
    ClosingArgumentOutput,
    JudgeClosingOutput,
    JudgeOpeningOutput,
)
from app.orchestrator.state import CourtroomState, TrialPhase
from app.ws.connection import manager as ws_manager
from app.ws.schemas import LineEvent, StateEvent

logger = logging.getLogger("app.orchestrator")


async def _get_agent_by_role(
    db: AsyncSession,
    trial_id: UUID,
    role: str,
) -> Optional[Agent]:
    """Fetch a single agent row by trial and role."""
    stmt = select(Agent).where(Agent.trial_id == trial_id, Agent.role == role)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


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
) -> Turn:
    """Create and flush a Turn row."""
    turn = Turn(
        trial_id=trial_id,
        seq=seq,
        agent_id=agent_id,
        speaker_role=speaker_role,
        text=text,
        action=action,
        emotion=emotion,
        camera=camera,
    )
    db.add(turn)
    await db.flush()
    return turn


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
    await _send_line(
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
    await _send_line(
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

    await db.commit()

    # Transition to next phase (EXAMINATION in Phase 6, skip to CLOSINGS for now)
    previous = state["current_phase"]
    new_phase = TrialPhase.CLOSINGS.value
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

    charge_text = case_row.charge
    case_title = case_row.title

    # Fetch agents
    prosecutor_agent = await _get_agent_by_role(db, trial_id, "prosecutor")
    defense_agent = await _get_agent_by_role(db, trial_id, "defense")
    judge_agent = await _get_agent_by_role(db, trial_id, "judge")

    turns_generated: List[Dict[str, Any]] = list(state.get("turns", []))

    # --- 1. Prosecution closing ---
    prosecution_messages = [
        {
            "role": "system",
            "content": (
                "You are the Prosecution counsel in an Indian criminal court. "
                "Deliver a compelling closing argument summarizing the case "
                "against the accused. Be persuasive and reference the charge. "
                "Keep it under 150 words."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Case: {case_title}\nCharge: {charge_text}\n\nDeliver your closing argument."
            ),
        },
    ]

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
    await _send_line(
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

    # --- 2. Defense closing ---
    defense_messages = [
        {
            "role": "system",
            "content": (
                "You are the Defense counsel in an Indian criminal court. "
                "Deliver a compelling closing argument defending the accused. "
                "Raise reasonable doubt and advocate for acquittal. "
                "Keep it under 150 words."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Case: {case_title}\nCharge: {charge_text}\n\nDeliver your closing argument."
            ),
        },
    ]

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
    await _send_line(
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
    await _send_line(
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
