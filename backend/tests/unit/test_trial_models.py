"""Unit tests for Trial, Agent, and Turn SQLAlchemy models."""

import uuid

from app.db.models.trial import Agent, Trial, Turn


def test_trial_model_instantiation():
    trial_id = uuid.uuid4()
    case_id = uuid.uuid4()
    user_id = uuid.uuid4()

    trial = Trial(
        id=trial_id,
        case_id=case_id,
        user_id=user_id,
        mode="watch",
        state="SETUP",
        config={
            "juror_count": 3,
            "rounds": 1,
            "threshold": 0.75,
            "hung_band": 0.05,
        },
    )

    assert trial.id == trial_id
    assert trial.case_id == case_id
    assert trial.user_id == user_id
    assert trial.mode == "watch"
    assert trial.state == "SETUP"
    assert trial.config["juror_count"] == 3

    # Check table indexes
    indexes = {idx.name for idx in Trial.__table__.indexes}
    assert "trials_user_idx" in indexes
    assert "trials_case_idx" in indexes


def test_agent_model_instantiation():
    agent_id = uuid.uuid4()
    trial_id = uuid.uuid4()

    agent = Agent(
        id=agent_id,
        trial_id=trial_id,
        role="judge",
        persona={"style": "procedural", "temperament": "neutral"},
        tier="strong",
        memory=[],
    )

    assert agent.id == agent_id
    assert agent.trial_id == trial_id
    assert agent.role == "judge"
    assert agent.tier == "strong"
    assert agent.persona["style"] == "procedural"

    indexes = {idx.name for idx in Agent.__table__.indexes}
    assert "agents_trial_idx" in indexes


def test_turn_model_instantiation():
    turn_id = uuid.uuid4()
    trial_id = uuid.uuid4()
    agent_id = uuid.uuid4()

    turn = Turn(
        id=turn_id,
        trial_id=trial_id,
        seq=1,
        agent_id=agent_id,
        speaker_role="judge",
        text="Order in the court. We are now in session.",
        action="gavel_strike",
        emotion="neutral",
        camera="wide",
        admitted=True,
        struck=False,
    )

    assert turn.id == turn_id
    assert turn.trial_id == trial_id
    assert turn.seq == 1
    assert turn.speaker_role == "judge"
    assert turn.action == "gavel_strike"
    assert turn.admitted is True
    assert turn.struck is False

    indexes = {idx.name for idx in Turn.__table__.indexes}
    assert "turns_trial_idx" in indexes

    constraints = {c.name for c in Turn.__table__.constraints}
    assert "uq_turns_trial_id_seq" in constraints
