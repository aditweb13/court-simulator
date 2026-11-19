"""Pure statutory voting, verdict aggregation, and sentencing calculation functions.

Pure functions only — zero database or LLM dependencies.
Formula:
  Score = 0.5 * J + 0.5 * P
  Disagreement = abs(J - P)
  Outcomes:
    Score >= threshold               -> guilty
    Score <= (threshold - hung_band) -> not_guilty
    between (threshold - hung_band) and threshold -> hung
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Final, List, Optional, Protocol

DEFAULT_VERDICT_THRESHOLD: Final[float] = 0.75
DEFAULT_HUNG_BAND: Final[float] = 0.05


class VoteProtocol(Protocol):
    """Protocol matching vote objects or dictionaries."""

    guilty: Optional[bool]
    guilt_probability: Optional[float]


@dataclass(frozen=True)
class VerdictAggregationResult:
    """Aggregated verdict outcome metrics and scoring."""

    j: float
    p: float
    score: float
    threshold: float
    hung_band: float
    outcome: str  # guilty | not_guilty | hung
    disagreement: float
    matches_truth: Optional[bool]


def calculate_jury_share(votes: List[Any]) -> float:
    """Calculate jury guilty share J (0.0 to 1.0).

    Uses fraction of affirmative guilty votes when available;
    falls back to the mean of guilt_probability values.
    """
    if not votes:
        return 0.0

    guilty_count = 0
    valid_count = 0
    prob_sum = 0.0
    has_boolean = False

    for v in votes:
        guilty_val = getattr(v, "guilty", None) if not isinstance(v, dict) else v.get("guilty")
        prob_val = (
            getattr(v, "guilt_probability", None)
            if not isinstance(v, dict)
            else v.get("guilt_probability")
        )

        if guilty_val is not None:
            has_boolean = True
            if bool(guilty_val):
                guilty_count += 1
            valid_count += 1
        elif prob_val is not None:
            prob_sum += float(prob_val)
            valid_count += 1

    if valid_count == 0:
        return 0.0

    if has_boolean:
        return round(guilty_count / valid_count, 3)
    return round(prob_sum / valid_count, 3)


def calculate_bench_probability(judge_votes: List[Any]) -> float:
    """Calculate mean judicial guilt probability P across the 3 verdict judges (0.0 to 1.0)."""
    if not judge_votes:
        return 0.0

    total_prob = 0.0
    count = 0

    for jv in judge_votes:
        prob = (
            getattr(jv, "guilt_probability", None)
            if not isinstance(jv, dict)
            else jv.get("guilt_probability")
        )
        if prob is not None:
            total_prob += float(prob)
            count += 1
        else:
            # Fall back to boolean guilty check if probability is missing
            guilty = getattr(jv, "guilty", None) if not isinstance(jv, dict) else jv.get("guilty")
            if guilty is not None:
                total_prob += 1.0 if bool(guilty) else 0.0
                count += 1

    if count == 0:
        return 0.0
    return round(total_prob / count, 3)


def calculate_disagreement(j: float, p: float) -> float:
    """Calculate the absolute divergence between jury share and judicial bench: abs(J - P)."""
    return round(abs(j - p), 3)


def calculate_verdict_score(
    j: float,
    p: float,
    jury_weight: float = 0.5,
    bench_weight: float = 0.5,
) -> float:
    """Calculate combined verdict score = 0.5 * J + 0.5 * P."""
    return round(jury_weight * j + bench_weight * p, 3)


def determine_verdict_outcome(
    score: float,
    threshold: float = DEFAULT_VERDICT_THRESHOLD,
    hung_band: float = DEFAULT_HUNG_BAND,
) -> str:
    """Determine outcome category based on verdict score, threshold, and hung band.

    - Score >= threshold: 'guilty'
    - Score <= (threshold - hung_band): 'not_guilty'
    - (threshold - hung_band) < Score < threshold: 'hung'
    """
    lower_bound = round(threshold - hung_band, 3)
    if score >= threshold:
        return "guilty"
    elif score <= lower_bound:
        return "not_guilty"
    else:
        return "hung"


def evaluate_truth_match(outcome: str, ground_truth_guilty: bool) -> Optional[bool]:
    """Compare final trial outcome with the hidden ground truth.

    Returns:
    - True if outcome matches truth ('guilty' == True or 'not_guilty' == False)
    - False if outcome contradicts truth
    - None if the trial resulted in a hung verdict
    """
    if outcome == "hung":
        return None
    if outcome == "guilty":
        return ground_truth_guilty is True
    if outcome == "not_guilty":
        return ground_truth_guilty is False
    return None


def calculate_bns_sentence_range(bns_section: str, charge: str) -> Dict[str, Any]:
    """Provide statutory sentencing range under Bharatiya Nyaya Sanhita, 2023 provisions."""
    clean_sec = bns_section.replace("BNS", "").replace("Section", "").strip().lower()

    if "103" in clean_sec or "murder" in charge.lower():
        return {
            "section": "BNS Section 103(1)",
            "offense": "Murder",
            "minimum": "Imprisonment for life",
            "maximum": "Death penalty",
            "fine": "Mandatory fine",
            "recommended": "Rigorous imprisonment for life with fine",
        }
    elif "318" in clean_sec or "cheating" in charge.lower():
        return {
            "section": "BNS Section 318(4)",
            "offense": "Cheating and dishonestly inducing delivery of property",
            "minimum": "Discretionary (up to 7 years)",
            "maximum": "Imprisonment up to 7 years",
            "fine": "Liable to fine",
            "recommended": "Rigorous imprisonment for 4 years with fine of Rs. 50,000",
        }
    elif "117" in clean_sec or "grievous" in charge.lower():
        return {
            "section": "BNS Section 117(2)",
            "offense": "Voluntarily causing grievous hurt",
            "minimum": "Discretionary (up to 7 years)",
            "maximum": "Imprisonment up to 7 years",
            "fine": "Liable to fine",
            "recommended": "Rigorous imprisonment for 3 years with fine of Rs. 25,000",
        }
    else:
        return {
            "section": f"BNS {bns_section}",
            "offense": charge,
            "minimum": "Statutory minimum",
            "maximum": "Statutory maximum prescribed under BNS",
            "fine": "Liable to fine",
            "recommended": "Term proportionate to gravity of proved offense",
        }


def aggregate_verdict(
    juror_final_votes: List[Any],
    judge_votes: List[Any],
    threshold: float = DEFAULT_VERDICT_THRESHOLD,
    hung_band: float = DEFAULT_HUNG_BAND,
    ground_truth_guilty: Optional[bool] = None,
) -> VerdictAggregationResult:
    """Perform complete verdict aggregation across jury and judicial bench."""
    j = calculate_jury_share(juror_final_votes)
    p = calculate_bench_probability(judge_votes)
    score = calculate_verdict_score(j, p)
    disagreement = calculate_disagreement(j, p)
    outcome = determine_verdict_outcome(score, threshold, hung_band)
    matches_truth = (
        evaluate_truth_match(outcome, ground_truth_guilty)
        if ground_truth_guilty is not None
        else None
    )

    return VerdictAggregationResult(
        j=j,
        p=p,
        score=score,
        threshold=threshold,
        hung_band=hung_band,
        outcome=outcome,
        disagreement=disagreement,
        matches_truth=matches_truth,
    )
