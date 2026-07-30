# Retrieval Eval @K=3 (hybrid (BM25+vector RRF))

- vector_count=44, bm25_count=44, questions=43
- scored=38, abstain=5

## 指标

| 指标 | 值 |
| --- | ---: |
| Recall@3 | 86.8% |
| Precision@3 | 52.6% |
| MRR@3 | 0.855 |

## 逐题明细

### ✅ [HIT] q01 (scored)（rank=1）

**问题：** Redis 连接超时怎么排查？

**期望：** runbooks/redis-timeout.md

**检索：** runbooks/redis-timeout.md, runbooks/redis-timeout.md, postmortems/2024-01-redis-cache-flush.md

### ✅ [HIT] q02 (scored)（rank=1）

**问题：** Redis 连接数打满了怎么办？

**期望：** runbooks/redis-timeout.md

**检索：** runbooks/redis-timeout.md, postmortems/2024-01-redis-cache-flush.md, postmortems/2024-01-redis-cache-flush.md

### ✅ [HIT] q03 (scored)（rank=2）

**问题：** Redis 慢查询怎么查？

**期望：** runbooks/redis-timeout.md

**检索：** postmortems/2024-01-redis-cache-flush.md, runbooks/redis-timeout.md, runbooks/redis-timeout.md

### ✅ [HIT] q04 (scored)（rank=1）

**问题：** Pod OOMKilled 怎么排查？

**期望：** runbooks/pod-oom.md

**检索：** runbooks/pod-oom.md, postmortems/2024-06-pod-oom-loop.md, runbooks/pod-oom.md

### ✅ [HIT] q05 (scored)（rank=1）

**问题：** Pod 内存泄漏怎么定位？

**期望：** runbooks/pod-oom.md

**检索：** runbooks/pod-oom.md, postmortems/2024-06-pod-oom-loop.md, runbooks/redis-timeout.md

### ✅ [HIT] q06 (scored)（rank=1）

**问题：** 502 Bad Gateway 怎么定位？

**期望：** runbooks/502-error.md

**检索：** runbooks/502-error.md, runbooks/502-error.md, postmortems/2024-03-payment-502.md

### ✅ [HIT] q07 (scored)（rank=1）

**问题：** Nginx upstream 连接失败是什么原因？

**期望：** runbooks/502-error.md

**检索：** runbooks/502-error.md, runbooks/502-error.md, postmortems/2024-03-payment-502.md

### ✅ [HIT] q08 (scored)（rank=1）

**问题：** 服务回滚怎么操作？

**期望：** runbooks/rollback.md

**检索：** runbooks/rollback.md, runbooks/rollback.md, runbooks/rollback.md

### ✅ [HIT] q09 (scored)（rank=1）

**问题：** K8s deployment 回滚到指定版本用什么命令？

**期望：** runbooks/rollback.md

**检索：** runbooks/rollback.md, architecture/service-topology.md, runbooks/rollback.md

### ✅ [HIT] q10 (scored)（rank=1）

**问题：** 磁盘空间满了怎么排查？

**期望：** runbooks/disk-full.md

**检索：** runbooks/disk-full.md, architecture/oncall-process.md, runbooks/pod-oom.md

### ✅ [HIT] q11 (scored)（rank=1）

**问题：** ShipLog 有哪些服务？服务拓扑是什么？

**期望：** architecture/service-topology.md

**检索：** architecture/service-topology.md, postmortems/2024-06-pod-oom-loop.md, architecture/service-topology.md

### ✅ [HIT] q12 (scored)（rank=1）

**问题：** On-call 告警分级有哪些？P0 是什么意思？

**期望：** architecture/oncall-process.md

**检索：** architecture/oncall-process.md, architecture/service-topology.md, architecture/service-topology.md

### ✅ [HIT] q13 (scored)（rank=1）

**问题：** On-call 事故响应流程是什么？

**期望：** architecture/oncall-process.md

**检索：** architecture/oncall-process.md, architecture/service-topology.md, runbooks/rollback.md

### ✅ [HIT] q14 (scored)（rank=1）

**问题：** Redis 缓存被 FLUSHALL 的事故是怎么发生的？

**期望：** postmortems/2024-01-redis-cache-flush.md

**检索：** postmortems/2024-01-redis-cache-flush.md, runbooks/redis-timeout.md, postmortems/2024-01-redis-cache-flush.md

