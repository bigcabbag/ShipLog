"""M6.0：On-call 结构化数据（incidents + service_topology，PostgreSQL seed）。"""

from __future__ import annotations

import json
from datetime import UTC, datetime

from sqlalchemy import create_engine, text

from app.config import get_database_url

_INCIDENTS_DDL = """
CREATE TABLE IF NOT EXISTS incidents (
    id            SERIAL PRIMARY KEY,
    title         TEXT NOT NULL,
    service       TEXT NOT NULL,
    severity      TEXT NOT NULL,
    root_cause    TEXT NOT NULL,
    resolved_at   TIMESTAMPTZ NOT NULL,
    summary       TEXT NOT NULL
);
"""

_TOPOLOGY_DDL = """
CREATE TABLE IF NOT EXISTS service_topology (
    service        TEXT PRIMARY KEY,
    language       TEXT,
    ports          JSONB NOT NULL DEFAULT '[]'::jsonb,
    depends_on     JSONB NOT NULL DEFAULT '[]'::jsonb,
    depended_by    JSONB NOT NULL DEFAULT '[]'::jsonb,
    datastores     JSONB NOT NULL DEFAULT '[]'::jsonb,
    responsibility TEXT
);
"""

_INCIDENT_SEED = [
    {
        "title": "Redis 缓存被 FLUSHALL 导致数据库雪崩",
        "service": "redis",
        "severity": "P0",
        "root_cause": "开发人员误连生产 Redis 执行 FLUSHALL，缓存穿透导致 MySQL 连接池耗尽",
        "resolved_at": "2024-01-15T15:10:00+00:00",
        "summary": "全站不可用 40 分钟；紧急限流 + 手动重建热点缓存后恢复",
    },
    {
        "title": "支付服务 502 导致订单支付超时",
        "service": "payment-service",
        "severity": "P1",
        "root_cause": "v2.3.0 数据库端口配置错误（3307 非 3306），Pod CrashLoop",
        "resolved_at": "2024-03-08T10:45:00+00:00",
        "summary": "支付接口 502 持续 30 分钟；kubectl rollout undo 回滚后恢复",
    },
    {
        "title": "search-service Pod OOM 循环",
        "service": "search-service",
        "severity": "P1",
        "root_cause": "Elasticsearch 批量查询未分页导致内存暴涨 OOMKilled",
        "resolved_at": "2024-06-20T03:30:00+00:00",
        "summary": "商品搜索不可用 90 分钟；回滚 v1.8.2 后 Pod 稳定",
    },
    {
        "title": "order-service 依赖 payment 超时连锁",
        "service": "order-service",
        "severity": "P1",
        "root_cause": "payment-service 502 期间 order RPC 超时堆积",
        "resolved_at": "2024-03-08T10:45:00+00:00",
        "summary": "订单创建正常但支付链路失败；随 payment 回滚恢复",
    },
]

_TOPOLOGY_SEED = [
    {
        "service": "gateway",
        "language": "Go",
        "ports": [8080],
        "depends_on": ["redis", "consul", "user-service", "order-service", "payment-service", "search-service"],
        "depended_by": [],
        "datastores": ["redis"],
        "responsibility": "API 网关、限流、路由",
    },
    {
        "service": "user-service",
        "language": "Java",
        "ports": [8081],
        "depends_on": ["mysql", "redis", "consul"],
        "depended_by": ["gateway"],
        "datastores": ["mysql", "redis"],
        "responsibility": "用户认证、权限",
    },
    {
        "service": "order-service",
        "language": "Java",
        "ports": [8082],
        "depends_on": ["mysql", "redis", "rabbitmq", "payment-service", "notify-service", "consul"],
        "depended_by": ["gateway"],
        "datastores": ["mysql", "redis", "rabbitmq"],
        "responsibility": "订单创建、状态流转",
    },
    {
        "service": "payment-service",
        "language": "Java",
        "ports": [8083],
        "depends_on": ["mysql", "redis", "rabbitmq", "consul"],
        "depended_by": ["gateway", "order-service"],
        "datastores": ["mysql", "redis", "rabbitmq"],
        "responsibility": "支付渠道对接",
    },
    {
        "service": "search-service",
        "language": "Python",
        "ports": [8084],
        "depends_on": ["elasticsearch", "consul"],
        "depended_by": ["gateway"],
        "datastores": ["elasticsearch"],
        "responsibility": "商品搜索",
    },
    {
        "service": "notify-service",
        "language": "Go",
        "ports": [8085],
        "depends_on": ["redis", "rabbitmq", "consul"],
        "depended_by": ["order-service", "payment-service"],
        "datastores": ["redis", "rabbitmq"],
        "responsibility": "短信、推送通知",
    },
]


