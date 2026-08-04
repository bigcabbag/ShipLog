"""M6.1：Multi-Agent 协调 + 专家分工 + 危险操作安全策略分支。"""

from __future__ import annotations

import json
import operator
import re
from functools import lru_cache
from typing import Annotated, Literal, Required, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph

from app.llm import get_llm
from app.rag.agent_graph import _collect_sources, _summarize_tool_content
from app.rag.trace import new_trace_id, save_trace
from app.tools import _get_topology, _query_incident, _search_runbook

DANGEROUS_KEYWORDS = (
    "flushall",
    "flushdb",
    "drop table",
    "truncate table",
    "delete namespace",
    "删库",
    "删表",
    "清空 redis",
    "清空缓存",
)

HISTORICAL_MARKERS = (
    "事故",
    "怎么发生",
    "如何发生",
    "复盘",
    "历史",
    "以前",
    "上次",
    "出过吗",
    "根因",
    "案例",
)

COORDINATOR_SYSTEM = """你是 ShipLog On-call **协调 Agent**。根据用户问题，决定派哪些专家子任务。

专家及能力：
- runbook：排查步骤、Runbook、SOP、第一步做什么 → args 需 query（中文检索句）
- incident：历史事故、以前出过吗、类似根因 → args 可选 service、keyword、limit
- topology：服务上下游、还影响谁、blast radius → args 需 service（服务名）

规则：
1. 至少派 1 个专家；复杂问题可派 2～3 个
2. 只派与问题相关的专家；不要凑数
3. 只输出 JSON，不要 markdown 代码块

输出格式：
{"tasks":[{"agent":"runbook","args":{"query":"..."}},{"agent":"topology","args":{"service":"order-service"}}]}"""

SAFE_POLICY_PROMPT = """你是 ShipLog On-call 安全助手。用户询问了**危险操作或合规策略**问题。

你必须给出**完整、明确的策略回答**（禁止回复「无法回答」「未找到信息」等空白拒答）。

回答结构（必须全部包含）：
1. **结论**：直接回答「不能/禁止」或说明必须 SRE Lead 审批
2. **风险**：说明可能后果（如缓存雪崩、数据丢失、全站不可用）
3. **依据**：引用下方 Runbook 禁止条款或历史事故
4. **正确做法**：说明审批流程与替代方案（如逐出策略、回滚、限流）；**禁止**给出 FLUSHALL/DROP/TRUNCATE 等危险命令的具体执行步骤

工具结果：
{tool_context}"""

MERGE_PROMPT = """你是 ShipLog On-call 故障排查助手。请仅根据以下**多路专家**返回的事实回答。

汇总规则：
1. 不要编造 shell 命令或配置
2. 若 Runbook 与事故记录描述不一致，以 **Runbook 步骤 + topology 结构化依赖** 为准，事故记录作背景参考
3. 工具无相关数据时明确说明，并建议下一步
4. FLUSHALL、删库等危险操作必须提醒需审批

专家结果：
{tool_context}"""


class MultiAgentState(TypedDict, total=False):
    question: Required[str]
    top_k: Required[int]
    trace_id: Required[str]
    search_query: str
    system_prompt: str | None
    trace_steps: Annotated[list[dict], operator.add]
    safe_branch: bool
    coordinator_plan: dict
    tool_results: list[dict]
    route: Literal["generate", "abstain"]
    sources: list[dict]
    rag_prompt: str
    abstain_reply: str | None


def _question_text(state: MultiAgentState) -> str:
    return (state.get("search_query") or state["question"]).strip()


def needs_safe_branch(question: str) -> bool:
    """危险操作/策略题走 safe_response；历史复盘题除外。"""
    text = question.strip()
    lower = text.lower()
    if not any(k in lower or k in text for k in DANGEROUS_KEYWORDS):
        return False
    if any(m in text for m in HISTORICAL_MARKERS):
        return False
    return True


def _extract_json_object(raw: str) -> dict:
    text = raw.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        text = text[start : end + 1]
    return json.loads(text)


def _normalize_tasks(plan: dict) -> list[dict]:
    tasks = plan.get("tasks") or []
    allowed = {"runbook", "incident", "topology"}
    normalized: list[dict] = []
    for item in tasks:
        if not isinstance(item, dict):
            continue
        agent = str(item.get("agent", "")).strip().lower()
        if agent not in allowed:
            continue
        args = item.get("args") or {}
        if not isinstance(args, dict):
            args = {}
        normalized.append({"agent": agent, "args": args})
    return normalized


