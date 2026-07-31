# ShipLog 服务拓扑

## 系统概览

ShipLog 是一个研发 On-call 故障排查助手，服务于内部 SRE 和研发团队。整体架构分为三层：

```
用户层 → 网关层 (Nginx + Gateway) → 服务层 → 数据层
```

## 服务清单

| 服务名 | 语言 | 端口 | 依赖 | 职责 |
|--------|------|------|------|------|
| gateway | Go | 8080 | Redis, Consul | API 网关、限流、路由 |
| user-service | Java | 8081 | MySQL, Redis | 用户认证、权限 |
| order-service | Java | 8082 | MySQL, Redis, MQ | 订单创建、状态流转 |
| payment-service | Java | 8083 | MySQL, Redis, MQ | 支付渠道对接 |
| search-service | Python | 8084 | Elasticsearch | 商品搜索 |
| notify-service | Go | 8085 | Redis, MQ | 短信、推送通知 |

## 数据层

| 组件 | 版本 | 端口 | 用途 |
|------|------|------|------|
| MySQL | 8.0 | 3306 | 主业务数据（user, order, payment） |
| Redis | 7.0 | 6379 | 缓存、Session、分布式锁 |
| Elasticsearch | 8.11 | 9200 | 商品搜索、日志检索 |
| RabbitMQ | 3.12 | 5672 | 异步消息（订单、支付回调） |
| Consul | 1.15 | 8500 | 服务注册发现 |

## 依赖关系

```
gateway → user-service, order-service, payment-service, search-service
order-service → payment-service (RPC), notify-service (MQ)
payment-service → notify-service (MQ)
所有服务 → Consul (注册)
所有服务 → Redis (缓存)
```

## 部署

- K8s 集群：3 worker 节点，每服务 2-4 副本
- 命名空间：prod（生产）、staging（预发）
- 部署方式：ArgoCD GitOps，镜像从 Harbor 拉取

## 告警接入

- Prometheus + Grafana 监控
- Alertmanager → 飞书/钉钉 On-call 群
- 告警分级：P0（全站宕机）、P1（核心链路受损）、P2（非核心功能异常）
