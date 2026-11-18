"""CLI script to clean, chunk, and ingest statutory acts into PostgreSQL.

Usage:
    python scripts/ingest_law.py --file data/law_corpus/sample_corpus.json --dry-run
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.rag.chunker import parse_act_json, parse_act_text, validate_section


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest statutory acts into knowledge_chunks")
    parser.add_argument("--file", type=str, required=True, help="Path to act text or JSON file")
    parser.add_argument("--act", type=str, default=None, help="Name of the act (e.g. BNS, BNSS)")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and validate without inserting into database",
    )
    return parser.parse_args()


async def run_ingestion(file_path: Path, act_name: str, dry_run: bool) -> int:
    if not file_path.exists():
        print(f"Error: file not found: {file_path}", file=sys.stderr)
        return 1

    content = file_path.read_text(encoding="utf-8")
    ext = file_path.suffix.lower()

    if ext == ".json":
        sections = parse_act_json(content, default_act=act_name)
    else:
        sections = parse_act_text(content, act_name=act_name or "Unknown")

    valid_sections = [s for s in sections if validate_section(s)]

    print(f"--- Law Ingestion Report: {file_path.name} ---")
    print(f"Total sections parsed: {len(sections)}")
    print(f"Valid sections:        {len(valid_sections)}")
    print(f"Rejected sections:     {len(sections) - len(valid_sections)}")

    if valid_sections:
        sample = valid_sections[0]
        print(f"\nSample Section [{sample.act} Sec {sample.section_no}]: {sample.title}")
        print(f"Body snippet: {sample.body[:150]}...")
        print(f"Audience: {sample.audience}")
        print(f"License:  {sample.license}")

    if dry_run:
        print("\n[Dry Run] Validation successful. No database records modified.")
        return 0

    print(f"\nIngesting {len(valid_sections)} sections into knowledge_chunks...")
    from app.db.models.knowledge import KnowledgeChunk
    from app.db.session import async_session_maker

    try:
        async with async_session_maker() as session, session.begin():
            for sec in valid_sections:
                chunk = KnowledgeChunk(
                    domain=sec.domain,
                    audience=sec.audience,
                    act=sec.act,
                    section_no=sec.section_no,
                    title=sec.title,
                    body=sec.body,
                    ipc_equivalent=sec.ipc_equivalent,
                    valid_from=sec.valid_from,
                    valid_to=sec.valid_to,
                    source=sec.source,
                    license=sec.license,
                    embedding_model="placeholder",
                    embedding=[0.0] * 1024,
                )
                session.add(chunk)
        print("Ingestion complete: all sections inserted.")
        return 0
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"Database insertion failed: {exc}", file=sys.stderr)
        return 1


def main() -> None:
    args = parse_args()
    file_path = Path(args.file)
    act = args.act or file_path.stem.upper()
    ret = asyncio.run(run_ingestion(file_path, act, args.dry_run))
    sys.exit(ret)


if __name__ == "__main__":
    main()