async def _safe_check_node(state: MultiAgentState) -> dict:
    question = _question_text(state)
    safe = needs_safe_branch(question)
    return {
        "safe_branch": safe,
        "trace_steps": [
            {
                "step": "safe_check",
                "route": "safe_response" if safe else "coordinator",
                "matched": safe,
            }
        ],
    }


def _route_after_safe_check(state: MultiAgentState) -> str:
    return "safe_response" if state.get("safe_branch") else "coordinator"


async def _safe_response_node(state: MultiAgentState) -> dict:
    question = _question_text(state)
    top_k = state["top_k"]
    lower = question.lower()

    policy_query = f"生产环境 危险操作 禁止 审批 {question}"
    runbook_raw = await _search_runbook(policy_query, top_k=top_k)

    incident_raw = ""
    if "flush" in lower or "redis" in lower or "缓存" in question:
        incident_raw = await _query_incident(keyword="FLUSHALL", limit=3)
    elif "drop" in lower or "truncate" in lower or "删" in question:
        incident_raw = await _query_incident(keyword="删", limit=3)

    tool_results = [
        {"agent": "runbook", "tool_name": "search_runbook", "content": runbook_raw, "args": {"query": policy_query}},
    ]
    if incident_raw:
        tool_results.append(
            {
                "agent": "incident",
                "tool_name": "query_incident",
                "content": incident_raw,
                "args": {"keyword": "FLUSHALL" if "flush" in lower else "删"},
            }
        )

    sources = _collect_sources_from_results(tool_results)
    tool_context = _build_results_context(tool_results)
    rag_prompt = SAFE_POLICY_PROMPT.format(tool_context=tool_context)
    extra = state.get("system_prompt")
    if extra:
        rag_prompt = f"{extra}\n\n{rag_prompt}"

    return {
        "route": "generate",
        "sources": sources,
        "rag_prompt": rag_prompt,
        "tool_results": tool_results,
        "trace_steps": [
            {
                "step": "safe_response",
                "route": "generate",
                "policy": True,
                "agents_used": [r["agent"] for r in tool_results],
                "source_count": len(sources),
            }
        ],
    }


async def _coordinator_node(state: MultiAgentState) -> dict:
    question = _question_text(state)
    llm = get_llm()
    raw = await llm.ainvoke(
        [
            SystemMessage(content=COORDINATOR_SYSTEM),
            HumanMessage(content=question),
        ]
    )
    content = raw.content if isinstance(raw.content, str) else str(raw.content)

    plan: dict = {"tasks": []}
    parse_error: str | None = None
    try:
        parsed = _extract_json_object(content)
        plan["tasks"] = _normalize_tasks(parsed)
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        parse_error = str(exc)

    if not plan["tasks"]:
        plan["tasks"] = [{"agent": "runbook", "args": {"query": question}}]

    dispatch = [
        {"agent": t["agent"], "args": t.get("args") or {}}
        for t in plan["tasks"]
    ]
    step: dict = {
        "step": "agent_dispatch",
        "tasks": dispatch,
        "agents": [t["agent"] for t in dispatch],
    }
    if parse_error:
        step["coordinator_fallback"] = True
        step["parse_error"] = parse_error[:120]

    return {
        "coordinator_plan": plan,
        "trace_steps": [step],
    }


async def _run_specialist(agent: str, args: dict, top_k: int) -> dict:
    if agent == "runbook":
        query = str(args.get("query") or "").strip() or "故障排查"
        content = await _search_runbook(query, top_k=int(args.get("top_k") or top_k))
        return {
            "agent": "runbook",
            "tool_name": "search_runbook",
            "args": {"query": query, "top_k": top_k},
            "content": content,
        }
    if agent == "incident":
        content = await _query_incident(
            service=args.get("service"),
            keyword=args.get("keyword"),
            limit=int(args.get("limit") or 5),
        )
        return {
            "agent": "incident",
            "tool_name": "query_incident",
            "args": {
                "service": args.get("service"),
                "keyword": args.get("keyword"),
                "limit": int(args.get("limit") or 5),
            },
            "content": content,
        }
    if agent == "topology":
        service = str(args.get("service") or "").strip() or "gateway"
        content = await _get_topology(service)
        return {
            "agent": "topology",
            "tool_name": "get_service_topology",
            "args": {"service": service},
            "content": content,
        }
    raise ValueError(f"未知专家: {agent}")


