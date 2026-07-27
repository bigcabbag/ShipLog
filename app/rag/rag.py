from app.llm import chat
from app.rag.graph import run_crag_prepare


async def rag_chat(
    message: str,
    *,
    top_k: int = 3,
    system_prompt: str | None = None,
) -> tuple[str, list[dict], str]:
    rag_prompt, sources, early, trace_id = await run_crag_prepare(
        message,
        top_k=top_k,
        system_prompt=system_prompt,
    )
    if early is not None:
        return early, sources, trace_id

    reply = await chat(message, system_prompt=rag_prompt)
    return reply, sources, trace_id


async def prepare_rag_stream_async(
    message: str,
    *,
    top_k: int = 3,
    system_prompt: str | None = None,
) -> tuple[str | None, list[dict], str | None, str]:
    """RAG 流式：CRAG 预处理（M4.2 LangGraph）+ trace_id（M4.4）。"""
    return await run_crag_prepare(
        message,
        top_k=top_k,
        system_prompt=system_prompt,
    )