### ✅ [HIT] q15 (scored)（rank=1）

**问题：** 缓存清空导致数据库雪崩的根因是什么？

**期望：** postmortems/2024-01-redis-cache-flush.md

**检索：** postmortems/2024-01-redis-cache-flush.md, runbooks/redis-timeout.md, postmortems/2024-01-redis-cache-flush.md

### ✅ [HIT] q16 (scored)（rank=1）

**问题：** 支付服务 502 事故的根因是什么？

**期望：** postmortems/2024-03-payment-502.md

**检索：** postmortems/2024-03-payment-502.md, runbooks/502-error.md, postmortems/2024-03-payment-502.md

### ✅ [HIT] q17 (scored)（rank=1）

**问题：** 搜索服务 Pod OOM 循环是什么原因？

**期望：** postmortems/2024-06-pod-oom-loop.md

**检索：** postmortems/2024-06-pod-oom-loop.md, postmortems/2024-06-pod-oom-loop.md, runbooks/pod-oom.md

### ✅ [HIT] q18 (scored)（rank=1）

**问题：** 哪些操作需要 SRE Lead 审批？

**期望：** architecture/oncall-process.md

**检索：** architecture/oncall-process.md, architecture/service-topology.md, runbooks/502-error.md

### ✅ [HIT] q19 (scored)（rank=1）

**问题：** 如何在生产环境执行 FLUSHALL 清空 Redis 缓存来释放内存？

**期望：** runbooks/redis-timeout.md, architecture/oncall-process.md

**检索：** runbooks/redis-timeout.md, architecture/oncall-process.md, postmortems/2024-01-redis-cache-flush.md

### ✅ [HIT] q20 (scored)（rank=1）

**问题：** 怎么直接 DROP TABLE 删掉生产数据库的订单表？

**期望：** architecture/oncall-process.md

**检索：** architecture/oncall-process.md, runbooks/rollback.md, runbooks/redis-timeout.md

### ✅ [HIT] q21 (scored)（rank=1）

**问题：** Redis 超时和 Pod OOM 有什么共同排查思路？

**期望：** runbooks/redis-timeout.md, runbooks/pod-oom.md

**检索：** runbooks/redis-timeout.md, runbooks/redis-timeout.md, postmortems/2024-06-pod-oom-loop.md

### ✅ [HIT] q22 (scored)（rank=1）

**问题：** 502 和回滚操作有什么关联？上线导致 502 后怎么处理？

**期望：** runbooks/502-error.md, runbooks/rollback.md

**检索：** runbooks/502-error.md, runbooks/502-error.md, postmortems/2024-03-payment-502.md

### ❌ [MISS] q23 (abstain)

**问题：** 线上服务挂了怎么办？

**期望：** (none)

**检索：** postmortems/2024-06-pod-oom-loop.md, runbooks/502-error.md, postmortems/2024-06-pod-oom-loop.md

### ✅ [HIT] q24 (scored)（rank=1）

**问题：** redis-cli slowlog get 10 这个命令是干什么的？

**期望：** runbooks/redis-timeout.md

**检索：** runbooks/redis-timeout.md, runbooks/redis-timeout.md, runbooks/redis-timeout.md

### ✅ [HIT] q25 (scored)（rank=1）

**问题：** kubectl rollout undo deployment 回滚到指定版本怎么写？

**期望：** runbooks/rollback.md

**检索：** runbooks/rollback.md, runbooks/rollback.md, runbooks/pod-oom.md

### ✅ [HIT] q26 (scored)（rank=1）

**问题：** 生产环境能不能直接 FLUSHALL 清空 Redis 缓存？

**期望：** runbooks/redis-timeout.md

**检索：** runbooks/redis-timeout.md, postmortems/2024-01-redis-cache-flush.md, postmortems/2024-01-redis-cache-flush.md

### ❌ [MISS] q27 (abstain)

**问题：** 怎么用 kubectl 查看节点资源使用情况？

**期望：** (none)

**检索：** runbooks/pod-oom.md, runbooks/disk-full.md, runbooks/pod-oom.md

### ✅ [HIT] q28 (scored)（rank=1）

**问题：** Pod Exit Code 137 是什么意思？

**期望：** runbooks/pod-oom.md

**检索：** runbooks/pod-oom.md, postmortems/2024-06-pod-oom-loop.md, runbooks/502-error.md

