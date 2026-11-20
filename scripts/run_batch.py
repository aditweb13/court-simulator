"""CLI script for running unattended trial batches and logging evaluation metrics.

Usage:
    python scripts/run_batch.py --case state-v-malhotra-2024 --runs 20 --fake-llm --yes
    python scripts/run_batch.py --case state-v-malhotra-2024 --runs 5 \
        --persona-mix rigorous_analytic --fake-llm --yes
"""

from __future__ import annotations

import argparse
import asyncio
import datetime
import json
import logging
import sys
import time
import uuid
from pathlib import Path
from typing import Any
from unittest.mock import patch

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.api.v1.trials import _seed_trial_agents
from app.core.errors import LLMUnavailable
from app.db.models.case import Case
from app.db.models.llm_call import LLMCall
from app.db.models.trial import Trial, Verdict, Vote
from app.db.session import async_session_maker
from app.llm.fake import DeterministicFakeLLM
from app.orchestrator.graph import run_trial
from app.orchestrator.headless import HeadlessAutoAckClient
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("run_batch")

ESTIMATED_CALLS_PER_RUN = 22
ESTIMATED_TOKENS_PER_RUN = 4400


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run unattended courtroom trial batches."
    )
    parser.add_argument(
        "--case",
        type=str,
        default="state-v-malhotra-2024",
        help="Case slug or UUID (default: state-v-malhotra-2024)",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=1,
        help="Number of trials to execute (default: 1)",
    )
    parser.add_argument(
        "--jurors",
        type=int,
        default=3,
        help="Number of jurors per trial (default: 3)",
    )
    parser.add_argument(
        "--rounds",
        type=int,
        default=1,
        help="Deliberation rounds per trial (default: 1)",
    )
    parser.add_argument(
        "--persona-mix",
        type=str,
        default=None,
        help="Path or name of persona mix JSON file (e.g. balanced, rigorous_analytic)",
    )
    parser.add_argument(
        "--out",
        type=str,
        default=None,
        help="Path to output JSONL file (default: data/eval/runs/batch_{timestamp}.jsonl)",
    )
    parser.add_argument(
        "--fake-llm",
        action="store_true",
        help="Use deterministic simulated LLM for fast, quota-free execution",
    )
    parser.add_argument(
        "--max-total-tokens",
        type=int,
        default=500000,
        help="Cumulative token budget cap across all runs in this batch (default: 500,000)",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Proceed automatically without interactive prompt for >3 runs",
    )
    return parser.parse_args()


