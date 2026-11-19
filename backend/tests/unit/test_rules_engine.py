"""Unit tests for pure rules engine functions: turn order, objections, and admissibility."""

import pytest

from app.rules import (
    DEFAULT_OBJECTION_QUOTA_PER_EXAM,
    check_objection_quota,
    evaluate_evidence_admissibility,
    get_examining_lawyer,
    get_next_examination_stage,
    get_opposing_party,
    get_statutory_basis,
    is_leading_question_permitted,
    is_valid_objection_ground,
)


def test_objection_grounds_validation():
    for ground in ["hearsay", "leading", "relevance", "badgering", "speculation", "character"]:
        assert is_valid_objection_ground(ground) is True
        assert is_valid_objection_ground(ground.upper()) is True
        citation = get_statutory_basis(ground)
        assert citation is not None
        assert "Bharatiya Sakshya Adhiniyam" in citation

    assert is_valid_objection_ground("invalid_random_ground") is False
    assert get_statutory_basis("invalid_random_ground") is None


def test_objection_quota():
    assert check_objection_quota(0, limit=3) is True
    assert check_objection_quota(2, limit=3) is True
    assert check_objection_quota(3, limit=3) is False
    assert check_objection_quota(4, limit=3) is False
    assert DEFAULT_OBJECTION_QUOTA_PER_EXAM == 3


def test_leading_question_permission():
    # Leading forbidden in direct (chief) and redirect under BSA 146
    assert is_leading_question_permitted("direct") is False
    assert is_leading_question_permitted("redirect") is False
    # Leading permitted in cross-examination under BSA 146(3)
    assert is_leading_question_permitted("cross") is True


def test_turn_order_opposing_party():
    assert get_opposing_party("prosecutor") == "defense"
    assert get_opposing_party("prosecution") == "defense"
    assert get_opposing_party("defense") == "prosecutor"
    assert get_opposing_party("defendant") == "prosecutor"

    with pytest.raises(ValueError):
        get_opposing_party("judge")


def test_turn_order_examining_lawyer():
    # When prosecution calls the witness
    assert get_examining_lawyer("direct", calling_party="prosecutor") == "prosecutor"
    assert get_examining_lawyer("cross", calling_party="prosecutor") == "defense"
    assert get_examining_lawyer("redirect", calling_party="prosecutor") == "prosecutor"

    # When defense calls the witness
    assert get_examining_lawyer("direct", calling_party="defense") == "defense"
    assert get_examining_lawyer("cross", calling_party="defense") == "prosecutor"
    assert get_examining_lawyer("redirect", calling_party="defense") == "defense"


def test_next_examination_stage():
    assert get_next_examination_stage("direct") == "cross"
    assert get_next_examination_stage("cross") == "redirect"
    assert get_next_examination_stage("redirect") is None


def test_admissibility_rules():
    # Electronic evidence without certificate
    admissible, reason = evaluate_evidence_admissibility("electronic", metadata={})
    assert admissible is False
    assert "Section 63" in (reason or "")

    # Electronic evidence with certificate
    admissible, reason = evaluate_evidence_admissibility(
        "electronic", metadata={"bsa_63_certificate": True}
    )
    assert admissible is True
    assert reason is None

    # Police confession
    admissible, reason = evaluate_evidence_admissibility(
        "document", metadata={"police_confession": True}
    )
    assert admissible is False
    assert "Section 23" in (reason or "")

    # Secondary evidence without foundation
    admissible, reason = evaluate_evidence_admissibility(
        "document", metadata={"is_secondary_evidence": True, "original_loss_proven": False}
    )
    assert admissible is False
    assert "Section 60" in (reason or "")

    # Physical murder weapon / autopsy report
    admissible, reason = evaluate_evidence_admissibility("physical", metadata={"sealed": True})
    assert admissible is True
    assert reason is None
