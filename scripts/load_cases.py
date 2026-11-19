"""CLI script to load and validate hand-made courtroom cases into PostgreSQL.

Usage:
    python scripts/load_cases.py
    python scripts/load_cases.py --dir data/cases --check-only
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from decimal import Decimal
from pathlib import Path

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.cases.validator import CaseValidationError, assert_case_valid
from app.db.models.case import Case, Evidence, Witness
from app.db.session import async_session_maker
from app.schemas.case import CaseSchema
from pydantic import ValidationError
from sqlalchemy import select


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Load courtroom cases from JSON files into PostgreSQL"
    )
    parser.add_argument(
        "--dir",
        type=str,
        default="data/cases",
        help="Directory containing case JSON files (default: data/cases)",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Validate JSON structure and case rules without writing to the database",
    )
    return parser.parse_args()


def read_and_validate_cases(cases_dir: Path) -> list[tuple[Path, CaseSchema]]:
    json_files = sorted(cases_dir.glob("*.json"))
    if not json_files:
        print(f"No JSON case files found in {cases_dir}")
        return []

    print(f"Found {len(json_files)} case file(s) in {cases_dir}...\n")

    valid_cases: list[tuple[Path, CaseSchema]] = []
    for file_path in json_files:
        try:
            raw_content = file_path.read_text(encoding="utf-8")
            raw_data = json.loads(raw_content)
            case_schema = CaseSchema.model_validate(raw_data)
            assert_case_valid(case_schema)
            valid_cases.append((file_path, case_schema))
            print(f"[VALID] {file_path.name} -> '{case_schema.title}' ({case_schema.slug})")
        except (json.JSONDecodeError, ValidationError, CaseValidationError, OSError) as e:
            print(f"[INVALID] {file_path.name}: {e}", file=sys.stderr)
            raise

    return valid_cases


async def load_all_cases(cases_dir: Path, check_only: bool = False) -> int:
    if not cases_dir.exists():
        print(f"Error: directory not found: {cases_dir}", file=sys.stderr)
        return 1

    try:
        valid_cases = read_and_validate_cases(cases_dir)
    except (json.JSONDecodeError, ValidationError, CaseValidationError, OSError):
        return 1

    if not valid_cases:
        return 0

    if check_only:
        print(f"\n[Check-Only] All {len(valid_cases)} case(s) passed validation.")
        return 0

    print(f"\nLoading {len(valid_cases)} case(s) into database...")
    async with async_session_maker() as session, session.begin():
        for file_path, case_schema in valid_cases:
            # Check if case exists with this slug
            stmt = select(Case).where(Case.slug == case_schema.slug)
            res = await session.execute(stmt)
            existing_case = res.scalar_one_or_none()

            if existing_case:
                print(f"Updating existing case '{case_schema.slug}'...")
                await session.delete(existing_case)
                await session.flush()

            # Insert new case
            case_row = Case(
                slug=case_schema.slug,
                title=case_schema.title,
                jurisdiction=case_schema.jurisdiction,
                charge=case_schema.charge,
                difficulty=case_schema.difficulty,
                truth=case_schema.truth.model_dump(),
                source=case_schema.source,
            )
            session.add(case_row)
            await session.flush()

            for ev in case_schema.evidence:
                ev_row = Evidence(
                    case_id=case_row.id,
                    exhibit_no=ev.exhibit_no,
                    type=ev.type,
                    description=ev.description,
                    admissible=ev.admissible,
                    reason_inadmissible=ev.reason_inadmissible,
                )
                session.add(ev_row)

            for w in case_schema.witnesses:
                w_row = Witness(
                    case_id=case_row.id,
                    name=w.name,
                    saw_event_ids=w.saw_event_ids,
                    reliability=Decimal(str(w.reliability)),
                    hides=w.hides,
                    persona=w.persona,
                )
                session.add(w_row)

            print(
                f"  Loaded '{case_schema.slug}' (ID: {case_row.id}): "
                f"{len(case_schema.evidence)} exhibits, {len(case_schema.witnesses)} witnesses."
            )

    print(f"\nSuccessfully loaded {len(valid_cases)} case(s) into database.")
    return 0


def main() -> None:
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(
            asyncio.WindowsSelectorEventLoopPolicy()  # type: ignore[attr-defined]
        )
    args = parse_args()
    cases_dir = Path(args.dir)
    exit_code = asyncio.run(load_all_cases(cases_dir, check_only=args.check_only))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
