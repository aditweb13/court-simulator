"""LangGraph courtroom graph builder and execution runner.

Builds the StateGraph containing setup, openings, and closings phases.
Phase 6 adds examination; Phase 7 adds deliberation and verdict.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, cast
from uuid import UUID

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.trial import Trial
from app.orchestrator.nodes import closings_node, openings_node, setup_node
from app.orchestrator.state import CourtroomState, TrialPhase

logger = logging.getLogger("app.orchestrator")


def _extract_db(config: Optional[RunnableConfig | Dict[str, Any]]) -> AsyncSession:
    """Extract AsyncSession dependency from LangGraph runnable config."""
    if config is None:
        raise ValueError("LangGraph config with 'configurable' is required")

    configurable = config.get("configurable", {})
    db = configurable.get("db")
    if db is None:
        raise ValueError("Configurable 'db' (AsyncSession) is required in LangGraph config")
    return db


# ---------------------------------------------------------------------------
# Node Adapters
# ---------------------------------------------------------------------------


async def _run_setup(
    state: CourtroomState,
    config: Optional[RunnableConfig] = None,
) -> CourtroomState:
    db = _extract_db(config)
    return await setup_node(state, db)


async def _run_openings(
    state: CourtroomState,
    config: Optional[RunnableConfig] = None,
) -> CourtroomState:
    db = _extract_db(config)
    return await openings_node(state, db)


async def _run_closings(
    state: CourtroomState,
    config: Optional[RunnableConfig] = None,
) -> CourtroomState:
    db = _extract_db(config)
    return await closings_node(state, db)


# ---------------------------------------------------------------------------
# Conditional Routing
# ---------------------------------------------------------------------------


def _route_after_setup(state: CourtroomState) -> str:
    """Route from setup: halt on error/pause, otherwise proceed to openings."""
    if state.get("error") or state.get("is_paused"):
        return END
    return "openings"


def _route_after_openings(state: CourtroomState) -> str:
    """Route from openings: halt on error/pause, otherwise proceed to closings.

    Phase 6 will route to 'examination' before closings.
    """
    if state.get("error") or state.get("is_paused"):
        return END
    return "closings"


def _route_after_closings(state: CourtroomState) -> str:
    """Route from closings: halt or finish.

    Phase 7 will route to 'deliberation'.
    """
    return END


# ---------------------------------------------------------------------------
# Graph Construction
# ---------------------------------------------------------------------------


def build_courtroom_graph() -> CompiledStateGraph:
    """Construct and compile the LangGraph StateGraph for courtroom simulation."""
    builder = StateGraph(CourtroomState)

    # 1. Register nodes
    builder.add_node("setup", _run_setup)
    builder.add_node("openings", _run_openings)
    builder.add_node("closings", _run_closings)

    # 2. Add edges & conditional routing
    builder.add_edge(START, "setup")
    builder.add_conditional_edges(
        "setup",
        _route_after_setup,
        {"openings": "openings", END: END},
    )
    builder.add_conditional_edges(
        "openings",
        _route_after_openings,
        {"closings": "closings", END: END},
    )
    builder.add_conditional_edges(
        "closings",
        _route_after_closings,
        {END: END},
    )

    return builder.compile()


# Global compiled instance
courtroom_graph = build_courtroom_graph()


# ---------------------------------------------------------------------------
# Public Execution Runner
# ---------------------------------------------------------------------------


async def run_trial(
    trial_id: UUID,
    db: AsyncSession,
) -> CourtroomState:
    """Execute the full trial simulation graph for a given trial_id."""
    logger.info("run_trial: initiating orchestrator execution for trial %s", trial_id)

    # Look up trial row to initialize state
    stmt = select(Trial).where(Trial.id == trial_id)
    result = await db.execute(stmt)
    trial_row = result.scalar_one_or_none()
    if trial_row is None:
        raise ValueError(f"Trial '{trial_id}' not found")

    initial_state: CourtroomState = {
        "trial_id": trial_id,
        "case_id": trial_row.case_id,
        "current_phase": TrialPhase.SETUP.value,
        "previous_phase": None,
        "turn_seq": 0,
        "active_speaker": None,
        "turns": [],
        "is_paused": False,
        "error": None,
    }

    config: RunnableConfig = {"configurable": {"db": db}}

    final_state: CourtroomState = cast(
        CourtroomState,
        await courtroom_graph.ainvoke(
            initial_state,
            config=config,
        ),
    )

    logger.info(
        "run_trial: completed execution for trial %s. Final phase=%s, turns=%d, error=%s",
        trial_id,
        final_state.get("current_phase"),
        len(final_state.get("turns", [])),
        final_state.get("error"),
    )

    return final_state
