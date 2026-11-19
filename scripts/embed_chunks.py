"""Populate embeddings for all knowledge_chunks in PostgreSQL."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from app.db.models.knowledge import KnowledgeChunk
from app.db.session import async_session_maker
from app.rag.embeddings import get_embedder
from sqlalchemy import select


async def run_embed():
    embedder = get_embedder()
    print("Generating embeddings for all statutory chunks in PostgreSQL...")
    async with async_session_maker() as session, session.begin():
        res = await session.execute(select(KnowledgeChunk))
        chunks = list(res.scalars().all())
        print(f"Loaded {len(chunks)} chunks.")

        passages = [f"{c.act} Section {c.section_no}: {c.title}. {c.body}" for c in chunks]
        embeddings = embedder.embed_documents(passages)

        for chunk, emb in zip(chunks, embeddings):
            chunk.embedding = emb
            chunk.embedding_model = "bge-m3"

    print("Successfully updated all knowledge chunk embeddings!")


if __name__ == "__main__":
    asyncio.run(run_embed())

