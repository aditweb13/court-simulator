"""Application server runner ensuring SelectorEventLoop on Windows."""

import asyncio
import os
import selectors
import sys

# Ensure PostgreSQL binaries are found on Windows
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    pg_bin = r"C:\Program Files\PostgreSQL\18\bin"
    if os.path.isdir(pg_bin):
        os.add_dll_directory(pg_bin)
        os.environ["PATH"] = pg_bin + os.pathsep + os.environ.get("PATH", "")

sys.path.insert(0, "backend")

import uvicorn
from app.main import create_app


async def main() -> None:
    app = create_app()
    config = uvicorn.Config(
        app,
        host="127.0.0.1",
        port=8000,
        loop="none",
        log_level="info",
    )
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    if sys.platform == "win32":
        loop_factory = lambda: asyncio.SelectorEventLoop(selectors.SelectSelector())  # noqa: E731
        asyncio.run(main(), loop_factory=loop_factory)
    else:
        asyncio.run(main())
