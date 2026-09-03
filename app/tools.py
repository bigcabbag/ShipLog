"""M6.0：On-call 三工具（LangChain @tool + Pydantic 参数）。"""

from __future__ import annotations

import json

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from app.rag.graph import run_crag_invoke
from app.rag.oncall_data import get_service_topology, query_incidents


class SearchRunbookInput(BaseModel):
    query: str = Field(description="要在 Runbook/复盘/架构文档中检索的中文问题")
    top_k: int = Field(default=3, ge=1, le=10, description="返回文档块数量")


class QueryIncidentInput(BaseModel):
    service: str | None = Field(
        default=None,
        description="服务名，如 redis、search-service、payment-service",
    )
    keyword: str | None = Field(
        default=None,
        description="标题/根因/摘要关键词，如 OOM、502、FLUSHALL",
    )
    limit: int = Field(default=5, ge=1, le=20, description="最多返回条数")


class ServiceTopologyInput(BaseModel):
    service: str = Field(
        description="服务名，如 order-service、payment-service、gateway",
    )


def _dump(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False)


async def _search_runbook(query: str, top_k: int = 3) -> str:
    result = await run_crag_invoke(
        query,
        top_k=top_k,
        search_query=query,
    )
    if result.get("route") == "abstain" or result.get("abstain_reply"):
        return _dump(
            {
                "tool": "search_runbook",
                "status": "abstain",
                "message": result.get("abstain_reply", ""),
            }
        )
    sources = result.get("sources") or []
    return _dump(
        {
            "tool": "search_runbook",
            "status": "ok",
            "source_count": len(sources),
            "sources": sources,
            "context_prompt": result.get("rag_prompt", ""),
        }
    )


async def _query_incident(
    service: str | None = None,
    keyword: str | None = None,
    limit: int = 5,
) -> str:
    rows = query_incidents(service=service, keyword=keyword, limit=limit)
    return _dump(
        {
            "tool": "query_incident",
            "status": "ok",
            "count": len(rows),
            "incidents": rows,
        }
    )


async def _get_topology(service: str) -> str:
    row = get_service_topology(service)
    if row is None:
        return _dump(
            {
                "tool": "get_service_topology",
                "status": "not_found",
                "service": service,
                "message": f"未找到服务 {service} 的拓扑记录",
            }
        )
    return _dump({"tool": "get_service_topology", "status": "ok", **row})


def make_oncall_tools(default_top_k: int = 3) -> list[StructuredTool]:
    """按请求 top_k 构造工具列表。"""

    async def search_runbook(query: str, top_k: int = default_top_k) -> str:
        """搜索 ShipLog 知识库 Runbook、事故复盘与架构文档。
        用于：怎么排查、第一步做什么、处理步骤、SOP。"""
        return await _search_runbook(query, top_k=top_k)

    async def query_incident_tool(
        service: str | None = None,
        keyword: str | None = None,
        limit: int = 5,
    ) -> str:
        """查询 PostgreSQL 历史事故表。
        用于：以前出过吗、上次根因、类似事故、上个月 OOM。"""
        return await _query_incident(service=service, keyword=keyword, limit=limit)

    async def get_service_topology_tool(service: str) -> str:
        """查询服务依赖拓扑：上下游、端口、中间件。
        用于：还影响谁、依赖谁、blast radius、502 连锁。"""
        return await _get_topology(service)

    return [
        StructuredTool.from_function(
            coroutine=search_runbook,
            name="search_runbook",
            description=search_runbook.__doc__ or "",
            args_schema=SearchRunbookInput,
        ),
        StructuredTool.from_function(
            coroutine=query_incident_tool,
            name="query_incident",
            description=query_incident_tool.__doc__ or "",
            args_schema=QueryIncidentInput,
        ),
        StructuredTool.from_function(
            coroutine=get_service_topology_tool,
            name="get_service_topology",
            description=get_service_topology_tool.__doc__ or "",
            args_schema=ServiceTopologyInput,
        ),
    ]
