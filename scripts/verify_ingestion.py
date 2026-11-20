"""Verification script for ingested statutory law chunks in PostgreSQL."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.db.session import async_session_maker
from app.rag.chunker import default_estimate_tokens
from sqlalchemy import text


async def verify() -> int:
    async with async_session_maker() as session:
        # 1. Row count per act
        res = await session.execute(
            text("SELECT act, count(*) FROM knowledge_chunks GROUP BY act ORDER BY act")
        )
        print("=== Row Count per Act ===")
        total_chunks = 0
        for row in res.fetchall():
            act, count = row[0], row[1]
            total_chunks += count
            print(f"  {act}: {count} chunks")
        print(f"  Total across all acts: {total_chunks}")

        # 2. Check for empty bodies
        res_empty = await session.execute(
            text("SELECT count(*) FROM knowledge_chunks WHERE body IS NULL OR trim(body) = ''")
        )
        empty_count = res_empty.scalar()
        print(f"\nEmpty bodies: {empty_count}")
        assert empty_count == 0, f"Found {empty_count} empty bodies!"

        # 3. Check for oversized chunks
        res_all = await session.execute(
            text("SELECT act, section_no, title, body FROM knowledge_chunks")
        )
        oversized = []
        for r in res_all.fetchall():
            toks = default_estimate_tokens(f"{r[2]}. {r[3]}")
            if toks > 512:
                oversized.append((r[0], r[1], toks))
        print(f"Chunks over 512 tokens: {len(oversized)}")
        assert len(oversized) == 0, f"Found {len(oversized)} oversized chunks!"

        # 4. Check audience for Constitution Arts 20, 21, 22
        res_aud = await session.execute(
            text(
                "SELECT section_no, audience FROM knowledge_chunks "
                "WHERE act = 'CONSTITUTION' AND ("
                "section_no IN ('20', '21', '22') "
                "OR section_no LIKE '20 (%' "
                "OR section_no LIKE '21 (%' "
                "OR section_no LIKE '22 (%'"
                ") ORDER BY section_no"
            )
        )
        print("\nConstitution Arts 20-22 Audience:")
        for r in res_aud.fetchall():
            print(f"  Art {r[0]}: {r[1]}")
            assert "juror" in r[1], f"Juror audience missing from {r[0]}"

        # 5. Check BNS IPC equivalents
        res_ipc = await session.execute(
            text(
                "SELECT count(*) FROM knowledge_chunks "
                "WHERE act = 'BNS' AND ipc_equivalent IS NOT NULL"
            )
        )
        ipc_count = res_ipc.scalar()
        print(f"\nBNS chunks with IPC equivalent: {ipc_count}")
        assert ipc_count > 0, "No IPC equivalents found in BNS chunks!"

        # 6. Dates check
        res_dates = await session.execute(
            text(
                "SELECT act, min(valid_from), max(valid_from) "
                "FROM knowledge_chunks GROUP BY act ORDER BY act"
            )
        )
        print("\nEffective Date Range:")
        for r in res_dates.fetchall():
            print(f"  {r[0]}: {r[1]} to {r[2]}")

        print("\nAll Ingestion Integrity Checks Passed Successfully!")
        return 0


def main() -> None:
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    code = asyncio.run(verify())
    sys.exit(code)


if __name__ == "__main__":
    main()
