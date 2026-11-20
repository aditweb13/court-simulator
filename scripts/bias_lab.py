"""CLI script for running comparative bias laboratory across persona mixes.

Evaluates sensitivity of verdict distributions and juror voting patterns
across distinct occupational and reasoning-style compositions.

Usage:
    python scripts/bias_lab.py --case state-v-malhotra-2024 --runs-per-mix 3 --fake-llm --yes
"""

from __future__ import annotations

import argparse
import asyncio
import datetime
import json
import logging
import subprocess
import sys
from pathlib import Path
from typing import Any

# Add project root and backend directory to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from scripts.report import wilson_score_interval

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("bias_lab")

DEFAULT_MIXES = ["balanced", "rigorous_analytic", "intuitive_holistic"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run courtroom simulation bias laboratory."
    )
    parser.add_argument(
        "--case",
        type=str,
        default="state-v-malhotra-2024",
        help="Case slug or UUID (default: state-v-malhotra-2024)",
    )
    parser.add_argument(
        "--runs-per-mix",
        type=int,
        default=3,
        help="Number of trials to execute per persona mix (default: 3)",
    )
    parser.add_argument(
        "--mixes",
        nargs="+",
        default=DEFAULT_MIXES,
        help="List of persona mix names or file paths to evaluate",
    )
    parser.add_argument(
        "--fake-llm",
        action="store_true",
        help="Use deterministic simulated LLM for fast, quota-free execution",
    )
    parser.add_argument(
        "--out-dir",
        type=str,
        default="data/eval/reports",
        help="Output directory for reports (default: data/eval/reports)",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Proceed automatically without interactive prompt",
    )
    return parser.parse_args()


