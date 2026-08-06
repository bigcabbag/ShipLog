"""M6.2：会话上下文工具（无 LangGraph 依赖，避免循环 import）。"""

from __future__ import annotations

from typing import Literal, TypedDict, cast

from langchain_core.runnables.config import RunnableConfig

MAX_TURN_HISTORY = 6
USER_CONTENT_MAX = 500
ASSISTANT_CONTENT_MAX = 800
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
