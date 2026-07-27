from langchain_core.documents import Document

from app.rag.bm25_index import bm25_search, doc_key
from app.rag.store import get_vector_store

DEFAULT_TOP_K = 3
RRF_K = 60
RRF_POOL_FACTOR = 5
# 向量主、BM25 辅：避免 qa 卡因关键词堆叠压过 steps 文档
VECTOR_RRF_WEIGHT = 1.0
BM25_RRF_WEIGHT = 0.35


def _vector_search(query: str, pool_k: int) -> list[Document]:
    store = get_vector_store()
    if store._collection.count() == 0:
        return []
    return store.similarity_search(query, k=pool_k)


def _rrf_fuse(
    ranked_lists: list[tuple[list[Document], float]],
    top_k: int,
) -> list[Document]:
    scores: dict[str, float] = {}
    doc_by_key: dict[str, Document] = {}

    for ranked, weight in ranked_lists:
        for rank, doc in enumerate(ranked, start=1):
            key = doc_key(doc)
            doc_by_key[key] = doc
            scores[key] = scores.get(key, 0.0) + weight / (RRF_K + rank)

    merged_keys = sorted(scores.keys(), key=lambda k: scores[k], reverse=True)
    return [doc_by_key[k] for k in merged_keys[:top_k]]


def retrieve(
    query: str,
    top_k: int = DEFAULT_TOP_K,
    *,
    hybrid: bool = True,
) -> list[Document]:
    """混合检索：向量（语义）+ BM25（关键词），RRF 融合排名。"""
    if not hybrid:
        return _vector_search(query, top_k)

    pool_k = max(top_k * RRF_POOL_FACTOR, top_k)
    vector_docs = _vector_search(query, pool_k)
    sparse_docs = bm25_search(query, pool_k)

    if not vector_docs and not sparse_docs:
        return []
    if not sparse_docs:
        return vector_docs[:top_k]
    if not vector_docs:
        return sparse_docs[:top_k]

    return _rrf_fuse(
        [
            (vector_docs, VECTOR_RRF_WEIGHT),
            (sparse_docs, BM25_RRF_WEIGHT),
        ],
        top_k,
    )
