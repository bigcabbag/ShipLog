"""U-014：同主题多文档冲突处理（Runbook 优先 + 较新优先）。"""

from __future__ import annotations

from datetime import datetime

from langchain_core.documents import Document

from app.rag.kb_meta import DOC_TYPE_PRIORITY, infer_doc_type, infer_topic


def _topic_of(doc: Document) -> str:
    meta = doc.metadata or {}
    raw = meta.get("topic")
    if raw:
        return str(raw).lower()
    return infer_topic(str(meta.get("source", "")))


def _doc_type_of(doc: Document) -> str:
    meta = doc.metadata or {}
    raw = meta.get("doc_type")
    if raw:
        return str(raw)
    return infer_doc_type(str(meta.get("source", "")))


def _updated_at_ts(doc: Document) -> float:
    raw = str((doc.metadata or {}).get("updated_at") or "")
    if not raw:
        return 0.0
    try:
        # 支持 ...Z
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0.0


def _rank_key(doc: Document) -> tuple[int, float]:
    """越小/越大：类型优先级升序，时间降序 → 排序用 (-prio 不，用 tuple)。"""
    prio = DOC_TYPE_PRIORITY.get(_doc_type_of(doc), DOC_TYPE_PRIORITY["other"])
    return (prio, -_updated_at_ts(doc))


def resolve_kb_conflicts(docs: list[Document]) -> tuple[list[Document], list[str]]:
    """同 topic 多源时：按 Runbook>Architecture>Postmortem，再按 updated_at 新优先。

    返回 (重排后的 docs, 冲突提示列表)。不丢弃文档，只重排，避免误伤召回。
    """
    if len(docs) <= 1:
        return docs, []

    by_topic: dict[str, list[int]] = {}
    for i, doc in enumerate(docs):
        topic = _topic_of(doc)
        if not topic:
            continue
        by_topic.setdefault(topic, []).append(i)

    conflict_topics = {
        t for t, idxs in by_topic.items() if len({str(docs[i].metadata.get("source")) for i in idxs}) > 1
    }
    if not conflict_topics:
        return docs, []

    # 稳定重排：冲突主题内按策略排序，整体保持「各主题最优块靠前」
    ordered_indices: list[int] = []
    seen: set[int] = set()

    # 先按原顺序扫，遇到冲突主题则插入该主题全部（已按策略排序）
    for i, doc in enumerate(docs):
        if i in seen:
            continue
        topic = _topic_of(doc)
        if topic in conflict_topics:
            group = sorted(by_topic[topic], key=lambda idx: _rank_key(docs[idx]))
            for idx in group:
                if idx not in seen:
                    ordered_indices.append(idx)
                    seen.add(idx)
        else:
            ordered_indices.append(i)
            seen.add(i)

    notes: list[str] = []
    for topic in sorted(conflict_topics):
        sources = [str(docs[i].metadata.get("source", "?")) for i in by_topic[topic]]
        types = [_doc_type_of(docs[i]) for i in by_topic[topic]]
        notes.append(
            f"主题「{topic}」同时命中 {', '.join(sources)} "
            f"（类型: {', '.join(types)}）；已按 Runbook 优先、较新优先排序，操作步骤以 Runbook 为准。"
        )

    return [docs[i] for i in ordered_indices], notes
