from app.llm import chat
from app.rag.graph import run_crag_prepare
from app.rag.query import resolve_rag_inputs


async def rag_chat(
    message: str,
    *,
    top_k: int = 3,
    system_prompt: str | None = None,
    image_base64: str | None = None,
    image_media_type: str = "image/png",
) -> tuple[str, list[dict], str, str | None]:
    user_message, retrieval_query, pre_steps, extracted = await resolve_rag_inputs(
        message,
        image_base64=image_base64,
        image_media_type=image_media_type,
    )
    rag_prompt, sources, early, trace_id = await run_crag_prepare(
        user_message,
        top_k=top_k,
        system_prompt=system_prompt,
        search_query=retrieval_query,
        pre_trace_steps=pre_steps,
    )
    if early is not None:
        return early, sources, trace_id, extracted

    reply = await chat(user_message, system_prompt=rag_prompt)
    return reply, sources, trace_id, extracted


async def prepare_rag_stream_async(
    message: str,
    *,
    top_k: int = 3,
    system_prompt: str | None = None,
    image_base64: str | None = None,
    image_media_type: str = "image/png",
) -> tuple[str | None, list[dict], str | None, str, str | None, str]:
    """RAG 流式：返回 (rag_prompt, sources, early, trace_id, extracted, user_message)。"""
    user_message, retrieval_query, pre_steps, extracted = await resolve_rag_inputs(
        message,
        image_base64=image_base64,
        image_media_type=image_media_type,
    )
    rag_prompt, sources, early, trace_id = await run_crag_prepare(
        user_message,
        top_k=top_k,
        system_prompt=system_prompt,
        search_query=retrieval_query,
        pre_trace_steps=pre_steps,
    )
    return rag_prompt, sources, early, trace_id, extracted, user_message
