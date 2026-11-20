"""Pytest configuration and global fixtures."""

import asyncio
import os
import sys
from pathlib import Path

# Ensure libpq from PostgreSQL installation is discoverable on Windows
# to support pure-python psycopg under Windows 11 Smart App Control
if sys.platform == "win32":
    pg_bin = r"C:\Program Files\PostgreSQL\18\bin"
    if os.path.isdir(pg_bin) and pg_bin not in os.environ.get("PATH", ""):
        os.environ["PATH"] = pg_bin + os.pathsep + os.environ.get("PATH", "")
    os.environ.setdefault("PSYCOPG_IMPL", "python")

import pytest

# Ensure backend root is on sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# Configure SelectorEventLoop on Windows for psycopg3 async compatibility
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())  # type: ignore[attr-defined]


@pytest.fixture(scope="session")
def event_loop_policy():
    if sys.platform == "win32":
        return asyncio.WindowsSelectorEventLoopPolicy()  # type: ignore[attr-defined]
    return asyncio.DefaultEventLoopPolicy()
