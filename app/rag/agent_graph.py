"""M6.0：LangGraph Tool Calling Agent（选工具 → 执行 → 汇总生成）。"""

from __future__ import annotations

import json
import operator
from functools import lru_cache
from typing import Annotated, Literal, Required, TypedDict

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from app.llm import get_llm
from app.rag.trace import new_trace_id, save_trace
from app.tools import make_oncall_tools

MAX_TOOL_ROUNDS = 3

AGENT_SYSTEM = """你是 ShipLog On-call 故障排查助手。根据用户问题，必须调用合适的工具获取事实后再回答。

工具选择指南：
- search_runbook：排查步骤、Runbook、怎么处理、第一步做什么
- query_incident：历史事故、以前出过吗、上次根因、OOM/502 类过往案例
- get_service_topology：服务依赖、还影响谁、上下游、blast radius

规则：
1. 至少调用一个工具；复杂问题可组合多个工具
2. 不要编造命令或数据；工具无结果时明确说明
3. 涉及 FLUSHALL、删库等危险操作必须提醒需审批
4. 工具返回 JSON 后，用中文给出结构化排查建议"""


class AgentState(TypedDict, total=False):
    question: Required[str]
    top_k: Required[int]
    trace_id: Required[str]
    search_query: str
    system_prompt: str | None
    messages: Annotated[list, operator.add]
    trace_steps: Annotated[list[dict], operator.add]
    tool_rounds: int
    route: Literal["generate", "abstain"]
    sources: list[dict]
    rag_prompt: str
    abstain_reply: str | None


def _summarize_tool_content(content: str, max_len: int = 240) -> str:
    text = content.strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def _tool_trace_step(msg: AIMessage) -> list[dict]:
    steps: list[dict] = []
    for call in msg.tool_calls or []:
        steps.append(
            {
                "step": "tool_start",
                "tool_name": call.get("name"),
                "args": call.get("args", {}),
            }
        )
    return steps


def _tool_result_steps(messages: list) -> list[dict]:
    steps: list[dict] = []
    for msg in messages:
        if not isinstance(msg, ToolMessage):
            continue
        steps.append(
            {
                "step": "tool_end",
                "tool_name": msg.name,
                "summary": _summarize_tool_content(str(msg.content)),
            }
        )
    return steps


def _collect_sources(messages: list) -> list[dict]:
    sources: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for msg in messages:
        if not isinstance(msg, ToolMessage):
            continue
        try:
            data = json.loads(str(msg.content))
        except json.JSONDecodeError:
            continue
        if data.get("tool") != "search_runbook":
            continue
        for item in data.get("sources") or []:
            key = (str(item.get("source", "")), str(item.get("page", "")))
            if key in seen:
                continue
            seen.add(key)
            sources.append(item)
    return sources


def _build_tool_context(messages: list) -> str:
    parts: list[str] = []
    for msg in messages:
        if isinstance(msg, ToolMessage):
            parts.append(f"### 工具 {msg.name} 返回\n{msg.content}")
        elif isinstance(msg, AIMessage) and msg.content and not msg.tool_calls:
            parts.append(f"### Agent 草稿\n{msg.content}")
    return "\n\n".join(parts) if parts else "（无工具结果）"


async def _agent_node(state: AgentState) -> dict:
    llm = get_llm().bind_tools(make_oncall_tools(state["top_k"]))
    messages = state.get("messages") or []
    rounds = state.get("tool_rounds", 0)

    last_error: Exception | None = None
    response: AIMessage | None = None
    for attempt in range(2):
        try:
            response = await llm.ainvoke(messages)
            if not isinstance(response, AIMessage):
                response = AIMessage(content=str(response))
            break
        except Exception as exc:
            last_error = exc
            messages = messages + [
                SystemMessage(content="上次工具调用 JSON 无效，请重试并严格按 schema 传参。")
            ]
    if response is None:
        raise last_error or RuntimeError("Agent 调用失败")

    steps = _tool_trace_step(response)
    if response.tool_calls:
        return {
            "messages": [response],
            "trace_steps": steps,
            "tool_rounds": rounds + 1,
        }

    return {
        "messages": [response],
        "trace_steps": steps,
        "route": "generate",
    }


