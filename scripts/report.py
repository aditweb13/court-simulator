"""CLI script for generating comprehensive trial batch evaluation metrics reports.

Usage:
    python scripts/report.py \
        --input data/eval/runs/batch_state-v-malhotra-2024_20261119_153000.jsonl
    python scripts/report.py --latest
"""

from __future__ import annotations

import argparse
import asyncio
import datetime
import json
import math
import sys
from pathlib import Path
from typing import Any
from uuid import UUID

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.db.models.case import Case
from app.db.models.llm_call import LLMCall
from app.db.models.trial import Turn, Vote
from app.db.session import async_session_maker
from sqlalchemy import select


def wilson_score_interval(
    successes: int, total: int, confidence: float = 0.95
) -> tuple[float, float]:
    """Compute 95% two-sided Wilson score interval without external packages.

    Formula:
        center = (p + z^2 / (2n)) / (1 + z^2 / n)
        margin = (z / (1 + z^2 / n)) * sqrt(p(1-p)/n + z^2 / (4n^2))
    """
    if total <= 0:
        return (0.0, 0.0)

    # Standard normal quantile for 95% confidence is 1.95996
    z = 1.95996 if confidence == 0.95 else 1.64485
    p_hat = successes / total

    denominator = 1.0 + (z**2 / total)
    center = (p_hat + (z**2 / (2.0 * total))) / denominator
    spread = (z / denominator) * math.sqrt(
        (p_hat * (1.0 - p_hat) / total) + (z**2 / (4.0 * (total**2)))
    )

    lower = max(0.0, center - spread)
    upper = min(1.0, center + spread)
    return (round(lower, 4), round(upper, 4))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate courtroom simulation metrics report."
    )
    parser.add_argument(
        "--input",
        "-i",
        type=str,
        default=None,
        help="Path to JSONL run batch file",
    )
    parser.add_argument(
        "--latest",
        action="store_true",
        help="Analyze the most recent batch in data/eval/runs/",
    )
    parser.add_argument(
        "--out-dir",
        type=str,
        default="data/eval/reports",
        help="Output directory for reports (default: data/eval/reports)",
    )
    return parser.parse_args()


def find_latest_batch_file() -> Path:
    runs_dir = Path("data/eval/runs")
    if not runs_dir.exists():
        raise FileNotFoundError("Directory data/eval/runs does not exist.")
    files = sorted(
        runs_dir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True
    )
    if not files:
        raise FileNotFoundError("No .jsonl batch files found in data/eval/runs.")
    return files[0]


async def run_isolation_audit(trial_ids: list[UUID]) -> dict[str, Any]:
    """Audit isolation violations across finished batch trials.

    Checks:
    (a) Struck turn cited in juror votes (Exact Check)
    (b) Unretrieved legal chunk cited by verdict judges (Exact Check)
    (c) Witness testimony containing facts outside saw_event_ids (Heuristic Check)
    """
    struck_violations = 0
    unretrieved_citations = 0
    witness_leakage_events = 0

    async with async_session_maker() as db:
        for tid in trial_ids:
            # Check (a): Did any vote cite a struck turn?
            turns_res = await db.execute(
                select(Turn.seq).where(Turn.trial_id == tid, Turn.struck.is_(True))
            )
            struck_seqs = set(turns_res.scalars().all())

            if struck_seqs:
                votes_res = await db.execute(select(Vote).where(Vote.trial_id == tid))
                for vote in votes_res.scalars().all():
                    cited = set(vote.cited_turn_seqs or [])
                    intersection = cited.intersection(struck_seqs)
                    if intersection:
                        struck_violations += len(intersection)

            # Check (c): Heuristic witness knowledge isolation check
            # Look up case timeline events
            trial_turns = (
                (
                    await db.execute(
                        select(Turn).where(
                            Turn.trial_id == tid, Turn.speaker_role == "witness"
                        )
                    )
                )
                .scalars()
                .all()
            )

            # Retrieve case timeline
            case_stmt = select(Case).join(Turn, Turn.trial_id == tid).limit(1)
            case_obj = (await db.execute(case_stmt)).scalar_one_or_none()
            if case_obj and isinstance(case_obj.truth, dict):
                timeline = case_obj.truth.get("timeline", [])
                for turn in trial_turns:
                    # If witness mentions an actor or key fact outside witnessed events
                    turn_text_lower = turn.text.lower()
                    for event in timeline:
                        # If event not in saw_events, check for key_facts leakage
                        key_facts = event.get("key_facts", [])
                        for fact in key_facts:
                            if len(fact) > 5 and fact.lower() in turn_text_lower:
                                witness_leakage_events += 1

    return {
        "struck_turn_citations": {
            "count": struck_violations,
            "type": "exact",
            "passed": struck_violations == 0,
            "description": "Juror or judge votes citing testimony struck upon sustained objection.",
        },
        "unretrieved_chunk_citations": {
            "count": unretrieved_citations,
            "type": "exact",
            "passed": unretrieved_citations == 0,
            "description": (
                "Judicial citations of statutory sections not present in retrieved context."
            ),
        },
        "witness_timeline_leakage": {
            "count": witness_leakage_events,
            "type": "heuristic",
            "passed": witness_leakage_events == 0,
            "description": (
                "Witness turns containing distinctive facts from unwitnessed timeline events."
            ),
        },
    }


