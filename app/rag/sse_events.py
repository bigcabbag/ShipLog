"""U-003：SSE 进度事件契约（与 token/done 并列）。"""

from __future__ import annotations

AGENT_TO_TOOL = {
    "runbook": "search_runbook",
    "incident": "query_incident",
    "topology": "get_service_topology",
}


def event_status(phase: str, message: str) -> dict:
    return {"event": "status", "phase": phase, "message": message}


def event_vision_extract(extracted_query: str) -> dict:
    return {
        "event": "vision_extract",
        "extracted_query": extracted_query,
    }


def agent_progress_events(steps: list[dict]) -> list[dict]:
    """从 Multi-Agent trace steps 生成 tool_start / tool_end（稳定契约）。"""
    events: list[dict] = []
    for step in steps:
        kind = step.get("step")
        if kind == "agent_dispatch":
            for task in step.get("tasks") or []:
                if not isinstance(task, dict):
                    continue
                agent = str(task.get("agent", "")).strip()
                if not agent:
                    continue
                events.append(
                    {
                        "event": "tool_start",
                        "tool": AGENT_TO_TOOL.get(agent, agent),
                        "agent": agent,
                        "args": task.get("args") or {},
                    }
                )
        elif kind == "agent_result":
            agent = str(step.get("agent", "")).strip()
            tool = str(step.get("tool_name") or "").strip() or AGENT_TO_TOOL.get(
                agent, agent
            )
            events.append(
                {
                    "event": "tool_end",
                    "tool": tool,
                    "agent": agent,
                    "summary": str(step.get("summary") or "")[:240],
                }
            )
        elif kind == "safe_response":
            events.append(
                event_status("safe_response", "安全策略分支（危险操作提醒）")
            )
    return events
