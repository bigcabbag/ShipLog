"""M5.1：RAG 请求 trace 日志（PostgreSQL，按 trace_id 回放检索过程）。

对外接口不变：new_trace_id() / doc_entry() / save_trace() / load_trace()。
存储从 JSONL 迁移到 PostgreSQL rag_traces 表（trace_id 唯一索引）。
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import uuid4

from langchain_core.documents import Document
from sqlalchemy import create_engine, text

from app.config import get_database_url
from app.rag.bm25_index import doc_key

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS rag_traces (
    trace_id   VARCHAR(16) PRIMARY KEY,
    question   TEXT,
    top_k      INTEGER,
    route      TEXT,
    rewrite_count INTEGER DEFAULT 0,
    steps      JSONB DEFAULT '[]'::jsonb,
    abstain_reply TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);
"""


def _ensure_table() -> None:
    engine = create_engine(get_database_url())
    with engine.begin() as conn:
        conn.execute(text(_CREATE_TABLE_SQL))


def new_trace_id() -> str:
    return uuid4().hex[:16]


def doc_entry(doc: Document, rank: int) -> dict[str, object]:
    return {
        "rank": rank,
        "chunk_id": doc.metadata.get("chunk_id") or doc_key(doc),
        "source": str(doc.metadata.get("source", "")),
    }


def save_trace(record: dict[str, object]) -> None:
    _ensure_table()
    engine = create_engine(get_database_url())
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO rag_traces
                    (trace_id, question, top_k, route, rewrite_count,
                     steps, abstain_reply, created_at)
                VALUES
                    (:trace_id, :question, :top_k, :route, :rewrite_count,
                     CAST(:steps AS jsonb), :abstain_reply, :created_at)
                ON CONFLICT (trace_id) DO NOTHING
                """
            ),
            {
                "trace_id": record.get("trace_id"),
                "question": record.get("question"),
                "top_k": record.get("top_k"),
                "route": record.get("route"),
                "rewrite_count": record.get("rewrite_count", 0),
                "steps": json.dumps(
                    record.get("steps", []), ensure_ascii=False
                ),
                "abstain_reply": record.get("abstain_reply"),
                "created_at": record.get(
                    "created_at", datetime.now(UTC).isoformat()
                ),
            },
        )


def load_trace(trace_id: str) -> dict | None:
    _ensure_table()
    engine = create_engine(get_database_url())
    with engine.connect() as conn:
        result = conn.execute(
            text(
                """
                SELECT trace_id, question, top_k, route, rewrite_count,
                       steps, abstain_reply, created_at
                FROM rag_traces WHERE trace_id = :tid
                """
            ),
            {"tid": trace_id},
        )
        row = result.fetchone()

    if row is None:
        return None

    return {
        "trace_id": row.trace_id,
        "question": row.question,
        "top_k": row.top_k,
        "route": row.route,
        "rewrite_count": row.rewrite_count,
        "steps": row.steps if isinstance(row.steps, list) else json.loads(row.steps),
        "abstain_reply": row.abstain_reply,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }
