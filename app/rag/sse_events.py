"""U-003：SSE 进度事件契约 + 实时 progress 总线。"""

from __future__ import annotations

import asyncio
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Iterator

AGENT_TO_TOOL = {
    "runbook": "search_runbook",
    "incident": "query_incident",
    "topology": "get_service_topology",
}

_progress_queue: ContextVar[asyncio.Queue | None] = ContextVar(
    "sse_progress_queue", default=None
)


def event_status(phase: str, message: str) -> dict:
    return {"event": "status", "phase": phase, "message": message}


def event_vision_extract(extracted_query: str) -> dict:
    return {
        "event": "vision_extract",
        "extracted_query": extracted_query,
    }


def event_tool_start(
    agent: str,
    *,
    tool: str | None = None,
    args: dict | None = None,
) -> dict:
    name = agent.strip()
    return {
        "event": "tool_start",
        "tool": tool or AGENT_TO_TOOL.get(name, name),
        "agent": name,
        "args": args or {},
    }


def event_tool_end(
    agent: str,
    *,
    tool: str | None = None,
    summary: str = "",
) -> dict:
    name = agent.strip()
    return {
        "event": "tool_end",
        "tool": tool or AGENT_TO_TOOL.get(name, name),
        "agent": name,
        "summary": (summary or "")[:240],
    }


@contextmanager
def progress_queue_scope(queue: asyncio.Queue) -> Iterator[asyncio.Queue]:
    """在当前 asyncio Task 内绑定进度队列（勿在 create_task 外 set）。"""
    token = _progress_queue.set(queue)
    try:
        yield queue
    finally:
        _progress_queue.reset(token)


async def emit_progress(event: dict) -> None:
    """若当前 task 绑定了队列则推送；无绑定则静默（非流式 /chat）。"""
    queue = _progress_queue.get()
    if queue is None:
        return
    await queue.put(event)
