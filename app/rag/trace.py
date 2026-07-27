"""M4.4：RAG 请求 trace 日志（JSONL，按 trace_id 回放检索过程）。"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from langchain_core.documents import Document

from app.rag.bm25_index import doc_key

TRACE_DIR = Path("data/traces")
TRACE_FILE = TRACE_DIR / "traces.jsonl"


def new_trace_id() -> str:
    return uuid4().hex[:16]


def doc_entry(doc: Document, rank: int) -> dict[str, object]:
    return {
        "rank": rank,
        "chunk_id": doc.metadata.get("chunk_id") or doc_key(doc),
        "source": str(doc.metadata.get("source", "")),
    }


def save_trace(record: dict[str, object]) -> None:
    TRACE_DIR.mkdir(parents=True, exist_ok=True)
    payload = dict(record)
    payload.setdefault("created_at", datetime.now(UTC).isoformat())
    with TRACE_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def load_trace(trace_id: str) -> dict | None:
    if not TRACE_FILE.exists():
        return None
    for line in TRACE_FILE.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("trace_id") == trace_id:
            return row
    return None
