"""M6.2：LangGraph AsyncPostgresSaver（会话 thread 状态持久化）。"""

from __future__ import annotations

import asyncio

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.config import get_database_url

_saver: AsyncPostgresSaver | None = None
_saver_cm = None
_setup_lock = asyncio.Lock()


def pg_conn_string() -> str:
    """SQLAlchemy 风格 URL → psycopg3 可用的 postgresql://。"""
    url = get_database_url()
    if url.startswith("postgresql+psycopg://"):
        return url.replace("postgresql+psycopg://", "postgresql://", 1)
    return url


async def get_async_checkpointer() -> AsyncPostgresSaver:
    global _saver, _saver_cm
    async with _setup_lock:
        if _saver is None:
            _saver_cm = AsyncPostgresSaver.from_conn_string(pg_conn_string())
            _saver = await _saver_cm.__aenter__()
            await _saver.setup()
        return _saver


async def close_async_checkpointer() -> None:
    global _saver, _saver_cm
    if _saver_cm is not None:
        await _saver_cm.__aexit__(None, None, None)
        _saver_cm = None
        _saver = None
