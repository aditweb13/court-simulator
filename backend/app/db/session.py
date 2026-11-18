"""Database engine, session factory, and FastAPI dependencies."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings

# Create async engine with psycopg 3
engine = create_async_engine(
    settings.database_url,
    echo=(settings.log_level.upper() == "DEBUG"),
    future=True,
)

async_session_maker = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that yields a database session per request."""
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()