async def _specialists_node(state: MultiAgentState) -> dict:
    plan = state.get("coordinator_plan") or {}
    tasks = plan.get("tasks") or []
    top_k = state["top_k"]

    results: list[dict] = []
    trace_steps: list[dict] = []
    for task in tasks:
        agent = task.get("agent", "")
        args = task.get("args") or {}
        result = await _run_specialist(agent, args, top_k)
        results.append(result)
        trace_steps.append(
            {
                "step": "agent_result",
                "agent": agent,
                "tool_name": result["tool_name"],
                "args": result["args"],
                "summary": _summarize_tool_content(result["content"]),
            }
        )

    return {"tool_results": results, "trace_steps": trace_steps}


def _collect_sources_from_results(tool_results: list[dict]) -> list[dict]:
    """从专家 tool JSON 提取 Runbook sources（与 M6.0 去重逻辑一致）。"""
    from langchain_core.messages import ToolMessage

    messages = [
        ToolMessage(content=r["content"], name=r["tool_name"], tool_call_id=r["agent"])
        for r in tool_results
    ]
    return _collect_sources(messages)


def _build_results_context(tool_results: list[dict]) -> str:
    parts: list[str] = []
    for item in tool_results:
        parts.append(
            f"### 专家 {item['agent']}（{item['tool_name']}）\n{item['content']}"
        )
    return "\n\n".join(parts) if parts else "（无专家结果）"


async def _merge_node(state: MultiAgentState) -> dict:
    tool_results = state.get("tool_results") or []
    sources = _collect_sources_from_results(tool_results)
    tool_context = _build_results_context(tool_results)

    for item in tool_results:
        if item.get("agent") != "runbook":
            continue
        try:
            data = json.loads(str(item["content"]))
        except json.JSONDecodeError:
            continue
        if data.get("status") == "abstain" and not sources:
            reply = data.get("message") or "知识库中未找到相关 Runbook"
            return {
                "route": "abstain",
                "abstain_reply": reply,
                "sources": [],
                "trace_steps": [{"step": "agent_merge", "route": "abstain"}],
            }

    rag_prompt = MERGE_PROMPT.format(tool_context=tool_context)
    extra = state.get("system_prompt")
    if extra:
        rag_prompt = f"{extra}\n\n{rag_prompt}"

    agents_used = [r["agent"] for r in tool_results]
    return {
        "route": "generate",
        "sources": sources,
        "rag_prompt": rag_prompt,
        "trace_steps": [
            {
                "step": "agent_merge",
                "route": "generate",
                "agents_used": agents_used,
                "source_count": len(sources),
            }
        ],
    }


@lru_cache
def get_multi_agent_graph():
    builder = StateGraph(MultiAgentState)
    builder.add_node("safe_check", _safe_check_node)
    builder.add_node("safe_response", _safe_response_node)
    builder.add_node("coordinator", _coordinator_node)
    builder.add_node("specialists", _specialists_node)
    builder.add_node("merge", _merge_node)

    builder.add_edge(START, "safe_check")
    builder.add_conditional_edges(
        "safe_check",
        _route_after_safe_check,
        {"safe_response": "safe_response", "coordinator": "coordinator"},
    )
    builder.add_edge("safe_response", END)
    builder.add_edge("coordinator", "specialists")
    builder.add_edge("specialists", "merge")
    builder.add_edge("merge", END)
    return builder.compile()


async def run_multi_agent_prepare(
    message: str,
    *,
    top_k: int = 3,
    system_prompt: str | None = None,
    search_query: str | None = None,
    pre_trace_steps: list[dict] | None = None,
) -> tuple[str | None, list[dict], str | None, str]:
    """M6.1 Multi-Agent 预处理：安全分支 / 协调派单 → 专家 → 汇总。"""
    trace_id = new_trace_id()
    query = (search_query or message).strip() or message
    graph = get_multi_agent_graph()

    result = await graph.ainvoke(
        {
            "question": message,
            "top_k": top_k,
            "trace_id": trace_id,
            "search_query": query,
            "system_prompt": system_prompt,
            "trace_steps": [],
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
