"""M6.2：thread 对话轮次写入 Postgres checkpointer。"""

from __future__ import annotations

from langchain_core.runnables.config import RunnableConfig
from langgraph.types import Overwrite

from app.rag.session_context import (
    ASSISTANT_CONTENT_MAX,
    TURN_HISTORY_AS_NODE,
    USER_CONTENT_MAX,
    graph_config,
    trim_turn_history,
)


def resolve_thread_id(thread_id: str | None) -> str:
    """空 thread_id 时生成新 id（与 multi_agent 一致）。"""
    tid = (thread_id or "").strip()
    if tid:
        return tid
    from app.rag.trace import new_trace_id

    return new_trace_id()


async def _thread_graph_state(thread_id: str):
    from app.rag.multi_agent_graph import get_multi_agent_graph

    graph = await get_multi_agent_graph()
    config: RunnableConfig = graph_config(thread_id)
    state = await graph.aget_state(config)
    return graph, config, state


async def load_thread_history(thread_id: str) -> list[dict]:
    """从 checkpointer 读取 turn_history（generate 层多轮用）。"""
    tid = thread_id.strip()
    if not tid:
        return []
    _, _, state = await _thread_graph_state(tid)
    return list((state.values or {}).get("turn_history") or [])


async def record_thread_turn(
    thread_id: str,
    *,
    user: str,
    assistant: str,
) -> None:
    tid = thread_id.strip()
    user_text = user.strip()[:USER_CONTENT_MAX]
    assistant_text = assistant.strip()[:ASSISTANT_CONTENT_MAX]
    if not tid or not user_text or not assistant_text:
        return
    graph, config, state = await _thread_graph_state(tid)
    history = list((state.values or {}).get("turn_history") or [])
    history.extend(
        [
            {"role": "user", "content": user_text},
            {"role": "assistant", "content": assistant_text},
        ]
    )
    await graph.aupdate_state(
        config,
        {"turn_history": Overwrite(trim_turn_history(history))},
        as_node=TURN_HISTORY_AS_NODE,
    )
