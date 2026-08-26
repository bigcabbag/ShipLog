"""M6.25：Cross-Encoder 二阶段重排（RRF 粗排 → bge-reranker 精排）。"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

from langchain_core.documents import Document

from app.config import get_rerank_model

logger = logging.getLogger(__name__)

# bge-reranker 常见 max_length≈512 token；中文 chunk 过长会被硬截断，预截可省算力
_RERANK_TEXT_MAX_CHARS = 480


@lru_cache
def get_cross_encoder() -> Any:
    """懒加载 CrossEncoder；首次调用会下载/加载模型。"""
    from app.hf_bootstrap import ensure_hf_mirror

    ensure_hf_mirror()
    from sentence_transformers import CrossEncoder

    return CrossEncoder(get_rerank_model())


def rerank_documents(
    query: str,
    docs: list[Document],
    top_k: int,
    *,
    model: Any | None = None,
) -> list[Document]:
    """按 (query, doc) 相关性分数降序截断 Top-K。

    ``model`` 可注入（单测 mock）；默认用懒加载的 CrossEncoder。
    模型加载/推理失败时 **fail-open**：原序截断 Top-K，不拖垮整条检索。
    """
    if not docs or top_k <= 0:
        return []

    try:
        encoder = model if model is not None else get_cross_encoder()
        pairs = [
            [query, doc.page_content[:_RERANK_TEXT_MAX_CHARS]] for doc in docs
        ]
        scores = encoder.predict(pairs)
    except Exception as exc:
        logger.warning(
            "Rerank 失败，回退粗排 Top-%s（docs=%s）: %s",
            top_k,
            len(docs),
            exc,
        )
        return docs[:top_k]

    ranked = sorted(
        zip(docs, scores, strict=True),
        key=lambda item: float(item[1]),
        reverse=True,
    )
    return [doc for doc, _ in ranked[:top_k]]
