"""CLI script to clean, chunk, and ingest statutory acts into PostgreSQL.

Usage:
    python scripts/ingest_law.py --file data/law_corpus/sample_corpus.json --act BNS --dry-run
"""

from __future__ import annotations

import argparse
import asyncio
import datetime
import sys
from pathlib import Path

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.rag.chunker import (
    default_estimate_tokens,
    extract_pdf_text,
    parse_act_json,
    parse_act_markdown,
    parse_act_text,
    validate_section,
    verify_act_in_sources,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest statutory acts into knowledge_chunks")
    parser.add_argument(
        "--file", type=str, required=True, help="Path to act PDF, text or JSON file"
    )
    parser.add_argument(
        "--act", type=str, default=None, help="Name of the act (e.g. BNS, BNSS, BSA)"
    )
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

    # Verify Act is registered in SOURCES.md
    if not verify_act_in_sources(act_name):
        print(
            f"Error: Act '{act_name}' is not registered in SOURCES.md. Ingestion refused.",
            file=sys.stderr,
        )
        return 1

    ext = file_path.suffix.lower()

    # Determine default valid_from date per Indian criminal law reform (July 1, 2024)
    default_valid_from: datetime.date | None = None
    if act_name.upper() in {"BNS", "BNSS", "BSA"}:
        default_valid_from = datetime.date(2024, 7, 1)
    elif act_name.upper() == "CONSTITUTION":
        default_valid_from = datetime.date(1950, 1, 26)

    content = file_path.read_text(encoding="utf-8")
    if ext == ".json":
        sections = parse_act_json(content, default_act=act_name)
    elif ext == ".pdf":
        text = extract_pdf_text(file_path)
        sections = parse_act_text(text, act_name=act_name, valid_from=default_valid_from)
    elif ext == ".md":
        sections = parse_act_markdown(content, act_name=act_name, valid_from=default_valid_from)
    else:
        sections = parse_act_text(content, act_name=act_name, valid_from=default_valid_from)

    valid_sections = [s for s in sections if validate_section(s)]
    split_chunks = [s for s in valid_sections if s.parent_section is not None]
    empty_bodies = [s for s in valid_sections if not s.body or not s.body.strip()]
    over_limit_chunks = [
        s for s in valid_sections if default_estimate_tokens(f"{s.title}. {s.body}") > 512
    ]
    with_ipc = [s for s in valid_sections if s.ipc_equivalent is not None]

    print(f"--- Law Ingestion Report: {file_path.name} ---")
    print(f"Act:                   {act_name}")
    print(f"Total chunks parsed:   {len(sections)}")
    print(f"Valid chunks:          {len(valid_sections)}")
    print(f"Split pieces created:  {len(split_chunks)}")
    print(f"Empty bodies:          {len(empty_bodies)}")
    print(f"Chunks over 512 tok:   {len(over_limit_chunks)}")
    if act_name.upper() == "BNS":
        print(f"BNS with IPC equiv:    {len(with_ipc)} / {len(valid_sections)}")
    print(f"Rejected chunks:       {len(sections) - len(valid_sections)}")

    if valid_sections:
        sample = valid_sections[0]
        print(f"\nSample Chunk [{sample.act} Sec {sample.section_no}]: {sample.title}")
        print(f"Body snippet: {sample.body[:150]}...")
        print(f"Audience: {sample.audience}")
        print(f"License:  {sample.license}")
        if sample.valid_from:
            print(f"Valid from: {sample.valid_from}")

    if dry_run:
        print("\n[Dry Run] Validation successful. No database records modified.")
        return 0

    print(f"\nIngesting {len(valid_sections)} chunks into knowledge_chunks...")
    from app.db.models.knowledge import KnowledgeChunk
    from app.db.session import async_session_maker
    from sqlalchemy import select

    try:
        async with async_session_maker() as session, session.begin():
            inserted = 0
            updated = 0
            for sec in valid_sections:
                # Idempotent upsert on (act, section_no, valid_from)
                stmt = select(KnowledgeChunk).where(
                    KnowledgeChunk.act == sec.act,
                    KnowledgeChunk.section_no == sec.section_no,
                    KnowledgeChunk.valid_from == sec.valid_from,
                )
                res = await session.execute(stmt)
                existing = res.scalar_one_or_none()

                if existing:
                    existing.title = sec.title
                    existing.body = sec.body
                    existing.domain = sec.domain
                    existing.audience = sec.audience
                    existing.ipc_equivalent = sec.ipc_equivalent
                    existing.valid_to = sec.valid_to
                    existing.source = sec.source
                    existing.license = sec.license
                    existing.embedding_model = "bge-m3"
                    existing.embedding = [0.0] * 1024
                    updated += 1
                else:
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
                        embedding_model="bge-m3",
                        embedding=[0.0] * 1024,
                    )
                    session.add(chunk)
                    inserted += 1

        print(f"Ingestion complete: {inserted} inserted, {updated} updated.")
        return 0
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"Database insertion failed: {exc}", file=sys.stderr)
        return 1


def main() -> None:
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    args = parse_args()
    file_path = Path(args.file)
    act = args.act or file_path.stem.upper()
    ret = asyncio.run(run_ingestion(file_path, act, args.dry_run))
    sys.exit(ret)


if __name__ == "__main__":
    main()
