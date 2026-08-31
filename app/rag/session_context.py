"""M6.2：会话上下文工具（无 LangGraph 依赖，避免循环 import）。"""

from __future__ import annotations

from typing import Literal, TypedDict, cast

from langchain_core.runnables.config import RunnableConfig

MAX_TURN_HISTORY = 6
USER_CONTENT_MAX = 500
ASSISTANT_CONTENT_MAX = 800
INCIDENT_ANCHOR_MAX = 240
# generate 层写 turn_history 时 aupdate_state 必须指定 as_node（多节点图否则 Ambiguous update）
TURN_HISTORY_AS_NODE = "merge"

REFERENTIAL_MARKERS = (
    "刚才",
    "那个",
    "上面",
    "上次",
    "继续",
    "还影响",
    "然后呢",
)

# 用户明确换题时清空旧锚点（U-008 事故锚点）
CLEAR_ANCHOR_MARKERS = (
    "新告警",
    "另一个问题",
    "换个问题",
    "新的问题",
    "换一个故障",
)

TurnRole = Literal["user", "assistant"]


class TurnMessage(TypedDict):
    role: TurnRole
    content: str


def graph_config(thread_id: str) -> RunnableConfig:
    """LangGraph RunnableConfig：面试可讲「thread_id = 会话主键」。"""
    return cast(
        RunnableConfig,
        {"configurable": {"thread_id": thread_id.strip()}},
    )


def format_turn_history(history: list[dict]) -> str:
    if not history:
        return "（无历史对话）"
    lines: list[str] = []
    for item in history[-MAX_TURN_HISTORY:]:
        role = str(item.get("role", "")).strip()
        content = str(item.get("content", "")).strip()
        if not content:
            continue
        label = "用户" if role == "user" else "助手"
        lines.append(f"- {label}：{content}")
    return "\n".join(lines) if lines else "（无历史对话）"


def last_user_turn(history: list[dict]) -> str | None:
    for item in reversed(history):
        if item.get("role") == "user":
            text = str(item.get("content", "")).strip()
            if text:
                return text
    return None


def enrich_question_with_history(question: str, history: list[dict]) -> str:
    """指代消解：「刚才那个」类短问句拼上一轮用户问题（业界 query rewrite 轻量版）。"""
    text = question.strip()
    if not text or not history:
        return text
    if not any(marker in text for marker in REFERENTIAL_MARKERS):
        return text
    prev = last_user_turn(history)
    if not prev:
        return text
    return f"{text}（上下文：上一轮用户问的是「{prev[:200]}」）"


def _clip_anchor(text: str) -> str:
    return text.strip()[:INCIDENT_ANCHOR_MAX]


def wants_clear_anchor(question: str) -> bool:
    return any(m in question for m in CLEAR_ANCHOR_MARKERS)


def resolve_incident_anchor(
    *,
    query: str,
    prior_anchor: str | None,
    candidate: str | None = None,
) -> tuple[str, str | None]:
    """把「当前事故」钉进检索 query。

    返回 ``(search_query, anchor_to_store)``。
    - 无先验：用 candidate（读图）或 query 建锚点
    - 有先验且未换题：检索前缀先验，锚点不变（避免跟进句劫持主题）
    - 换题标记：丢弃先验，按本轮重建
    """
    q = query.strip()
    cand = (candidate or "").strip()
    if cand.upper() == "UNKNOWN":
        cand = ""
    prior = (prior_anchor or "").strip() or None

    if wants_clear_anchor(q) or not prior:
        seed = cand or q
        anchor = _clip_anchor(seed) if seed else None
        if anchor and q and anchor not in q:
            return f"{anchor} {q}".strip(), anchor
        return q or (anchor or ""), anchor

    # 跟进轮：先验钉死检索，避免「反思 OOM」抢走主题
    if prior in q:
        return q, prior
    return f"{prior} | {q}".strip(), prior


def format_anchor_system_note(anchor: str | None) -> str | None:
    text = (anchor or "").strip()
    if not text:
        return None
    return (
        f"当前事故锚点：{text}。"
        "回答必须围绕该锚点；禁止改口成其他故障类型或引用无关 Runbook。"
    )


def trim_turn_history(history: list[dict]) -> list[dict]:
    out: list[dict] = []
    for item in history[-MAX_TURN_HISTORY:]:
        role = item.get("role")
        content = str(item.get("content", "")).strip()
        if not content:
            continue
        limit = USER_CONTENT_MAX if role == "user" else ASSISTANT_CONTENT_MAX
        out.append(
            {
                "role": "user" if role == "user" else "assistant",
                "content": content[:limit],
            }
        )
    return out
