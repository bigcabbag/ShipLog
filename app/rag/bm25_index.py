"""M4.3：BM25 稀疏检索索引（与 Chroma 向量库并行维护）。"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from langchain_core.documents import Document
from rank_bm25 import BM25Okapi

BM25_DIR = Path("data/bm25")
CORPUS_PATH = BM25_DIR / "corpus.json"

# 英文/路径整段 + 中文单字，兼顾 API 名与中文问句
_TOKEN_RE = re.compile(r"[\w/\.:-]+|[\u4e00-\u9fff]")


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text)]


def doc_key(doc: Document) -> str:
    chunk_id = doc.metadata.get("chunk_id")
    if chunk_id:
        return str(chunk_id)
    source = str(doc.metadata.get("source", ""))
    return f"{source}:{hash(doc.page_content)}"


def _load_records() -> list[dict[str, Any]]:
    if not CORPUS_PATH.exists():
        return []
    data = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        return []
    return data


def _save_records(records: list[dict[str, Any]]) -> None:
    BM25_DIR.mkdir(parents=True, exist_ok=True)
    CORPUS_PATH.write_text(
        json.dumps(records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    _get_bm25.cache_clear()


def _records_to_documents(records: list[dict[str, Any]]) -> list[Document]:
    return [
        Document(page_content=r["page_content"], metadata=dict(r.get("metadata") or {}))
        for r in records
    ]


@lru_cache
def _get_bm25() -> tuple[BM25Okapi | None, list[Document]]:
    records = _load_records()
    docs = _records_to_documents(records)
    if not docs:
        return None, []
    tokenized = [tokenize(d.page_content) for d in docs]
    return BM25Okapi(tokenized), docs


def sync_chunks(chunks: list[Document], source: str) -> int:
    """同名 source 先删后写，与 store.index_chunks 保持一致。"""
    records = _load_records()
    records = [r for r in records if r.get("metadata", {}).get("source") != source]

    for i, chunk in enumerate(chunks):
        chunk.metadata["source"] = source
        chunk.metadata["chunk_id"] = f"{source}:{i}"
        records.append(
            {
                "page_content": chunk.page_content,
                "metadata": dict(chunk.metadata),
            }
        )

    _save_records(records)
    return len(chunks)


def bm25_search(query: str, top_k: int) -> list[Document]:
    bm25, docs = _get_bm25()
    if bm25 is None or not docs:
        return []

    tokens = tokenize(query)
    if not tokens:
        return []

    scores = bm25.get_scores(tokens)
    ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)

    results: list[Document] = []
    for idx in ranked:
        if scores[idx] <= 0:
            break
        results.append(docs[idx])
        if len(results) >= top_k:
            break
    return results


def get_bm25_stats() -> dict[str, int]:
    return {"bm25_count": len(_load_records())}


def rebuild_from_vector_store() -> int:
    """从 Chroma 全量重建 BM25 语料（已有向量库、首次启用 M4.3 时用）。"""
    from app.rag.store import get_vector_store

    store = get_vector_store()
    count = int(store._collection.count())
    if count == 0:
        _save_records([])
        return 0

    raw = store.get(include=["documents", "metadatas"])
    records: list[dict[str, Any]] = []
    per_source_index: dict[str, int] = {}

    for text, meta in zip(raw["documents"], raw["metadatas"], strict=True):
        meta = dict(meta or {})
        source = str(meta.get("source", "unknown"))
        idx = per_source_index.get(source, 0)
        meta["chunk_id"] = meta.get("chunk_id") or f"{source}:{idx}"
        per_source_index[source] = idx + 1
        records.append({"page_content": text, "metadata": meta})

    _save_records(records)
    return len(records)