async def _tools_node(state: AgentState) -> dict:
    tools = make_oncall_tools(state["top_k"])
    node = ToolNode(tools)
    result = await node.ainvoke(state)
    new_messages = result.get("messages") or []
    return {
        "messages": new_messages,
        "trace_steps": _tool_result_steps(new_messages),
    }


async def _synthesize_node(state: AgentState) -> dict:
    messages = state.get("messages") or []
    sources = _collect_sources(messages)
    tool_context = _build_tool_context(messages)

    for msg in messages:
        if isinstance(msg, ToolMessage):
            try:
                data = json.loads(str(msg.content))
            except json.JSONDecodeError:
                continue
            if data.get("status") == "abstain" and not sources:
                reply = data.get("message") or "知识库中未找到相关 Runbook"
                return {
                    "route": "abstain",
                    "abstain_reply": reply,
                    "sources": [],
                    "trace_steps": [{"step": "agent_synthesize", "route": "abstain"}],
                }

    rag_prompt = (
        "你是 ShipLog On-call 故障排查助手。请仅根据以下工具返回的事实回答。\n"
        "规则：\n"
        "1. 不要编造 shell 命令或配置\n"
        "2. FLUSHALL、删库等危险操作必须提醒需审批\n"
        "3. 工具无相关数据时明确说明，并建议下一步\n\n"
        f"工具结果：\n{tool_context}"
    )
    extra = state.get("system_prompt")
    if extra:
        rag_prompt = f"{extra}\n\n{rag_prompt}"

    return {
        "route": "generate",
        "sources": sources,
        "rag_prompt": rag_prompt,
        "trace_steps": [
            {
                "step": "agent_synthesize",
                "route": "generate",
                "source_count": len(sources),
                "tools_used": [
                    m.name for m in messages if isinstance(m, ToolMessage)
                ],
            }
        ],
    }


def _route_after_agent(state: AgentState) -> str:
    messages = state.get("messages") or []
    if not messages:
        return "synthesize"
    last = messages[-1]
    if isinstance(last, AIMessage) and last.tool_calls:
        if state.get("tool_rounds", 0) >= MAX_TOOL_ROUNDS:
            return "synthesize"
        return "tools"
    return "synthesize"


@lru_cache
def get_agent_graph():
    builder = StateGraph(AgentState)
    builder.add_node("agent", _agent_node)
    builder.add_node("tools", _tools_node)
    builder.add_node("synthesize", _synthesize_node)

    builder.add_edge(START, "agent")
    builder.add_conditional_edges(
        "agent",
        _route_after_agent,
        {"tools": "tools", "synthesize": "synthesize"},
    )
    builder.add_edge("tools", "agent")
    builder.add_edge("synthesize", END)
    return builder.compile()


async def run_agent_prepare(
    message: str,
    *,
    top_k: int = 3,
    system_prompt: str | None = None,
    search_query: str | None = None,
    pre_trace_steps: list[dict] | None = None,
) -> tuple[str | None, list[dict], str | None, str]:
    """M6.0 Agent 预处理：选工具 → 汇总 → 返回 rag_prompt、sources、early_reply、trace_id。"""
    trace_id = new_trace_id()
    query = (search_query or message).strip() or message
    graph = get_agent_graph()

    result = await graph.ainvoke(
        {
            "question": message,
            "top_k": top_k,
            "trace_id": trace_id,
            "search_query": query,
            "system_prompt": system_prompt,
            "messages": [
                SystemMessage(content=AGENT_SYSTEM),
                HumanMessage(content=query),
            ],
            "trace_steps": [],
            "tool_rounds": 0,
        }
    )

    steps = list(pre_trace_steps or []) + (result.get("trace_steps") or [])
    save_trace(
        {
            "trace_id": trace_id,
            "question": message,
            "top_k": top_k,
            "route": result.get("route", "generate"),
            "rewrite_count": 0,
            "steps": steps,
            "abstain_reply": result.get("abstain_reply"),
        }
    )

    if result.get("route") == "abstain" or result.get("abstain_reply"):
        return None, [], result.get("abstain_reply"), trace_id

    return (
        result.get("rag_prompt"),
        result.get("sources") or [],
        None,
        trace_id,
    )