def ensure_oncall_tables() -> None:
    engine = create_engine(get_database_url())
    with engine.begin() as conn:
        conn.execute(text(_INCIDENTS_DDL))
        conn.execute(text(_TOPOLOGY_DDL))
        count = conn.execute(text("SELECT COUNT(*) FROM incidents")).scalar()
        if int(count or 0) == 0:
            for row in _INCIDENT_SEED:
                conn.execute(
                    text(
                        """
                        INSERT INTO incidents
                            (title, service, severity, root_cause, resolved_at, summary)
                        VALUES
                            (:title, :service, :severity, :root_cause, :resolved_at, :summary)
                        """
                    ),
                    row,
                )
        topo_count = conn.execute(text("SELECT COUNT(*) FROM service_topology")).scalar()
        if int(topo_count or 0) == 0:
            for row in _TOPOLOGY_SEED:
                conn.execute(
                    text(
                        """
                        INSERT INTO service_topology
                            (service, language, ports, depends_on, depended_by,
                             datastores, responsibility)
                        VALUES
                            (:service, :language, CAST(:ports AS jsonb),
                             CAST(:depends_on AS jsonb), CAST(:depended_by AS jsonb),
                             CAST(:datastores AS jsonb), :responsibility)
                        """
                    ),
                    {
                        **row,
                        "ports": json.dumps(row["ports"]),
                        "depends_on": json.dumps(row["depends_on"]),
                        "depended_by": json.dumps(row["depended_by"]),
                        "datastores": json.dumps(row["datastores"]),
                    },
                )


def query_incidents(
    *,
    service: str | None = None,
    keyword: str | None = None,
    limit: int = 5,
) -> list[dict]:
    ensure_oncall_tables()
    clauses = ["1=1"]
    params: dict = {"limit": limit}
    if service:
        clauses.append("service ILIKE :service")
        params["service"] = f"%{service.strip()}%"
    if keyword:
        clauses.append(
            "(title ILIKE :kw OR root_cause ILIKE :kw OR summary ILIKE :kw)"
        )
        params["kw"] = f"%{keyword.strip()}%"

    sql = f"""
        SELECT id, title, service, severity, root_cause, resolved_at, summary
        FROM incidents
        WHERE {' AND '.join(clauses)}
        ORDER BY resolved_at DESC
        LIMIT :limit
    """
    engine = create_engine(get_database_url())
    with engine.connect() as conn:
        rows = conn.execute(text(sql), params).fetchall()

    results: list[dict] = []
    for row in rows:
        resolved = row.resolved_at
        results.append(
            {
                "id": row.id,
                "title": row.title,
                "service": row.service,
                "severity": row.severity,
                "root_cause": row.root_cause,
                "resolved_at": resolved.isoformat() if resolved else None,
                "summary": row.summary,
            }
        )
    return results


def get_service_topology(service: str) -> dict | None:
    ensure_oncall_tables()
    engine = create_engine(get_database_url())
    with engine.connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT service, language, ports, depends_on, depended_by,
                       datastores, responsibility
                FROM service_topology
                WHERE service ILIKE :name
                """
            ),
            {"name": service.strip()},
        ).fetchone()
    if row is None:
        return None

    def _json_list(val: object) -> list:
        if isinstance(val, list):
            return val
        if isinstance(val, str):
            parsed = json.loads(val)
            return parsed if isinstance(parsed, list) else [parsed]
        if val is None:
            return []
        return list(val)  # type: ignore[arg-type]

    return {
        "service": row.service,
        "language": row.language,
        "ports": _json_list(row.ports),
        "depends_on": _json_list(row.depends_on),
        "depended_by": _json_list(row.depended_by),
        "datastores": _json_list(row.datastores),
        "responsibility": row.responsibility,
    }
