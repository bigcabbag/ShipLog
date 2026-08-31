from collections.abc import AsyncIterator
from typing import Any

from app.llm import chat
from app.rag.multi_agent_graph import run_multi_agent_prepare
from app.rag.query import resolve_rag_inputs
from app.rag.session import load_thread_history, record_thread_turn, resolve_thread_id
from app.rag.sse_events import event_status, event_vision_extract


async def rag_chat(
    message: str,
    *,
    top_k: int = 3,
    system_prompt: str | None = None,
    image_base64: str | None = None,
    image_media_type: str = "image/png",
    thread_id: str | None = None,
) -> tuple[str, list[dict], str, str | None, list[str], str]:
    user_message, retrieval_query, pre_steps, extracted = await resolve_rag_inputs(
        message,
        image_base64=image_base64,
        image_media_type=image_media_type,
    )
    tid = resolve_thread_id(thread_id)
    rag_prompt, sources, early, trace_id, plan_steps, _tid, _progress = (
        await run_multi_agent_prepare(
            user_message,
            top_k=top_k,
            system_prompt=system_prompt,
            search_query=retrieval_query,
            pre_trace_steps=pre_steps,
            thread_id=tid,
            anchor_candidate=extracted,
        )
    )
    if early is not None:
        if early.strip():
            await record_thread_turn(tid, user=user_message, assistant=early)
        return early, sources, trace_id, extracted, plan_steps, tid

    history = await load_thread_history(tid)
    reply = await chat(user_message, system_prompt=rag_prompt, history=history)
    if reply.strip():
        await record_thread_turn(tid, user=user_message, assistant=reply)
    return reply, sources, trace_id, extracted, plan_steps, tid


async def iter_rag_stream_prepare(
    message: str,
    *,
    top_k: int = 3,
    system_prompt: str | None = None,
    image_base64: str | None = None,
    image_media_type: str = "image/png",
    thread_id: str | None = None,
) -> AsyncIterator[dict[str, Any]]:
    """U-003：流式准备阶段。先 yield SSE 进度，最后 yield ready 载荷。

    进度事件：``{"kind": "sse", "data": {...}}``
    就绪：``{"kind": "ready", "data": {rag_prompt, sources, early, ...}}``
    """
    if image_base64:
        yield {
            "kind": "sse",
            "data": event_status("vision", "正在读图识别告警…"),
        }

    user_message, retrieval_query, pre_steps, extracted = await resolve_rag_inputs(
        message,
        image_base64=image_base64,
        image_media_type=image_media_type,
    )
    if extracted and extracted.upper() != "UNKNOWN":
        yield {"kind": "sse", "data": event_vision_extract(extracted)}

    yield {
        "kind": "sse",
        "data": event_status("agents", "Multi-Agent 检索与规划中…"),
    }

    tid = resolve_thread_id(thread_id)
    rag_prompt, sources, early, trace_id, plan_steps, tid, progress = (
        await run_multi_agent_prepare(
            user_message,
            top_k=top_k,
            system_prompt=system_prompt,
            search_query=retrieval_query,
            pre_trace_steps=pre_steps,
            thread_id=tid,
            anchor_candidate=extracted,
        )
    )
    for ev in progress:
        yield {"kind": "sse", "data": ev}

    yield {
        "kind": "ready",
        "data": {
            "rag_prompt": rag_prompt,
            "sources": sources,
            "early": early,
            "trace_id": trace_id,
            "extracted": extracted,
            "user_message": user_message,
            "plan_steps": plan_steps,
            "thread_id": tid,
        },
    }
