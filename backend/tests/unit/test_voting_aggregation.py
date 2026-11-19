"""Unit tests for the voting and verdict aggregation module.

Verifies:
1. Jury share calculation (boolean votes and probabilities).
2. Judicial bench probability calculation across 3 judges.
3. 0.5 * J + 0.5 * P verdict scoring formula.
4. Disagreement metric |J - P|.
5. Threshold and hung-band outcome resolution (guilty, not_guilty, hung).
6. Ground truth matching logic.
7. Statutory BNS sentencing range mappings.
"""

from __future__ import annotations

import pytest

from app.voting import (
    DEFAULT_HUNG_BAND,
    DEFAULT_VERDICT_THRESHOLD,
    aggregate_verdict,
    calculate_bench_probability,
    calculate_bns_sentence_range,
    calculate_disagreement,
    calculate_jury_share,
    calculate_verdict_score,
    determine_verdict_outcome,
    evaluate_truth_match,
)


def test_calculate_jury_share_boolean_votes():
    """Verify jury share calculation from boolean guilty votes."""
    # 5 out of 7 guilty = 5/7 ~ 0.714
    votes = [{"guilty": True}] * 5 + [{"guilty": False}] * 2
    share = calculate_jury_share(votes)
    assert share == pytest.approx(0.714, abs=0.001)

    # All 7 guilty
    unanimous_guilty = [{"guilty": True}] * 7
    assert calculate_jury_share(unanimous_guilty) == 1.0

    # Unanimous not guilty
    unanimous_not_guilty = [{"guilty": False}] * 7
    assert calculate_jury_share(unanimous_not_guilty) == 0.0

    # Empty list
    assert calculate_jury_share([]) == 0.0


def test_calculate_jury_share_probability_fallback():
    """Verify fallback to probabilities when boolean flag is absent."""
    votes = [
        {"guilt_probability": 0.8},
        {"guilt_probability": 0.6},
        {"guilt_probability": 0.4},
    ]
    assert calculate_jury_share(votes) == pytest.approx(0.6, abs=0.001)


def test_calculate_bench_probability():
    """Verify mean judicial guilt probability across 3 judges."""
    judge_votes = [
        {"guilt_probability": 0.90},  # textualist
        {"guilt_probability": 0.80},  # precedent
        {"guilt_probability": 0.70},  # fairness
    ]
    prob = calculate_bench_probability(judge_votes)
    assert prob == pytest.approx(0.80, abs=0.001)

    assert calculate_bench_probability([]) == 0.0


def test_calculate_verdict_score():
    """Verify verdict score follows 0.5 * J + 0.5 * P."""
    j = 0.80
    p = 0.60
    # 0.5 * 0.80 + 0.5 * 0.60 = 0.70
    assert calculate_verdict_score(j, p) == 0.70


def test_calculate_disagreement():
    """Verify disagreement is absolute difference between jury and bench."""
    assert calculate_disagreement(0.85, 0.60) == 0.25
    assert calculate_disagreement(0.40, 0.75) == 0.35
    assert calculate_disagreement(0.70, 0.70) == 0.0


def test_determine_verdict_outcome_thresholds():
    """Verify outcome categorization based on threshold and hung band."""
    threshold = 0.75
    hung_band = 0.05
    # Lower bound = 0.70

    # Score >= 0.75 -> guilty
    assert determine_verdict_outcome(0.75, threshold, hung_band) == "guilty"
    assert determine_verdict_outcome(0.85, threshold, hung_band) == "guilty"

    # Score <= 0.70 -> not_guilty
    assert determine_verdict_outcome(0.70, threshold, hung_band) == "not_guilty"
    assert determine_verdict_outcome(0.65, threshold, hung_band) == "not_guilty"

    # 0.70 < Score < 0.75 -> hung
    assert determine_verdict_outcome(0.72, threshold, hung_band) == "hung"
    assert determine_verdict_outcome(0.74, threshold, hung_band) == "hung"
    assert determine_verdict_outcome(0.71, threshold, hung_band) == "hung"


def test_evaluate_truth_match():
    """Verify truth comparison for all outcomes."""
    # Guilty outcome matches True, mismatches False
    assert evaluate_truth_match("guilty", True) is True
    assert evaluate_truth_match("guilty", False) is False

    # Not guilty outcome matches False, mismatches True
    assert evaluate_truth_match("not_guilty", False) is True
    assert evaluate_truth_match("not_guilty", True) is False

    # Hung outcome returns None
    assert evaluate_truth_match("hung", True) is None
    assert evaluate_truth_match("hung", False) is None


def test_calculate_bns_sentence_range():
    """Verify statutory sentencing ranges under Bharatiya Nyaya Sanhita, 2023."""
    murder = calculate_bns_sentence_range("103(1)", "Murder of Arvind Sharma")
    assert "103(1)" in murder["section"]
    assert "life" in murder["minimum"].lower()
    assert "death" in murder["maximum"].lower()

    cheating = calculate_bns_sentence_range("318(4)", "Cheating and dishonestly inducing delivery")
    assert "318(4)" in cheating["section"]
    assert "7 years" in cheating["maximum"]

    hurt = calculate_bns_sentence_range("117(2)", "Grievous hurt with dangerous weapon")
    assert "117(2)" in hurt["section"]
    assert "7 years" in hurt["maximum"]


def test_aggregate_verdict_complete():
    """Verify aggregate_verdict resolves complete metrics and truth matching."""
    # 6 of 7 jurors vote guilty (J = 6/7 ~ 0.857)
    juror_votes = [{"guilty": True}] * 6 + [{"guilty": False}]
    # 3 judges average P = 0.800
    judge_votes = [
        {"guilt_probability": 0.85},
        {"guilt_probability": 0.80},
        {"guilt_probability": 0.75},
    ]

    res = aggregate_verdict(
        juror_final_votes=juror_votes,
        judge_votes=judge_votes,
        threshold=DEFAULT_VERDICT_THRESHOLD,
        hung_band=DEFAULT_HUNG_BAND,
        ground_truth_guilty=True,
    )

    assert res.j == pytest.approx(0.857, abs=0.001)
    assert res.p == 0.800
    # Score = 0.5 * 0.857 + 0.5 * 0.800 = 0.8285 -> round to 0.829
    assert res.score == pytest.approx(0.829, abs=0.001)
    assert res.outcome == "guilty"
    assert res.disagreement == pytest.approx(0.057, abs=0.001)
    assert res.matches_truth is True
