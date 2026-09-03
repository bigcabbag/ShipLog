"""U-003：SSE 进度事件契约 + 实时总线单测。"""

import asyncio

from app.rag.sse_events import (
    emit_progress,
    event_tool_end,
    event_tool_start,
    event_vision_extract,
    progress_queue_scope,
)


def test_vision_extract_event_shape():
    ev = event_vision_extract("DROP DATABASE prod")
    assert ev["event"] == "vision_extract"
    assert "DROP" in ev["extracted_query"]


def test_tool_event_shapes():
    start = event_tool_start("runbook", args={"query": "Redis"})
    end = event_tool_end("runbook", tool="search_runbook", summary="命中")
    assert start == {
        "event": "tool_start",
        "tool": "search_runbook",
        "agent": "runbook",
        "args": {"query": "Redis"},
    }
    assert end["event"] == "tool_end"
    assert end["summary"] == "命中"


def test_emit_progress_live_queue():
    async def _run() -> list[dict]:
        queue: asyncio.Queue = asyncio.Queue()
        received: list[dict] = []

        async def producer() -> None:
            with progress_queue_scope(queue):
                await emit_progress(event_tool_start("topology", args={"service": "x"}))
                await emit_progress(
                    event_tool_end("topology", summary="上下游 2")
                )
            await queue.put(None)

        async def consumer() -> None:
            while True:
                item = await queue.get()
                if item is None:
                    break
                received.append(item)

        await asyncio.gather(producer(), consumer())
        return received

    events = asyncio.run(_run())
    assert [e["event"] for e in events] == ["tool_start", "tool_end"]
    assert events[0]["tool"] == "get_service_topology"


def test_emit_without_queue_is_noop():
    async def _run() -> None:
        await emit_progress(event_tool_start("runbook"))

    asyncio.run(_run())  # 不抛错
