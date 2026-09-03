"""U-014：知识库文档元数据（版本 / 时间 / 主题 / 类型）。"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path

_DATE_PREFIX_RE = re.compile(r"^\d{4}-\d{2}(?:-\d{2})?-")

# 文件夹 → 文档类型（冲突时 Runbook 优先于 Postmortem）
_FOLDER_DOC_TYPE = {
    "runbooks": "runbook",
    "postmortems": "postmortem",
    "architecture": "architecture",
    "demo": "demo",
    "samples": "sample",
}

DOC_TYPE_PRIORITY = {
    "runbook": 0,
    "architecture": 1,
    "postmortem": 2,
    "demo": 3,
    "sample": 4,
    "upload": 5,
    "other": 6,
}


def infer_doc_type(source: str) -> str:
    parts = Path(source.replace("\\", "/")).parts
    if len(parts) >= 2:
        folder = parts[0].lower()
        if folder in _FOLDER_DOC_TYPE:
            return _FOLDER_DOC_TYPE[folder]
    if len(parts) == 1 and source.lower().endswith((".pdf", ".md")):
        return "upload"
    return "other"


def infer_topic(source: str) -> str:
    """去掉文件名日期前缀，便于 Runbook / Postmortem 对齐同一主题。"""
    stem = Path(source.replace("\\", "/")).stem
    return _DATE_PREFIX_RE.sub("", stem).lower()


def content_version(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def file_updated_at(path: Path | None) -> str:
    if path is not None and path.is_file():
        ts = path.stat().st_mtime
        return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def stamp_document_metadata(
    *,
    source: str,
    cleaned_text: str,
    path: Path | None = None,
    extra: dict | None = None,
) -> dict:
    meta = {
        "source": source,
        "page": 0,
        "doc_type": infer_doc_type(source),
        "topic": infer_topic(source),
        "doc_version": content_version(cleaned_text),
        "updated_at": file_updated_at(path),
    }
    if extra:
        meta.update(extra)
    return meta
