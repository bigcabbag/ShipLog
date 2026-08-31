"""M6.1：Multi-Agent 协调 + 专家分工 + 危险操作安全策略分支。
M6.2：Planning 节点 + Postgres checkpointer 多轮 turn_history。
U-008：incident_anchor 跨轮钉住当前事故（检索 + generate）。
"""

from __future__ import annotations

import asyncio
import json
import operator
import re
from typing import Annotated, Literal, Required, TypedDict, cast

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.types import Overwrite

from app.llm import get_llm
from app.rag.agent_graph import _collect_sources, _summarize_tool_content
from app.rag.checkpointer import get_async_checkpointer
from app.rag.session import resolve_thread_id
from app.rag.session_context import (
    enrich_question_with_history,
    format_anchor_system_note,
    format_turn_history,
    graph_config,
    resolve_incident_anchor,
)
from app.rag.trace import new_trace_id, save_trace
from app.tools import _get_topology, _query_incident, _search_runbook

_graph = None
_graph_lock = asyncio.Lock()
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

COORDINATOR_SYSTEM = """你是 ShipLog On-call **协调 Agent**。根据用户问题、对话历史与排查计划，决定派哪些专家子任务。

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

PLANNING_SYSTEM = """你是 ShipLog On-call **规划 Agent**。根据用户问题与对话历史，输出 2～4 步排查计划（中文短句）。

规则：
1. 步骤具体、可执行，适合 On-call 值班场景
2. 简单问题可 1～2 步；复杂故障 3～4 步
3. 只输出 JSON，不要 markdown 代码块

