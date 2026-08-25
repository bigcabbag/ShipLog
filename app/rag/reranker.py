"""M6.25：Cross-Encoder 二阶段重排（RRF 粗排 → bge-reranker 精排）。"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from langchain_core.documents import Document

from app.config import get_rerank_model


@lru_cache
def get_cross_encoder() -> Any:
    """懒加载 CrossEncoder；首次调用会下载/加载模型。"""
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
    """
    if not docs or top_k <= 0:
        return []

    encoder = model if model is not None else get_cross_encoder()
    pairs = [[query, doc.page_content] for doc in docs]
    scores = encoder.predict(pairs)

    ranked = sorted(
        zip(docs, scores, strict=True),
        key=lambda item: float(item[1]),
        reverse=True,
    )
    return [doc for doc, _ in ranked[:top_k]]
