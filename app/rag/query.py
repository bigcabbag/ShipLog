"""M5.3：RAG 请求入参解析（文字 + 可选截图）。"""

from __future__ import annotations

from app.rag.vision import build_retrieval_query, extract_query_from_image

DEFAULT_IMAGE_ONLY_MESSAGE = "请根据截图中的告警信息，给出排查建议。"


async def resolve_rag_inputs(
    message: str,
    *,
    image_base64: str | None = None,
    image_media_type: str = "image/png",
) -> tuple[str, str, list[dict], str | None]:
    """返回 (user_message, retrieval_query, pre_trace_steps, extracted_query)。"""
    text = message.strip()
    if not text and not image_base64:
        raise ValueError("message 与 image_base64 至少提供一个")

    user_message = text or DEFAULT_IMAGE_ONLY_MESSAGE
    retrieval_query = user_message
    pre_steps: list[dict] = []
    extracted: str | None = None

    if image_base64:
        extracted = await extract_query_from_image(
            text,
            image_base64,
            media_type=image_media_type,
        )
        retrieval_query = build_retrieval_query(text, extracted)
        pre_steps.append(
            {
                "step": "vision_extract",
                "has_image": True,
                "user_message": text,
                "extracted_query": extracted,
                "retrieval_query": retrieval_query,
            }
        )

    return user_message, retrieval_query, pre_steps, extracted
