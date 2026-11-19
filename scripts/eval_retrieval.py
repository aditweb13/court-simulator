"""Benchmark script evaluating statutory retrieval accuracy on 50 legal questions.

Definition of Done for Phase 3:
At least 90% of the 50 test questions must return the correct section in top 5.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Any

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.rag.retriever import retrieve

logger = logging.getLogger(__name__)


def matches_expected(
    chunk_act: str,
    chunk_sec: str,
    parent_sec: str | None,
    exp_act: str,
    exp_sec: str,
) -> bool:
    if chunk_act.upper() != exp_act.upper():
        return False
    # Clean section numbers e.g. "103 (Part 1/2)" -> "103"
    clean_sec = chunk_sec.split()[0].split("(")[0].strip()
    if clean_sec == exp_sec:
        return True
    return bool(parent_sec and parent_sec.strip() == exp_sec)


async def run_evaluation(dataset_path: Path) -> int:
    if not dataset_path.exists():
        print(f"Error: test dataset not found: {dataset_path}", file=sys.stderr)
        return 1

    questions: list[dict[str, Any]] = json.loads(dataset_path.read_text(encoding="utf-8"))
    total = len(questions)
    print(f"Loaded {total} benchmark questions from {dataset_path.name}...\n")

    top_1 = 0
    top_3 = 0
    top_5 = 0
    failures: list[dict[str, Any]] = []

    for i, q in enumerate(questions):
        qid = q["id"]
        query_text = q["query"]
        exp_act = q["expected_act"]
        exp_sec = str(q["expected_section"])
        role = q.get("role", "judge")

        retrieved = await retrieve(query_text, role=role, k=5)

        found_rank: int | None = None
        for rank, c in enumerate(retrieved):
            if matches_expected(c.act, c.section_no, c.parent_section, exp_act, exp_sec):
                found_rank = rank + 1
                break

        if found_rank == 1:
            top_1 += 1
            top_3 += 1
            top_5 += 1
            status = "HIT (Top 1)"
        elif found_rank is not None and found_rank <= 3:
            top_3 += 1
            top_5 += 1
            status = f"HIT (Top {found_rank})"
        elif found_rank is not None and found_rank <= 5:
            top_5 += 1
            status = f"HIT (Top {found_rank})"
        else:
            status = "MISS"
            retrieved_summary = [f"{c.act} {c.section_no}" for c in retrieved]
            failures.append({
                "id": qid,
                "query": query_text,
                "expected": f"{exp_act} {exp_sec}",
                "got": retrieved_summary,
            })

        print(
            f"[{qid:02d}/{total:02d}] {status:<12} "
            f"Exp: {exp_act} {exp_sec:<5} Query: {query_text[:60]}..."
        )

    top_1_acc = (top_1 / total) * 100
    top_3_acc = (top_3 / total) * 100
    top_5_acc = (top_5 / total) * 100

    print("\n" + "=" * 55)
    print("           RAG RETRIEVAL ACCURACY REPORT")
    print("=" * 55)
    print(f"Total Questions Evaluated:  {total}")
    print(f"Top-1 Accuracy:            {top_1:02d} / {total} ({top_1_acc:.1f}%)")
    print(f"Top-3 Accuracy:            {top_3:02d} / {total} ({top_3_acc:.1f}%)")
    print(f"Top-5 Accuracy:            {top_5:02d} / {total} ({top_5_acc:.1f}%)")
    print("=" * 55)

    if failures:
        print("\nMissed Questions:")
        for f in failures:
            print(f"  Q{f['id']}: Expected {f['expected']}, Got {f['got']}")

    if top_5_acc >= 90.0:
        print(f"\nSUCCESS: Top-5 accuracy ({top_5_acc:.1f}%) meets Definition of Done (>= 90.0%)!")
        return 0
    else:
        print(
            f"\nFAILURE: Top-5 accuracy ({top_5_acc:.1f}%) is below 90.0% threshold.",
            file=sys.stderr,
        )
        return 1


def main() -> None:
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    dataset = Path("data/eval/retrieval_eval_50.json")
    code = asyncio.run(run_evaluation(dataset))
    sys.exit(code)


if __name__ == "__main__":
    main()