def load_persona_mix(mix_name_or_path: str | None) -> list[dict[str, Any]] | None:
    """Load persona templates from JSON file."""
    if not mix_name_or_path:
        return None

    path = Path(mix_name_or_path)
    if not path.exists():
        # Try finding in data/eval/persona_mixes/
        candidate = Path("data/eval/persona_mixes") / f"{mix_name_or_path}.json"
        if candidate.exists():
            path = candidate
        else:
            raise FileNotFoundError(f"Persona mix file not found: {mix_name_or_path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
        return data.get("personas", [])


async def get_or_verify_case(case_ident: str) -> Case:
    """Look up case by slug or UUID."""
    async with async_session_maker() as db:
        stmt = select(Case).options(selectinload(Case.witnesses))
        try:
            case_uuid = uuid.UUID(case_ident)
            stmt = stmt.where(Case.id == case_uuid)
        except ValueError:
            stmt = stmt.where(Case.slug == case_ident)

        res = await db.execute(stmt)
        case_obj = res.scalar_one_or_none()
        if not case_obj:
            # Fallback: get first available case
            stmt_first = select(Case).options(selectinload(Case.witnesses)).limit(1)
            case_obj = (await db.execute(stmt_first)).scalar_one_or_none()
            if not case_obj:
                raise RuntimeError(
                    "No cases found in database. Seed cases first using scripts/load_cases.py"
                )
            logger.warning(
                "Requested case '%s' not found. Falling back to '%s'",
                case_ident,
                case_obj.slug,
            )
        return case_obj


async def create_batch_trial(
    case: Case,
    juror_count: int,
    rounds: int,
    persona_mix: list[dict[str, Any]] | None,
) -> Trial:
    """Create a new trial record in the database configured for unattended run."""
    trial_id = uuid.uuid4()
    config = {
        "juror_count": juror_count,
        "rounds": rounds,
        "threshold": 0.75,
        "hung_band": 0.05,
    }

    trial = Trial(
        id=trial_id,
        case_id=case.id,
        user_id=None,
        mode="watch",
        state="SETUP",
        config=config,
    )

    async with async_session_maker() as db:
        db.add(trial)
        # Seed agents with optional custom persona mix
        agents = _seed_trial_agents(case, config, custom_juror_personas=persona_mix)
        for a in agents:
            a.trial_id = trial_id
            db.add(a)
        await db.commit()
        await db.refresh(trial)
        return trial


async def main() -> None:
    args = parse_args()
    case = await get_or_verify_case(args.case)
    persona_mix = load_persona_mix(args.persona_mix)
    mix_label = args.persona_mix or "default"

    # 1. Output setup
    if not args.out:
        out_dir = Path("data/eval/runs")
        out_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.datetime.now(datetime.UTC).strftime("%Y%m%d_%H%M%S")
        out_path = out_dir / f"batch_{case.slug}_{timestamp}.jsonl"
    else:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)

    # 2. Resumable check
    completed_runs: set[int] = set()
    accumulated_tokens = 0
    if out_path.exists():
        with open(out_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        record = json.loads(line)
                        if record.get("status") == "completed":
                            completed_runs.add(record.get("run_index", -1))
                            accumulated_tokens += record.get("total_tokens", 0)
                    except json.JSONDecodeError:
                        pass
        if completed_runs:
            print(
                f"Resuming existing batch: {len(completed_runs)} runs "
                f"already completed in {out_path}."
            )

    remaining_runs = [i for i in range(1, args.runs + 1) if i not in completed_runs]
    if not remaining_runs:
        print(f"All {args.runs} runs are already completed in {out_path}.")
        return

    # 3. Estimate tokens and calls
    est_calls = len(remaining_runs) * ESTIMATED_CALLS_PER_RUN
    est_tokens = len(remaining_runs) * ESTIMATED_TOKENS_PER_RUN

    print("\n" + "=" * 60)
    print("VERDICT UNATTENDED BATCH SIMULATION RUNNER")
    print("=" * 60)
    print(f"Case:           {case.slug} ({case.title})")
    print(f"Total Runs:     {args.runs} ({len(remaining_runs)} remaining)")
    print(f"Jurors:         {args.jurors} | Deliberation Rounds: {args.rounds}")
    print(f"Persona Mix:    {mix_label}")
    print(
        f"Engine:         {'FakeLLM (deterministic, offline)' if args.fake_llm else 'Live Router'}"
    )
    print(f"Est. LLM Calls: ~{est_calls}")
    print(f"Est. Tokens:    ~{est_tokens:,} (Cap: {args.max_total_tokens:,})")
    print(f"Output File:    {out_path}")
    print("=" * 60 + "\n")

    if len(remaining_runs) > 3 and not args.yes:
        confirm = (
            input(f"Run batch of {len(remaining_runs)} trials? [y/N]: ").strip().lower()
        )
        if confirm != "y":
            print("Aborted by user.")
            sys.exit(0)

    fake_llm = DeterministicFakeLLM() if args.fake_llm else None

    # 4. Sequential execution loop
    for run_idx in remaining_runs:
        if accumulated_tokens >= args.max_total_tokens:
            logger.warning(
                "Batch token cap (%d) reached with %d tokens. Stopping cleanly.",
                args.max_total_tokens,
                accumulated_tokens,
            )
            break

        print(
            f"[{run_idx}/{args.runs}] Starting trial simulation...", end=" ", flush=True
        )
        start_time = time.monotonic()
        trial = await create_batch_trial(
            case=case,
            juror_count=args.jurors,
            rounds=args.rounds,
            persona_mix=persona_mix,
        )

        try:
            # Use HeadlessAutoAckClient to drive turns without a browser
            async with HeadlessAutoAckClient(trial.id):
                if args.fake_llm and fake_llm:
                    with patch(
                        "app.orchestrator.nodes.chat", side_effect=fake_llm.chat
                    ):
                        async with async_session_maker() as db:
                            await run_trial(trial.id, db)
                else:
                    async with async_session_maker() as db:
                        await run_trial(trial.id, db)

        except LLMUnavailable as exc:
            logger.error("Batch interrupted by LLM provider exhaustion: %s", exc)
            break
        except Exception:
            logger.exception("Error executing trial %s", trial.id)
            continue

        elapsed = time.monotonic() - start_time

        # Retrieve verdict and metrics from DB
        async with async_session_maker() as db:
            verdict = await db.get(Verdict, trial.id)
            # Count calls and tokens for this trial
            call_stmt = select(
                func.count(LLMCall.id),
                func.coalesce(func.sum(LLMCall.tokens_in), 0),
                func.coalesce(func.sum(LLMCall.tokens_out), 0),
            ).where(LLMCall.trial_id == trial.id)
            calls_res = await db.execute(call_stmt)
            call_count, t_in, t_out = calls_res.one()

            # Query juror votes for J score calculation
            juror_votes = (
                (
                    await db.execute(
                        select(Vote).where(
                            Vote.trial_id == trial.id, Vote.kind == "juror_final"
                        )
                    )
                )
                .scalars()
                .all()
            )
            guilty_juror_votes = sum(1 for v in juror_votes if v.guilty)
            j_score = (
                round(guilty_juror_votes / len(juror_votes), 3) if juror_votes else 0.0
            )

        trial_tokens = int(t_in + t_out)
        accumulated_tokens += trial_tokens

        outcome = verdict.outcome if verdict else "unknown"
        score = float(verdict.score) if verdict and verdict.score is not None else 0.0
        matches_truth = bool(verdict.matches_truth) if verdict else False

        p_score = round((score - (0.5 * j_score)) / 0.5, 3) if verdict else 0.0
        disagreement = round(abs(j_score - p_score), 3)

        summary_line = {
            "trial_id": str(trial.id),
            "run_index": run_idx,
            "case_id": str(case.id),
            "case_slug": case.slug,
            "persona_mix": mix_label,
            "jurors": args.jurors,
            "rounds": args.rounds,
            "status": "completed",
            "outcome": outcome,
            "score": score,
            "j_score": j_score,
            "p_score": p_score,
            "disagreement": disagreement,
            "matches_truth": matches_truth,
            "tokens_in": int(t_in),
            "tokens_out": int(t_out),
            "total_tokens": trial_tokens,
            "llm_calls_count": int(call_count),
            "duration_seconds": round(elapsed, 2),
            "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
        }

        with open(out_path, "a", encoding="utf-8") as out_f:
            out_f.write(json.dumps(summary_line) + "\n")

        print(
            f"Done in {elapsed:.1f}s. Outcome: {outcome.upper()} "
            f"(Score: {score:.2f}, Match: {matches_truth})"
        )

    print("\n" + "=" * 60)
    print(f"Batch completed. Results written to:\n  {out_path}")
    print("=" * 60)


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())  # type: ignore[attr-defined]
    asyncio.run(main())
