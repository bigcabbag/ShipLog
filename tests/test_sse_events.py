"""U-003：SSE 进度事件契约单测。"""

from app.rag.sse_events import agent_progress_events, event_vision_extract


def test_vision_extract_event_shape():
    ev = event_vision_extract("DROP DATABASE prod")
    assert ev["event"] == "vision_extract"
    assert "DROP" in ev["extracted_query"]


def test_agent_dispatch_and_result_to_tool_events():
    steps = [
        {
            "step": "agent_dispatch",
            "tasks": [
                {"agent": "runbook", "args": {"query": "Redis 超时"}},
                {"agent": "topology", "args": {"service": "order-service"}},
            ],
        },
        {
            "step": "agent_result",
            "agent": "runbook",
            "tool_name": "search_runbook",
            "summary": "命中 redis-timeout",
        },
        {
            "step": "agent_result",
            "agent": "topology",
            "tool_name": "get_service_topology",
            "summary": "上下游 3 个",
        },
    ]
    events = agent_progress_events(steps)
    kinds = [e["event"] for e in events]
    assert kinds == ["tool_start", "tool_start", "tool_end", "tool_end"]
    assert events[0]["tool"] == "search_runbook"
    assert events[1]["tool"] == "get_service_topology"
    assert events[2]["summary"] == "命中 redis-timeout"


def test_safe_response_emits_status_and_tools():
    events = agent_progress_events(
        [
            {
                "step": "safe_response",
                "route": "generate",
                "agents_used": ["runbook", "incident"],
            }
        ]
    )
    assert events[0]["event"] == "status"
    assert events[0]["phase"] == "safe_response"
    kinds = [e["event"] for e in events[1:]]
    assert kinds == ["tool_start", "tool_end", "tool_start", "tool_end"]
    assert events[1]["tool"] == "search_runbook"
    assert events[3]["tool"] == "query_incident"