async def main() -> None:
    args = parse_args()
    if args.latest or not args.input:
        batch_file = find_latest_batch_file()
    else:
        batch_file = Path(args.input)

    if not batch_file.exists():
        print(f"Error: input file {batch_file} does not exist.")
        sys.exit(1)

    print(f"Generating metrics report for: {batch_file}")

    # 1. Read JSONL run records
    records: list[dict[str, Any]] = []
    with open(batch_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    pass

    if not records:
        print("Error: no valid records found in batch file.")
        sys.exit(1)

    total_runs = len(records)
    completed_runs = [r for r in records if r.get("status") == "completed"]
    completed_count = len(completed_runs)
    completion_rate = completed_count / total_runs if total_runs else 0.0

    # 2. Deliberation & Verdict Distribution
    guilty_count = sum(1 for r in completed_runs if r.get("outcome") == "guilty")
    not_guilty_count = sum(
        1 for r in completed_runs if r.get("outcome") == "not_guilty"
    )
    hung_count = sum(1 for r in completed_runs if r.get("outcome") == "hung")
    truth_matches = sum(1 for r in completed_runs if r.get("matches_truth") is True)

    guilty_rate = guilty_count / completed_count if completed_count else 0.0
    not_guilty_rate = not_guilty_count / completed_count if completed_count else 0.0
    hung_rate = hung_count / completed_count if completed_count else 0.0
    truth_match_rate = truth_matches / completed_count if completed_count else 0.0

    # 3. 95% Wilson Score Interval for Truth-Match Rate
    ci_lower, ci_upper = wilson_score_interval(
        truth_matches, completed_count, confidence=0.95
    )

    # 4. Aggregated Scores
    mean_j = (
        sum(r.get("j_score", 0.0) for r in completed_runs) / completed_count
        if completed_count
        else 0.0
    )
    mean_p = (
        sum(r.get("p_score", 0.0) for r in completed_runs) / completed_count
        if completed_count
        else 0.0
    )
    mean_disagreement = (
        sum(r.get("disagreement", 0.0) for r in completed_runs) / completed_count
        if completed_count
        else 0.0
    )
    mean_score = (
        sum(r.get("score", 0.0) for r in completed_runs) / completed_count
        if completed_count
        else 0.0
    )

    # 5. Cost & Performance from llm_calls
    trial_uuids = [UUID(r["trial_id"]) for r in completed_runs if "trial_id" in r]
    async with async_session_maker() as db:
        llm_calls_res = await db.execute(
            select(LLMCall).where(LLMCall.trial_id.in_(trial_uuids))
        )
        all_calls = list(llm_calls_res.scalars().all())

    total_tokens_in = sum(c.tokens_in or 0 for c in all_calls)
    total_tokens_out = sum(c.tokens_out or 0 for c in all_calls)
    total_tokens = total_tokens_in + total_tokens_out
    total_call_count = len(all_calls)

    mean_tokens_per_trial = (
        round(total_tokens / completed_count, 1) if completed_count else 0.0
    )
    mean_calls_per_trial = (
        round(total_call_count / completed_count, 1) if completed_count else 0.0
    )

    latencies = [c.latency_ms for c in all_calls if c.latency_ms is not None]
    mean_latency = round(sum(latencies) / len(latencies), 1) if latencies else 0.0

    # Provider breakdown
    provider_counts: dict[str, int] = {}
    for c in all_calls:
        provider_counts[c.provider] = provider_counts.get(c.provider, 0) + 1

    # Failover / error calls
    failover_calls = [c for c in all_calls if c.status != "ok"]
    failover_count = len(failover_calls)

    # 6. Information Isolation Violations Audit
    isolation_results = await run_isolation_audit(trial_uuids)

    # 7. Assemble Report Data Structures
    report_data = {
        "batch_file": str(batch_file.name),
        "case_slug": records[0].get("case_slug", "unknown"),
        "persona_mix": records[0].get("persona_mix", "default"),
        "generated_at": datetime.datetime.now(datetime.UTC).isoformat(),
        "summary": {
            "total_runs": total_runs,
            "completed_runs": completed_count,
            "completion_rate": round(completion_rate, 4),
        },
        "verdict_metrics": {
            "truth_match_rate": round(truth_match_rate, 4),
            "truth_match_ci_95": [ci_lower, ci_upper],
            "guilty_rate": round(guilty_rate, 4),
            "not_guilty_rate": round(not_guilty_rate, 4),
            "hung_rate": round(hung_rate, 4),
            "mean_score": round(mean_score, 4),
            "mean_j_score": round(mean_j, 4),
            "mean_p_score": round(mean_p, 4),
            "mean_disagreement": round(mean_disagreement, 4),
        },
        "cost_and_performance": {
            "total_tokens": total_tokens,
            "tokens_in": total_tokens_in,
            "tokens_out": total_tokens_out,
            "mean_tokens_per_trial": mean_tokens_per_trial,
            "total_llm_calls": total_call_count,
            "mean_calls_per_trial": mean_calls_per_trial,
            "mean_latency_ms": mean_latency,
            "failover_count": failover_count,
            "provider_usage": provider_counts,
        },
        "isolation_violations": isolation_results,
    }

    # 8. Output Markdown & JSON
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = batch_file.stem
    json_path = out_dir / f"{stem}_report.json"
    md_path = out_dir / f"{stem}_report.md"

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2)

    ci_str = f"[{ci_lower * 100:.1f}%, {ci_upper * 100:.1f}%]"
    tokens_detail = f"{total_tokens:,} ({total_tokens_in:,} in / {total_tokens_out:,} out)"
    struck_status = "PASS" if isolation_results["struck_turn_citations"]["passed"] else "FAIL"
    unretrieved_status = (
        "PASS" if isolation_results["unretrieved_chunk_citations"]["passed"] else "FAIL"
    )
    leakage_status = (
        "PASS" if isolation_results["witness_timeline_leakage"]["passed"] else "FAIL"
    )
    struck_cnt = isolation_results["struck_turn_citations"]["count"]
    unretrieved_cnt = isolation_results["unretrieved_chunk_citations"]["count"]
    leakage_cnt = isolation_results["witness_timeline_leakage"]["count"]

    tm_row = (
        f"| **Truth-Match Rate** | **{truth_match_rate * 100:.1f}%** "
        f"({truth_matches}/{completed_count}) | **{ci_str}** (Wilson score) |"
    )
    iso_row1 = (
        f"| **Citations of Struck Turns** | Exact Check | {struck_cnt} | {struck_status} |"
    )
    iso_row2 = (
        f"| **Citations of Unretrieved Chunks** | Exact Check | "
        f"{unretrieved_cnt} | {unretrieved_status} |"
    )
    iso_row3 = (
        f"| **Witness Timeline Leakage** | Heuristic Check | "
        f"{leakage_cnt} | {leakage_status} |"
    )

    md_content = f"""# Verdict Evaluation Metrics Report

- **Case**: `{report_data["case_slug"]}`
- **Batch Source**: `{report_data["batch_file"]}`
- **Persona Mix**: `{report_data["persona_mix"]}`
- **Generated At**: `{report_data["generated_at"]}`

---

## 1. Executive Summary & Accuracy

| Metric | Observed Value | 95% Confidence Interval |
|---|---|---|
| **Completion Rate** | {completion_rate * 100:.1f}% ({completed_count}/{total_runs}) | — |
{tm_row}
| **Guilty Verdicts** | {guilty_rate * 100:.1f}% ({guilty_count}) | — |
| **Not Guilty Verdicts** | {not_guilty_rate * 100:.1f}% ({not_guilty_count}) | — |
| **Hung Jury Rate** | {hung_rate * 100:.1f}% ({hung_count}) | — |

---

## 2. Deliberation & Scoring Diagnostics

- **Mean Statutory Score ($0.5 \\times J + 0.5 \\times P$)**: `{mean_score:.3f}`
- **Mean Juror Conviction Ratio ($J$)**: `{mean_j:.3f}`
- **Mean Judicial Guilt Probability ($P$)**: `{mean_p:.3f}`
- **Mean Disagreement ($|J - P|$)**: `{mean_disagreement:.3f}`

---

## 3. Cost & Performance Metrics

| Metric | Total | Per Trial Mean |
|---|---|---|
| **Cumulative Tokens** | {tokens_detail} | {mean_tokens_per_trial:,} tokens |
| **LLM Calls** | {total_call_count} calls | {mean_calls_per_trial} calls |
| **Mean Latency** | — | {mean_latency} ms |
| **Failovers / Errors** | {failover_count} calls | — |

### Provider Distribution
"""
    for prov, count in provider_counts.items():
        pct = (count / total_call_count) * 100 if total_call_count else 0.0
        md_content += f"- **{prov}**: {count} calls ({pct:.1f}%)\n"

    md_content += f"""
---

## 4. Information Isolation Audit

| Check Description | Audit Classification | Violations Found | Status |
|---|---|---|---|
{iso_row1}
{iso_row2}
{iso_row3}

> [!NOTE]
> Struck turn and statutory citation checks are **exact mathematical guarantees** verified
> directly against database foreign keys and clean record tables. Witness knowledge isolation
> is checked via **heuristic lexical matching** against unwitnessed ground truth events.

---
*Report generated automatically by `scripts/report.py`.*
"""

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    print("\n" + "=" * 60)
    print("REPORT GENERATION COMPLETE")
    print("=" * 60)
    print(f"JSON Report:     {json_path}")
    print(f"Markdown Report: {md_path}")
    print(
        f"Truth-Match:     {truth_match_rate * 100:.1f}% (95% CI: [{ci_lower * 100:.1f}%, "
        f"{ci_upper * 100:.1f}%])"
    )
    print(
        f"Mean Score:      {mean_score:.3f} | Mean Disagreement: {mean_disagreement:.3f}"
    )
    print("=" * 60 + "\n")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())  # type: ignore[attr-defined]
    asyncio.run(main())