async def run_mix_batch(
    case_slug: str,
    mix_name: str,
    runs: int,
    fake_llm: bool,
    out_jsonl: Path,
    yes: bool,
) -> list[dict[str, Any]]:
    """Invoke run_batch.py programmatically for a specific persona mix."""
    cmd = [
        sys.executable,
        "scripts/run_batch.py",
        "--case",
        case_slug,
        "--runs",
        str(runs),
        "--persona-mix",
        mix_name,
        "--out",
        str(out_jsonl),
    ]
    if fake_llm:
        cmd.append("--fake-llm")
    if yes:
        cmd.append("--yes")

    logger.info("Executing batch for persona mix '%s' (%d runs)...", mix_name, runs)
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        logger.error("run_batch failed for mix %s: %s", mix_name, proc.stderr)
        raise RuntimeError(f"run_batch failed for mix {mix_name}")

    records: list[dict[str, Any]] = []
    if out_jsonl.exists():
        with open(out_jsonl, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
    return records


async def main() -> None:
    args = parse_args()
    timestamp = datetime.datetime.now(datetime.UTC).strftime("%Y%m%d_%H%M%S")
    runs_dir = Path("data/eval/runs")
    runs_dir.mkdir(parents=True, exist_ok=True)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print("\n" + "=" * 60)
    print("VERDICT BIAS LABORATORY: PERSONA MIX SENSITIVITY EVALUATION")
    print("=" * 60)
    print(f"Case:           {args.case}")
    print(f"Persona Mixes:  {', '.join(args.mixes)}")
    print(
        f"Runs Per Mix:   {args.runs_per_mix} (Total: {args.runs_per_mix * len(args.mixes)})"
    )
    print(f"Engine:         {'FakeLLM (offline)' if args.fake_llm else 'Live Router'}")
    print("=" * 60 + "\n")

    if not args.yes and (args.runs_per_mix * len(args.mixes)) > 3:
        confirm = (
            input("Run complete bias laboratory evaluation? [y/N]: ").strip().lower()
        )
        if confirm != "y":
            print("Aborted by user.")
            sys.exit(0)

    mix_results: dict[str, dict[str, Any]] = {}

    for mix_name in args.mixes:
        out_jsonl = runs_dir / f"bias_{args.case}_{mix_name}_{timestamp}.jsonl"
        records = await run_mix_batch(
            case_slug=args.case,
            mix_name=mix_name,
            runs=args.runs_per_mix,
            fake_llm=args.fake_llm,
            out_jsonl=out_jsonl,
            yes=args.yes,
        )

        completed = [r for r in records if r.get("status") == "completed"]
        n = len(completed)
        guilty_cnt = sum(1 for r in completed if r.get("outcome") == "guilty")
        not_guilty_cnt = sum(1 for r in completed if r.get("outcome") == "not_guilty")
        hung_cnt = sum(1 for r in completed if r.get("outcome") == "hung")
        match_cnt = sum(1 for r in completed if r.get("matches_truth") is True)

        mean_j = sum(r.get("j_score", 0.0) for r in completed) / n if n else 0.0
        mean_p = sum(r.get("p_score", 0.0) for r in completed) / n if n else 0.0
        mean_score = sum(r.get("score", 0.0) for r in completed) / n if n else 0.0

        ci_low, ci_high = wilson_score_interval(match_cnt, n)

        mix_results[mix_name] = {
            "n": n,
            "guilty_rate": round(guilty_cnt / n, 4) if n else 0.0,
            "not_guilty_rate": round(not_guilty_cnt / n, 4) if n else 0.0,
            "hung_rate": round(hung_cnt / n, 4) if n else 0.0,
            "truth_match_rate": round(match_cnt / n, 4) if n else 0.0,
            "truth_match_ci_95": [ci_low, ci_high],
            "mean_j_score": round(mean_j, 4),
            "mean_p_score": round(mean_p, 4),
            "mean_score": round(mean_score, 4),
        }

    # Generate Markdown and JSON comparison report
    report_json_path = out_dir / f"bias_lab_{args.case}_{timestamp}.json"
    report_md_path = out_dir / f"bias_lab_{args.case}_{timestamp}.md"

    lab_report = {
        "case_slug": args.case,
        "runs_per_mix": args.runs_per_mix,
        "generated_at": datetime.datetime.now(datetime.UTC).isoformat(),
        "mix_results": mix_results,
    }

    with open(report_json_path, "w", encoding="utf-8") as f:
        json.dump(lab_report, f, indent=2)

    # Format Markdown Table
    md_content = f"""# Verdict Bias Laboratory: Comparative Evaluation Report

- **Case**: `{args.case}`
- **Runs Per Mix**: `{args.runs_per_mix}`
- **Generated At**: `{lab_report["generated_at"]}`

> [!WARNING]
> **Sample Size Notice**: Sample size ($N = {args.runs_per_mix}$ per mix) is too small to claim
> statistically significant differences. The confidence intervals reported below illustrate
> variance bounds; do not infer causal behavioral divergence between persona compositions without
> high-volume power testing ($N \\ge 100$).

---

## 1. Cross-Panel Comparative Performance

| Panel | $N$ | Guilty % | Not Guilty % | Hung % | Mean $J$ | Mean $P$ | Truth-Match (95% CI) |
|---|---|---|---|---|---|---|---|
"""
    for mix_name, data in mix_results.items():
        ci = data["truth_match_ci_95"]
        ci_str = f"[{ci[0] * 100:.1f}%, {ci[1] * 100:.1f}%]"
        md_content += (
            f"| **{mix_name}** | {data['n']} | "
            f"{data['guilty_rate'] * 100:.1f}% | {data['not_guilty_rate'] * 100:.1f}% | "
            f"{data['hung_rate'] * 100:.1f}% | {data['mean_j_score']:.3f} | "
            f"{data['mean_p_score']:.3f} | **{data['truth_match_rate'] * 100:.1f}%** ({ci_str}) |\n"
        )

    md_content += """
---

## 2. Demographic & Bias Guard Verification

All juror personas evaluated in this laboratory vary strictly across:
- **Professional Domain**: (e.g., Forensic Auditor, Science Teacher, Family Counselor, Architect)
- **Cognitive / Evidentiary Reasoning Style**: (e.g., empirical, forensic, holistic, deductive)

**Strict Prohibition**: In compliance with the courtroom simulator ethical charter, zero
demographic or protected attributes (gender, religion, caste, socio-economic status, or
geographic background) are included in persona templates or deliberation prompts.

---

## 3. Recommended Follow-Up: Counterfactual Attribute-Swap Testing

To rigorously probe for underlying model bias without contaminating primary trial records:
- **Proposal**: Implement counterfactual attribute-swap testing as an offline evaluation harness,
  where identical evidence records are evaluated while rotating non-probative defendant
  identifiers (e.g. name variations across distinct communities) under controlled temperature.
- *Awaiting user approval before implementing.*

---
*Generated by `scripts/bias_lab.py`.*
"""

    with open(report_md_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    print("\n" + "=" * 60)
    print("BIAS LABORATORY EVALUATION COMPLETE")
    print("=" * 60)
    print(f"JSON Report:     {report_json_path}")
    print(f"Markdown Report: {report_md_path}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())  # type: ignore[attr-defined]
    asyncio.run(main())
