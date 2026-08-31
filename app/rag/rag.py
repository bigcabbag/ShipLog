from app.llm import chat
from app.rag.multi_agent_graph import run_multi_agent_prepare
from app.rag.query import resolve_rag_inputs
from app.rag.session import load_thread_history, record_thread_turn, resolve_thread_id


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
    rag_prompt, sources, early, trace_id, plan_steps, _tid = await run_multi_agent_prepare(
        user_message,
        top_k=top_k,
        system_prompt=system_prompt,
        search_query=retrieval_query,
        pre_trace_steps=pre_steps,
        thread_id=tid,
        anchor_candidate=extracted,
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


async def prepare_rag_stream_async(
    message: str,
    *,
    top_k: int = 3,
    system_prompt: str | None = None,
    image_base64: str | None = None,
    image_media_type: str = "image/png",
    thread_id: str | None = None,
) -> tuple[
    str | None,
    list[dict],
    str | None,
    str,
    str | None,
    str,
    list[str],
    str,
]:
    """RAG 流式：返回 (rag_prompt, sources, early, trace_id, extracted, user_message, plan_steps, thread_id)。"""
    user_message, retrieval_query, pre_steps, extracted = await resolve_rag_inputs(
        message,
        image_base64=image_base64,
        image_media_type=image_media_type,
    )
    tid = resolve_thread_id(thread_id)
    rag_prompt, sources, early, trace_id, plan_steps, _tid = await run_multi_agent_prepare(
        user_message,
        top_k=top_k,
        system_prompt=system_prompt,
        search_query=retrieval_query,
        pre_trace_steps=pre_steps,
        thread_id=tid,
        anchor_candidate=extracted,
    )
    return rag_prompt, sources, early, trace_id, extracted, user_message, plan_steps, tid