### ✅ [HIT] q29 (scored)（rank=1）

**问题：** 支付服务 502 事故里 readiness probe 有什么问题？

**期望：** postmortems/2024-03-payment-502.md

**检索：** postmortems/2024-03-payment-502.md, postmortems/2024-03-payment-502.md, runbooks/502-error.md

### ✅ [HIT] q30 (scored)（rank=1）

**问题：** 搜索服务 OOM 循环事故的改进措施有哪些？

**期望：** postmortems/2024-06-pod-oom-loop.md

**检索：** postmortems/2024-06-pod-oom-loop.md, postmortems/2024-06-pod-oom-loop.md, postmortems/2024-06-pod-oom-loop.md

### ❌ [MISS] q31 (abstain)

**问题：** 怎么配置 Redis AOF 持久化？

**期望：** (none)

**检索：** runbooks/redis-timeout.md, postmortems/2024-01-redis-cache-flush.md, runbooks/redis-timeout.md

### ❌ [MISS] q32 (abstain)

**问题：** MySQL 主从切换怎么做？

**期望：** (none)

**检索：** runbooks/rollback.md, postmortems/2024-01-redis-cache-flush.md, architecture/service-topology.md

### ❌ [MISS] q33 (abstain)

**问题：** Consul 服务注册失败怎么排查？

**期望：** (none)

**检索：** architecture/service-topology.md, architecture/oncall-process.md, runbooks/redis-timeout.md

### ✅ [HIT] q34 (scored)（rank=1）

**问题：** ShipLog 的数据层用了哪些组件？版本分别是多少？

**期望：** architecture/service-topology.md

**检索：** architecture/service-topology.md, architecture/service-topology.md, architecture/service-topology.md

### ✅ [HIT] q35 (scored)（rank=1）

**问题：** On-call 交接班需要交接什么内容？

**期望：** architecture/oncall-process.md

**检索：** architecture/oncall-process.md, architecture/service-topology.md, architecture/service-topology.md

### ✅ [HIT] q36 (scored)（rank=1）

**问题：** Redis 连接泄漏的止血方法是什么？

**期望：** runbooks/redis-timeout.md

**检索：** runbooks/redis-timeout.md, runbooks/redis-timeout.md, postmortems/2024-01-redis-cache-flush.md

### ✅ [HIT] q37 (scored)（rank=1）

**问题：** 支付服务 502 事故影响了多少笔支付超时？

**期望：** postmortems/2024-03-payment-502.md

**检索：** postmortems/2024-03-payment-502.md, runbooks/502-error.md, postmortems/2024-03-payment-502.md

### ✅ [HIT] q38 (scored)（rank=1）

**问题：** 搜索服务 OOM 事故发生在什么时间？

**期望：** postmortems/2024-06-pod-oom-loop.md

**检索：** postmortems/2024-06-pod-oom-loop.md, postmortems/2024-06-pod-oom-loop.md, runbooks/pod-oom.md

### ❌ [MISS] q39 (abstain)

**问题：** 怎么配置 Prometheus 告警规则？

**期望：** runbooks/prometheus-alerts.md

**检索：** architecture/service-topology.md, postmortems/2024-03-payment-502.md, architecture/oncall-process.md

### ❌ [MISS] q40 (abstain)

**问题：** K8s NetworkPolicy 怎么配置？

**期望：** runbooks/network-policy.md

**检索：** architecture/service-topology.md, runbooks/disk-full.md, runbooks/disk-full.md

### ❌ [MISS] q41 (abstain)

**问题：** 怎么给 Nginx 配置 SSL 证书？

**期望：** runbooks/nginx-ssl.md

**检索：** runbooks/502-error.md, runbooks/502-error.md, postmortems/2024-03-payment-502.md

### ❌ [MISS] q42 (abstain)

**问题：** Docker 镜像构建有哪些最佳实践？

**期望：** runbooks/docker-build.md

**检索：** runbooks/disk-full.md, runbooks/disk-full.md, runbooks/disk-full.md

### ❌ [MISS] q43 (abstain)

**问题：** GitLab CI/CD 流水线怎么配置？

**期望：** runbooks/gitlab-ci.md

**检索：** runbooks/disk-full.md, runbooks/502-error.md, runbooks/disk-full.md

## abstain 集

- 共 5 题，空检索 0 题
- 检索层仅参考；生成层拒答看 CRAG / prompt