输出格式：
{"plan_steps":["步骤1","步骤2","步骤3"]}"""

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
    incident_anchor: str | None
    trace_steps: Annotated[list[dict], operator.add]
    turn_history: Annotated[list[dict], operator.add]
    plan_steps: list[str]
    safe_branch: bool
    coordinator_plan: dict
    tool_results: list[dict]
    route: Literal["generate", "abstain"]
    sources: list[dict]
    rag_prompt: str
    abstain_reply: str | None


def _format_plan_steps(steps: list[str]) -> str:
    if not steps:
        return "（无显式计划，按问题直接排查）"
    return "\n".join(f"{i + 1}. {s}" for i, s in enumerate(steps))


def _question_text(state: MultiAgentState) -> str:
    return (state.get("search_query") or state["question"]).strip()


def _should_skip_planning_llm(question: str, history: list[dict]) -> bool:
    """首轮简单问句跳过 Planning LLM（fast-path，省延迟）。"""
    if history:
        return False
    text = question.strip()
    if len(text) > 80:
        return False
    complex_markers = ("还影响", "上下游", "事故", "根因", "多个", "对比", "以及", "分别")
    return not any(marker in text for marker in complex_markers)


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


async def _invoke_json_llm(*, system: str, user_content: str) -> tuple[dict | None, str | None]:
    llm = get_llm()
    raw = await llm.ainvoke(
        [SystemMessage(content=system), HumanMessage(content=user_content)]
    )
    content = raw.content if isinstance(raw.content, str) else str(raw.content)
    try:
        return _extract_json_object(content), None
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        return None, str(exc)


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


def _normalize_plan_steps(raw: dict, question: str) -> list[str]:
    steps = raw.get("plan_steps") or raw.get("steps") or []
    normalized: list[str] = []
    if isinstance(steps, list):
        for item in steps:
            text = str(item).strip()
            if text:
                normalized.append(text)
    if not normalized:
        normalized = [f"围绕「{question[:80]}」收集 Runbook / 拓扑 / 事故信息并给出建议"]
    return normalized[:4]


async def _safe_check_node(state: MultiAgentState) -> dict:
    question = _question_text(state)
    safe = needs_safe_branch(question)
    return {
        "safe_branch": safe,
        "trace_steps": [
            {
                "step": "safe_check",
                "route": "safe_response" if safe else "planning",
                "matched": safe,
            }
        ],
    }


def _route_after_safe_check(state: MultiAgentState) -> str:
    return "safe_response" if state.get("safe_branch") else "planning"


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


async def _planning_node(state: MultiAgentState) -> dict:
    question = _question_text(state)
    history = state.get("turn_history") or []

    if _should_skip_planning_llm(question, history):
        plan_steps = _normalize_plan_steps({}, question)
        return {
            "plan_steps": plan_steps,
            "trace_steps": [
                {
                    "step": "planning",
                    "plan_steps": plan_steps,
                    "history_turns": len(history),
                    "planning_skipped": True,
                }
            ],
        }

    history_text = format_turn_history(history)
    parsed, parse_error = await _invoke_json_llm(
        system=PLANNING_SYSTEM,
        user_content=(
            f"对话历史：\n{history_text}\n\n"
            f"当前问题：{question}\n\n"
            "请输出排查计划 JSON。"
        ),
    )
    plan_steps = _normalize_plan_steps(parsed or {}, question)

    step: dict = {
        "step": "planning",
        "plan_steps": plan_steps,
        "history_turns": len(history),
    }
    if parse_error:
        step["planning_fallback"] = True
        step["parse_error"] = parse_error[:120]

    return {"plan_steps": plan_steps, "trace_steps": [step]}


async def _coordinator_node(state: MultiAgentState) -> dict:
    question = _question_text(state)
    history_text = format_turn_history(state.get("turn_history") or [])
    plan_text = _format_plan_steps(state.get("plan_steps") or [])
    parsed, parse_error = await _invoke_json_llm(
        system=COORDINATOR_SYSTEM,
        user_content=(
            f"对话历史：\n{history_text}\n\n"
            f"排查计划：\n{plan_text}\n\n"
            f"当前问题：{question}\n\n"
            "请输出专家派单 JSON。"
        ),
    )

    plan: dict = {"tasks": _normalize_tasks(parsed or {})}
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


def _build_multi_agent_graph():
    builder = StateGraph(MultiAgentState)
    builder.add_node("safe_check", _safe_check_node)
    builder.add_node("safe_response", _safe_response_node)
    builder.add_node("planning", _planning_node)
    builder.add_node("coordinator", _coordinator_node)
    builder.add_node("specialists", _specialists_node)
    builder.add_node("merge", _merge_node)

    builder.add_edge(START, "safe_check")
    builder.add_conditional_edges(
        "safe_check",
        _route_after_safe_check,
        {"safe_response": "safe_response", "planning": "planning"},
    )
    builder.add_edge("safe_response", END)
    builder.add_edge("planning", "coordinator")
    builder.add_edge("coordinator", "specialists")
    builder.add_edge("specialists", "merge")
    builder.add_edge("merge", END)
    return builder


async def get_multi_agent_graph():
    global _graph
    async with _graph_lock:
        if _graph is None:
            checkpointer = await get_async_checkpointer()
            _graph = _build_multi_agent_graph().compile(checkpointer=checkpointer)
        return _graph


def _unwrap_state_value(value: object) -> object:
    """checkpointer 回合里未改写的字段可能仍是 LangGraph Overwrite 包装。"""
    if isinstance(value, Overwrite):
        return value.value
    return value


def _state_str(value: object) -> str | None:
    raw = _unwrap_state_value(value)
    return raw if isinstance(raw, str) else None


def _state_route(value: object) -> Literal["generate", "abstain"]:
    raw = _unwrap_state_value(value)
    if raw in ("generate", "abstain"):
        return raw
    return "generate"


def _state_dict_list(value: object) -> list[dict]:
    raw = _unwrap_state_value(value)
    return raw if isinstance(raw, list) else []


def _state_str_list(value: object) -> list[str]:
    raw = _unwrap_state_value(value)
    if not isinstance(raw, list):
        return []
    return [str(item) for item in raw]


def _turn_invoke_payload(
    *,
    message: str,
    top_k: int,
    trace_id: str,
    search_query: str,
    system_prompt: str | None,
    incident_anchor: str | None,
) -> MultiAgentState:
    """每轮重置 ephemeral 字段；turn_history 由 checkpointer 保留；锚点显式 Overwrite。"""
    return cast(
        MultiAgentState,
        {
            "question": message,
            "top_k": top_k,
            "trace_id": trace_id,
            "search_query": search_query,
            "system_prompt": system_prompt,
            "incident_anchor": Overwrite(incident_anchor),
            "trace_steps": Overwrite([]),
            "plan_steps": Overwrite([]),
            "safe_branch": Overwrite(False),
            "coordinator_plan": Overwrite({}),
            "tool_results": Overwrite([]),
            "route": Overwrite("generate"),
            "sources": Overwrite([]),
            "rag_prompt": Overwrite(""),
            "abstain_reply": Overwrite(None),
        },
    )


async def run_multi_agent_prepare(
    message: str,
    *,
    top_k: int = 3,
    system_prompt: str | None = None,
    search_query: str | None = None,
    pre_trace_steps: list[dict] | None = None,
    thread_id: str | None = None,
    anchor_candidate: str | None = None,
) -> tuple[str | None, list[dict], str | None, str, list[str], str]:
    """M6.1 Multi-Agent 预处理；M6.2 返回 plan_steps 与 thread_id。"""
    trace_id = new_trace_id()
    query = (search_query or message).strip() or message
    tid = resolve_thread_id(thread_id)
    graph = await get_multi_agent_graph()
    config = graph_config(tid)

    prior = await graph.aget_state(config)
    prior_vals = prior.values or {}
    history = list(prior_vals.get("turn_history") or [])
    prior_anchor_raw = _unwrap_state_value(prior_vals.get("incident_anchor"))
    prior_anchor = prior_anchor_raw if isinstance(prior_anchor_raw, str) else None

    enriched_query = enrich_question_with_history(query, history)
    pinned_query, anchor = resolve_incident_anchor(
        query=enriched_query,
        prior_anchor=prior_anchor,
        candidate=anchor_candidate,
    )
    anchor_note = format_anchor_system_note(anchor)
    merged_system = system_prompt
    if anchor_note:
        merged_system = (
            f"{anchor_note}\n\n{system_prompt}" if system_prompt else anchor_note
        )

    result = await graph.ainvoke(
        _turn_invoke_payload(
            message=message,
            top_k=top_k,
            trace_id=trace_id,
            search_query=pinned_query,
            system_prompt=merged_system,
            incident_anchor=anchor,
        ),
        config,
    )

    route = _state_route(result.get("route"))
    abstain_reply = _state_str(result.get("abstain_reply"))
    rag_prompt = _state_str(result.get("rag_prompt"))
    sources = _state_dict_list(result.get("sources"))
    trace_steps = _state_dict_list(result.get("trace_steps"))
    plan_steps = _state_str_list(result.get("plan_steps"))

    steps = list(pre_trace_steps or []) + trace_steps
    if tid:
        steps = [{"step": "session", "thread_id": tid}] + steps
    if anchor:
        steps = [
            {
                "step": "incident_anchor",
                "anchor": anchor,
                "search_query": pinned_query,
                "cleared": bool(prior_anchor and prior_anchor != anchor),
            }
        ] + steps
    save_trace(
        {
            "trace_id": trace_id,
            "question": message,
            "top_k": top_k,
            "route": route,
            "rewrite_count": 0,
            "steps": steps,
            "abstain_reply": abstain_reply,
            "thread_id": tid,
            "plan_steps": plan_steps,
        }
    )

    if route == "abstain" or abstain_reply:
        return None, [], abstain_reply, trace_id, plan_steps, tid

    return (
        rag_prompt,
        sources,
        None,
        trace_id,
        plan_steps,
        tid,
    )
