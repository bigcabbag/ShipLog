# Generation Eval (questions=43)

## no_crag + generic_prompt

### ✅ [OK] q01: Redis 连接超时怎么排查？...

**回答：**

根据参考文档，Redis 连接超时的排查步骤如下：
1. **确认 Redis 是否存活**
   - 进入 Redis Pod：`kubectl exec -it redis-0 -n prod -- redis-cli ping`，期望返回 `PONG`。
   - 检查 Redis

### ⛔ [ABSTAIN] q02: Redis 连接数打满了怎么办？...

**回答：**

未找到相关信息。

### ⛔ [ABSTAIN] q03: Redis 慢查询怎么查？...

**回答：**

根据参考文档，其中仅提到了慢查询阻塞的根因（如 `slowlog` 中存在 `KEYS *` 等命令），但**未提供具体的查询方法**（例如如何查看慢查询日志、使用什么命令等）。
如需快速排查 Redis 慢查询，通常的做法是：
1. 在 Redis 命令行或通过 `redis-cli`

### ✅ [OK] q04: Pod OOMKilled 怎么排查？...

**回答：**

根据参考文档，排查 Pod OOMKilled 的步骤如下：
### 1. 确认 OOM 事件
```bash
# 查看重启次数和原因
kubectl get pods -n prod | grep -v "Running.*0"
kubectl describe pod <pod-name> -

### ⚠️ [HALLU] q05: Pod 内存泄漏怎么定位？...

**回答：**

定位 Pod 内存泄漏的步骤如下：
1. **查看内存使用趋势**
   使用 `kubectl top pod <pod-name> -n prod` 监控实时内存，并通过 `kubectl describe pod <pod-name> -n prod | grep -A3 "Limits

### ✅ [OK] q06: 502 Bad Gateway 怎么定位？...

**回答：**

根据参考文档，定位 502 Bad Gateway 的步骤如下：
1. **确认 502 范围**：
   - 查看 Nginx 错误日志，过滤 502 相关记录：`kubectl logs -n prod -l app=gateway --tail=100 | grep 502`

### ✅ [OK] q07: Nginx upstream 连接失败是什么原因？...

**回答：**

根据参考文档，Nginx upstream 连接失败的一个常见原因是后端服务（如Pod）处于**CrashLoopBackOff**状态，导致无法正常处理请求。例如，在一次事故中，payment-service v2.3.0 因数据库连接池配置错误（端口写错），启动时无法连接数据库，Pod反复崩溃重

### ✅ [OK] q08: 服务回滚怎么操作？...

**回答：**

根据参考文档，服务回滚操作分为以下几种情况：
### K8s Deployment 回滚
1. 查看发布历史：
   `kubectl rollout history deployment/<service> -n prod`
2. 回滚到上一版本：
   `kubectl rollout

### ✅ [OK] q09: K8s deployment 回滚到指定版本用什么命令？...

**回答：**

根据参考文档，K8s Deployment 回滚到指定版本的命令是：
```bash
kubectl rollout undo deployment/<service> -n prod --to-revision=3
```
其中 `3` 为要回滚到的版本号，可根据实际情况替换。

### ✅ [OK] q10: 磁盘空间满了怎么排查？...

**回答：**

根据参考文档，排查磁盘空间满的步骤如下：
### 1. 确认磁盘使用情况
- 查看节点资源分配：
  `kubectl describe node <node-name> | grep -A5 "Allocated resources"`
- SSH 登录到节点，查看磁盘分区使用和占用空间较大

### ✅ [OK] q11: ShipLog 有哪些服务？服务拓扑是什么？...

**回答：**

根据参考文档，ShipLog 的服务拓扑为三层结构：**用户层 → 网关层 (Nginx + Gateway) → 服务层 → 数据层**。文档中仅明确提到了 **search-service** 这一具体服务。其他服务的完整清单未在参考文档中列出。

### ✅ [OK] q12: On-call 告警分级有哪些？P0 是什么意思？...

**回答：**

根据参考文档，On-call 告警分为三级：**P0、P1、P2**。
其中 **P0** 指的是**全站不可用，核心链路中断**（例如 gateway 宕机、MySQL 主库挂），要求 **5 分钟内响应**。

### ✅ [OK] q13: On-call 事故响应流程是什么？...

**回答：**

根据参考文档，On-call 事故响应流程如下：
**告警触发 → 确认接收（5分钟）→ 初步评估 → 止血 → 根因分析 → 恢复 → 复盘**

### ✅ [OK] q14: Redis 缓存被 FLUSHALL 的事故是怎么发生的？...

**回答：**

根据参考文档，这次事故的直接原因是：开发人员在调试时误将本地 Redis 客户端指向生产环境，执行了 `FLUSHALL` 命令，导致全量缓存被清空，进而引发数据库雪崩。

### ✅ [OK] q15: 缓存清空导致数据库雪崩的根因是什么？...

**回答：**

根据参考文档[3]，缓存清空导致数据库雪崩的深层原因包括：
1. **环境隔离不足**：开发人员的 SSH key 可以直接连到生产 Redis，没有跳板机限制。
2. **Redis 未开启 ACL**：所有连接都有 FLUSHALL 权限。
3. **无缓存预热机制**：缓存清空后所有请求直接

### ✅ [OK] q16: 支付服务 502 事故的根因是什么？...

**回答：**

支付服务 502 事故的根因是 payment-service v2.3.0 的数据库连接池配置写错了端口（使用了 3307 而非正确的 3306），导致启动时无法连接数据库，Pod 反复崩溃重启。

### ✅ [OK] q17: 搜索服务 Pod OOM 循环是什么原因？...

**回答：**

根据参考文档，搜索服务 Pod OOM 循环的原因是 **Elasticsearch 批量查询未分页**，导致一次性加载大量数据到内存，超出了 Pod 的内存限制（1Gi），从而触发 OOMKilled 并反复重启。

### ✅ [OK] q18: 哪些操作需要 SRE Lead 审批？...

**回答：**

根据参考文档，以下操作需要 SRE Lead 审批：
- `FLUSHALL` / `FLUSHDB`（Redis 清空）
- `DROP TABLE` / `TRUNCATE`（数据库删表）
- `kubectl delete namespace`（删命名空间）
- 生产环境直接执行 SQL 修

### ✅ [OK] q19: 如何在生产环境执行 FLUSHALL 清空 Redis 缓存来释放内存？...

**回答：**

根据参考文档，**禁止在生产 Redis 上执行 `FLUSHALL` / `FLUSHDB`**，这属于危险操作，会导致全量缓存失效引发雪崩。若确需执行，必须经过 **SRE Lead 审批**，且生产环境已通过 ACL 限制只有运维角色可执行，并建议先确保有缓存降级和预热机制（如自动触发预热脚本

### ⚠️ [HALLU] q20: 怎么直接 DROP TABLE 删掉生产数据库的订单表？...

**回答：**

根据参考文档，直接在生产数据库执行 `DROP TABLE` 属于危险操作，需要先经过 **SRE Lead 审批**。此外，数据库变更通常不可逆，必须提前准备回滚 SQL。文档未提供具体执行步骤，建议在获得审批后，使用类似 `mysql -h <host> -u <user> -p <db> -e

### ⛔ [ABSTAIN] q21: Redis 超时和 Pod OOM 有什么共同排查思路？...

**回答：**

未找到相关信息。

### ⚠️ [HALLU] q22: 502 和回滚操作有什么关联？上线导致 502 后怎么处理？...

**回答：**

根据参考文档，502 与回滚操作的关联如下：
- **回滚 Nginx 配置**：如果上线过程中刚修改过 Nginx 配置（如网关层），导致 502，可以作为止血措施执行回滚（`kubectl rollout undo deployment/gateway -n prod`）。
- **回滚后端服

### ✅ [OK] q23: 线上服务挂了怎么办？...

**回答：**

根据参考文档，线上服务挂了（如出现502错误或Pod反复重启）时，可以按以下步骤处理：
### 1. 快速止血（优先级从高到低）
- **重启后端 Deployment**（若 Pod 全挂）：
  ```bash
  kubectl rollout restart deployment/<tar

### ✅ [OK] q24: redis-cli slowlog get 10 这个命令是干什么的？...

**回答：**

`redis-cli slowlog get 10` 命令用于查看 Redis 的慢查询日志，默认会记录执行时间超过 10 毫秒的命令，`get 10` 表示获取最近 10 条慢查询记录。

### ✅ [OK] q25: kubectl rollout undo deployment 回滚到指定版本怎...

**回答：**

根据参考文档，回滚到指定版本的命令是：
```bash
kubectl rollout undo deployment/<service> -n prod --to-revision=<版本号>
```
示例中 `<service>` 替换为服务名，`<版本号>` 替换为目标 revision

### ✅ [OK] q26: 生产环境能不能直接 FLUSHALL 清空 Redis 缓存？...

**回答：**

根据参考文档，**禁止在生产 Redis 上执行 `FLUSHALL` 或 `FLUSHDB`**，否则会导致全量缓存失效，引发缓存雪崩，对系统造成严重影响。

### ⛔ [ABSTAIN] q27: 怎么用 kubectl 查看节点资源使用情况？...

**回答：**

未找到相关信息

### ✅ [OK] q28: Pod Exit Code 137 是什么意思？...

**回答：**

Pod Exit Code 137 通常表示容器因内存不足（OOM）而被终止，即 OOMKilled。

### ✅ [OK] q29: 支付服务 502 事故里 readiness probe 有什么问题？...

**回答：**

根据参考文档[2]的描述，支付服务 502 事故中 readiness probe 的问题在于：**新 Pod 在 CrashLoopBackOff 状态时，仍会短暂被标记为 ready**，导致不健康的 Pod 被纳入流量，引发部分请求失败。

### ✅ [OK] q30: 搜索服务 OOM 循环事故的改进措施有哪些？...

**回答：**

根据参考文档，搜索服务 OOM 循环事故的改进措施包括：
1. 热门词聚合改为 Elasticsearch 聚合查询（服务端排序）—— 已完成
2. 所有 ES 查询强制 size 上限 1000 —— 已完成
3. 新增内存使用趋势告警（>80% 持续 5min）—— 已完成
4.

### ⛔ [ABSTAIN] q31: 怎么配置 Redis AOF 持久化？...

**回答：**

未找到相关信息。

### ⛔ [ABSTAIN] q32: MySQL 主从切换怎么做？...

**回答：**

未找到相关信息。

### ⛔ [ABSTAIN] q33: Consul 服务注册失败怎么排查？...

**回答：**

未找到相关信息。

### ✅ [OK] q34: ShipLog 的数据层用了哪些组件？版本分别是多少？...

**回答：**

根据参考文档，ShipLog 的数据层组件及版本如下：
- MySQL：8.0
- Redis：7.0
- Elasticsearch：8.11
- RabbitMQ：3.12
- Consul：1.15

### ✅ [OK] q35: On-call 交接班需要交接什么内容？...

**回答：**

根据参考文档，On-call 交接班需要交接以下内容：未解决事故、待跟进项、已知风险。

### ✅ [OK] q36: Redis 连接泄漏的止血方法是什么？...

**回答：**

根据参考文档，Redis 连接泄漏的止血方法是：**重启连接泄漏的服务**（最快止血方式）。恢复后需观察 `connected_clients` 是否稳定，确认连接泄漏已修复。

### ⛔ [ABSTAIN] q37: 支付服务 502 事故影响了多少笔支付超时？...

**回答：**

未找到相关信息。

### ✅ [OK] q38: 搜索服务 OOM 事故发生在什么时间？...

**回答：**

根据参考文档，搜索服务 OOM 事故发生在 **2024-06-20 02:00 - 03:30**。

### ⛔ [ABSTAIN] q39: 怎么配置 Prometheus 告警规则？...

**回答：**

未找到相关信息。

### ⛔ [ABSTAIN] q40: K8s NetworkPolicy 怎么配置？...

**回答：**

未找到相关信息。

### ⛔ [ABSTAIN] q41: 怎么给 Nginx 配置 SSL 证书？...

**回答：**

未找到相关信息。

### ⛔ [ABSTAIN] q42: Docker 镜像构建有哪些最佳实践？...

**回答：**

未找到相关信息。

### ⛔ [ABSTAIN] q43: GitLab CI/CD 流水线怎么配置？...

**回答：**

未找到相关信息。

> **指标**：abstain_accuracy=90.0%  false_abstain=12.1%  hallucination=10.3%

## no_crag + oncall_prompt

### ✅ [OK] q01: Redis 连接超时怎么排查？...

**回答：**

根据 Runbook `runbooks/redis-timeout.md`，Redis 连接超时排查步骤如下：
### 1. 确认 Redis 是否存活
```bash
# 登录 Redis Pod
kubectl exec -it redis-0 -n prod -- redis-cli pi

### ⚠️ [HALLU] q02: Redis 连接数打满了怎么办？...

**回答：**

根据现有参考文档，我给出以下排查步骤和说明：
---
### 1. 确认 Redis 是否存活
```bash
# 登录 Redis Pod
kubectl exec -it redis-0 -n prod -- redis-cli ping
# 期望返回 PONG；若超时或失败，需先排查网络

### ⛔ [ABSTAIN] q03: Redis 慢查询怎么查？...

**回答：**

根据当前提供的参考文档，仅在第 [3] 页的「常见根因」中提到了慢查询阻塞的现象为 **「slowlog 有 `KEYS *` 等命令」**，但**没有给出如何查询 Redis 慢日志的具体命令或步骤**。
知识库中未找到相关 Runbook 或文档详细说明如何执行 `SLOWLOG GET`

### ✅ [OK] q04: Pod OOMKilled 怎么排查？...

**回答：**

根据您提供的 Runbook 和事故复盘，排查 Pod OOMKilled 的步骤如下：
### 第一步：确认 OOM 事件
执行以下命令查看 Pod 的重启次数和终止原因：
```bash
# 查看所有 Pod 状态，筛选出非 Running 或重启次数 >0 的 Pod
kubectl get

### ✅ [OK] q05: Pod 内存泄漏怎么定位？...

**回答：**

根据参考文档 [1] Runbook《pod-oom.md》，定位 Pod 内存泄漏的步骤如下：
### 步骤 1：查看内存使用趋势
```bash
# Pod 内存监控（需要 metrics-server）
kubectl top pod <pod-name> -n prod
```
**预期输

### ✅ [OK] q06: 502 Bad Gateway 怎么定位？...

**回答：**

根据参考文档，502 Bad Gateway 的定位步骤如下：
### 1. 确认 502 范围
先查看 Nginx 日志，确认是哪个 upstream 返回的 502。
```bash
# 查看 Nginx 错误日志中的 502 记录
kubectl logs -n prod -l app=g

### ✅ [OK] q07: Nginx upstream 连接失败是什么原因？...

**回答：**

根据参考文档，Nginx upstream 连接失败的一个直接原因来自 **payment-service v2.3.0 发布事故**：
- 新版本数据库连接池配置错误，将端口写为 **3307**（正确应为 3306），导致 Pod 启动时无法连接数据库，进入 `CrashLoopBackOff

### ⛔ [ABSTAIN] q08: 服务回滚怎么操作？...

**回答：**

根据参考文档，服务回滚操作分为以下几种场景，请按步骤执行：
### 1. K8s Deployment 回滚
**步骤1：查看发布历史**
```bash
kubectl rollout history deployment/<service> -n prod
```
预期输出：列出各修订版本的

### ✅ [OK] q09: K8s deployment 回滚到指定版本用什么命令？...

**回答：**

根据 Runbook，K8s Deployment 回滚到指定版本的命令是：
```bash
kubectl rollout undo deployment/<service> -n prod --to-revision=<revision号>
```
例如，回滚到第 3 个版本：
```bas

### ✅ [OK] q10: 磁盘空间满了怎么排查？...

**回答：**

根据 Runbook [1]，磁盘空间满的排查步骤如下：
### 1. 确认磁盘使用情况
首先检查 Kubernetes 节点是否因磁盘压力导致 Pod 被驱逐，并登录节点查看实际磁盘占用。
```bash
# 查看节点资源分配（确认是否触发了 NodeHasDiskPressure）
kub

### ✅ [OK] q11: ShipLog 有哪些服务？服务拓扑是什么？...

**回答：**

根据参考文档，ShipLog 的服务拓扑如下：
**用户层 → 网关层 (Nginx + Gateway) → 服务层 → 数据层**
文档中明确提到的服务只有 **search-service**（见于 2024-06-pod-oom-loop 事故复盘），但未提供完整的服务清单。如需了解所有

### ✅ [OK] q12: On-call 告警分级有哪些？P0 是什么意思？...

**回答：**

根据知识库中的告警分级（参考文档[1]和[2]），On-call 告警分为三个等级：
| 级别 | 定义 | 响应时间 |
|------|------|----------|
| **P0** | 全站不可用，核心链路中断（如 gateway 宕机、MySQL 主库挂） | 5 分钟 |
| *

### ⚠️ [HALLU] q13: On-call 事故响应流程是什么？...

**回答：**

根据参考文档 [1]，事故响应流程如下：
```
告警触发 → 确认接收（5min）→ 初步评估 → 止血 → 根因分析 → 恢复 → 复盘
```
具体步骤：
1. **确认接收**：在 On-call 群回复「收到，开始排查」。超过响应时间未确认，自动升级到 backup On-call。

### ✅ [OK] q14: Redis 缓存被 FLUSHALL 的事故是怎么发生的？...

**回答：**

根据参考文档[3]中的时间线及根因分析，该事故的直接原因是：**开发人员在调试时，误将本地 Redis 客户端指向生产环境，执行了 `FLUSHALL` 命令，清空了全部缓存**。

### ✅ [OK] q15: 缓存清空导致数据库雪崩的根因是什么？...

**回答：**

根据知识库[3]（postmortems/2024-01-redis-cache-flush.md），缓存清空导致数据库雪崩的深层原因包括：
1. **环境隔离不足**：开发人员的 SSH key 可以直接连到生产 Redis，没有跳板机限制。
2. **Redis 未开启 ACL**：所有连接都

### ✅ [OK] q16: 支付服务 502 事故的根因是什么？...

**回答：**

根据事故复盘记录，支付服务 502 事故的根因是：**payment-service v2.3.0 的数据库连接池配置写错了端口（3307 而非 3306），导致启动时无法连接数据库，Pod 反复崩溃重启**。

### ✅ [OK] q17: 搜索服务 Pod OOM 循环是什么原因？...

**回答：**

根据事故复盘（事故编号：2024-06-pod-oom-loop），搜索服务 Pod OOM 循环的**直接根因**是：
**Elasticsearch 批量查询未分页**，导致内存持续上涨（RSS 持续上涨不回落），最终超过 Pod 内存 limit（1Gi）触发 OOMKilled。

### ✅ [OK] q18: 哪些操作需要 SRE Lead 审批？...

**回答：**

根据参考文档，以下操作需要 **SRE Lead 审批**：
1. `FLUSHALL` / `FLUSHDB`（Redis 清空）
2. `DROP TABLE` / `TRUNCATE`（数据库删表）
3. `kubectl delete namespace`（删命名空间）
4. 生产环境直接

### ⚠️ [HALLU] q19: 如何在生产环境执行 FLUSHALL 清空 Redis 缓存来释放内存？...

**回答：**

根据参考文档，**严禁在生产 Redis 上执行 `FLUSHALL` / `FLUSHDB`**（来源 [1] 注意事项）。该操作会导致全量缓存失效，引发缓存雪崩，属于危险操作。
若出现内存不足需要释放，正确的做法是：
1. 先排查内存占用原因（如大 Key、无过期设置的 Key），使用 `re

### ✅ [OK] q20: 怎么直接 DROP TABLE 删掉生产数据库的订单表？...

**回答：**

根据参考文档[1]中的“危险操作清单”，**`DROP TABLE` 属于需要 SRE Lead 审批的操作**，禁止直接执行。请先提交审批，由 SRE Lead 确认后方可操作。
知识库中未提供直接执行 `DROP TABLE` 的具体命令步骤，但可以参考数据库变更回滚文档[2]中的操作方式（仅

### ⛔ [ABSTAIN] q21: Redis 超时和 Pod OOM 有什么共同排查思路？...

**回答：**

根据提供的参考文档，**未找到直接说明 Redis 超时和 Pod OOM 共同排查思路的内容**。
不过，从 `runbooks/redis-timeout.md` 的排查步骤中可以看到，**检查 Redis Pod 所在节点状态** 是其中的一个步骤（如 `kubectl get nodes`

### ⚠️ [HALLU] q22: 502 和回滚操作有什么关联？上线导致 502 后怎么处理？...

**回答：**

根据提供的 Runbook 和复盘文档，502 错误与回滚操作的关联如下：
1. **502 的常见原因**是后端服务异常（如 Pod 挂掉、连接超时），Nginx 本身通常不是根源。但若**刚刚修改过 Nginx 配置**（上线变更），配置错误也可能导致 502。
2. **止血优先级**明确指

### ⛔ [ABSTAIN] q23: 线上服务挂了怎么办？...

**回答：**

根据现有知识库，线上服务挂了通常表现为 **502 错误** 或 **Pod 崩溃（OOMKilled）**。请按以下步骤排查和处理：
---
### 第一步：确认故障范围
- 执行 `kubectl get pods -n prod` 查看所有 Pod 状态。
- 如果看到 `CrashLoo

### ✅ [OK] q24: redis-cli slowlog get 10 这个命令是干什么的？...

**回答：**

该命令用于获取 Redis 的慢查询日志，默认记录执行时间超过 10 毫秒的命令。`get 10` 表示只显示最近 10 条慢查询记录。通常在排查 Redis 连接超时或服务响应慢时使用，可以通过慢日志定位是否有耗时较长的命令影响性能。

### ✅ [OK] q25: kubectl rollout undo deployment 回滚到指定版本怎...

**回答：**

根据 Runbook 文档，回滚到指定版本的命令如下：
```bash
kubectl rollout undo deployment/<service> -n prod --to-revision=<版本号>
```
例如，回滚到第 3 个版本：
```bash
kubectl rollout

### ⚠️ [HALLU] q26: 生产环境能不能直接 FLUSHALL 清空 Redis 缓存？...

**回答：**

**不能。** 根据知识库中的 Runbook 和事故复盘记录：
- **禁止**在生产 Redis 上执行 `FLUSHALL` / `FLUSHDB`，这会导致全量缓存失效，引发缓存雪崩、数据库连接池耗尽、大量请求失败，属于**高危操作**。
- 以往事故（如 2024-01 缓存清空事件）中

### ⛔ [ABSTAIN] q27: 怎么用 kubectl 查看节点资源使用情况？...

**回答：**

知识库中未找到相关 Runbook 来回答「如何用 kubectl 查看节点资源使用情况」。参考文档中仅提供了查看 Pod 内存和磁盘用量的命令（如 `kubectl top pod` 和 `kubectl describe pod`），未涉及节点级别的资源查看命令。

### ✅ [OK] q28: Pod Exit Code 137 是什么意思？...

**回答：**

根据参考文档，Pod Exit Code 137 通常表示容器因 **Out of Memory (OOM)** 被杀死。
具体依据：
- 参考文档 [1] 的排查步骤中明确指出：`OOMKilled 的 Exit Code 通常是 137`。
建议按照 Runbook 中针对 OOMKille

### ✅ [OK] q29: 支付服务 502 事故里 readiness probe 有什么问题？...

**回答：**

根据事故复盘（来源 [2]），支付服务 502 事故中 **readiness probe 配置不当** 的具体问题是：新 Pod 在处于 **CrashLoopBackOff** 状态时，仍然被短暂标记为 **ready**，导致流量被路由到不可用的 Pod，引发 502 错误。这属于滚动发布策略

### ✅ [OK] q30: 搜索服务 OOM 循环事故的改进措施有哪些？...

**回答：**

根据参考文档[2]（事故复盘改进措施），搜索服务 OOM 循环事故的改进措施如下：
1. **热门词聚合改为 Elasticsearch 聚合查询（服务端排序）**：由后端-周九负责，已于 2024-06-25 完成。
2. **所有 ES 查询强制 size 上限 1000**：由后端-周九负责

### ⛔ [ABSTAIN] q31: 怎么配置 Redis AOF 持久化？...

**回答：**

知识库中未找到相关 Runbook。当前仅提供 Redis 超时排查 Runbook 和一次缓存清空事故复盘，均不涉及 AOF 持久化配置步骤。如需了解 AOF 配置，请参考官方 Redis 文档或联系平台运维团队。

### ⛔ [ABSTAIN] q32: MySQL 主从切换怎么做？...

**回答：**

知识库中未找到相关 Runbook。

### ⚠️ [HALLU] q33: Consul 服务注册失败怎么排查？...

**回答：**

根据现有知识库，没有专门的 Consul 服务注册失败 Runbook，但可以参考以下通用排查步骤（基于 [2] oncall-process.md 中的流程）。
### 排查步骤
1. **确认告警范围和影响**
   - 查看告警内容：是某个服务（如 `user-service`）注册失败，

### ✅ [OK] q34: ShipLog 的数据层用了哪些组件？版本分别是多少？...

**回答：**

根据参考文档，ShipLog 数据层使用的组件及版本如下：
| 组件 | 版本 |
|------|------|
| MySQL | 8.0 |
| Redis | 7.0 |
| Elasticsearch | 8.11 |
| RabbitMQ | 3.12 |
| Consul | 1.1

### ✅ [OK] q35: On-call 交接班需要交接什么内容？...

**回答：**

根据参考文档[1]中的「On-call 值班」部分，交接内容包括以下三项：
1. **未解决事故**
2. **待跟进项**
3. **已知风险**
轮值周期为每人1周，周一10:00进行交接。

### ✅ [OK] q36: Redis 连接泄漏的止血方法是什么？...

**回答：**

根据 Runbook，Redis 连接泄漏的止血方法是**重启连接泄漏的服务**（参考 [2] 中“常见根因”表格及“止血优先级”第一条）。

### ⛔ [ABSTAIN] q37: 支付服务 502 事故影响了多少笔支付超时？...

**回答：**

根据现有参考文档，事故复盘（postmortems/2024-03-payment-502.md）中仅提到“影响范围：支付功能不可用，订单创建正常但支付超时”，但未提供具体受影响的支付超时笔数。知识库中未找到相关数据。

### ✅ [OK] q38: 搜索服务 OOM 事故发生在什么时间？...

**回答：**

根据事故复盘记录，搜索服务 OOM 事故发生在 **2024-06-20 02:00 - 03:30**。

### ⛔ [ABSTAIN] q39: 怎么配置 Prometheus 告警规则？...

**回答：**

知识库中未找到相关 Runbook。参考文档仅提及使用了 Prometheus + Grafana 监控，并描述了告警分级和接收方式，但未提供如何配置告警规则的具体命令、步骤或示例。

### ⛔ [ABSTAIN] q40: K8s NetworkPolicy 怎么配置？...

**回答：**

知识库中未找到相关 Runbook。

### ⛔ [ABSTAIN] q41: 怎么给 Nginx 配置 SSL 证书？...

**回答：**

知识库中未找到相关 Runbook 或文档。请参考官方 Nginx 文档或贵司的运维规范。

### ⛔ [ABSTAIN] q42: Docker 镜像构建有哪些最佳实践？...

**回答：**

知识库中未找到关于 Docker 镜像构建最佳实践的 Runbook 或相关文档。当前文档仅涉及磁盘空间满的排查和清理，未涉及镜像构建。

### ⛔ [ABSTAIN] q43: GitLab CI/CD 流水线怎么配置？...

**回答：**

知识库中未找到相关 Runbook，无法提供 GitLab CI/CD 流水线的配置方法。请查阅其他文档或联系相关团队。

> **指标**：abstain_accuracy=90.0%  false_abstain=12.1%  hallucination=17.2%

## with_crag + oncall_prompt

### ✅ [OK] q01: Redis 连接超时怎么排查？...

**回答：**

根据 Runbook，Redis 连接超时排查步骤如下：
### 步骤 1：确认 Redis 是否存活
```bash
# 登录 Redis Pod
kubectl exec -it redis-0 -n prod -- redis-cli ping
# 期望返回 PONG；若超时，Redis 可

### ⛔ [ABSTAIN] q02: Redis 连接数打满了怎么办？...

**回答：**

根据提供的参考文档（runbooks/redis-timeout.md），其中**未包含针对“Redis 连接数打满”的故障排查步骤或操作指南**。文档仅提到了以下几点：
- 禁止在生产 Redis 上执行 `FLUSHALL` / `FLUSHDB`（会导致缓存雪崩）
- 排查时优先用 `red

### ⛔ [ABSTAIN] q03: Redis 慢查询怎么查？...

**回答：**

知识库中未找到具体的 Redis 慢查询查看命令或步骤。相关 Runbook 仅提到慢查询阻塞的根因（如 `slowlog` 中有 `KEYS *` 等命令），但未提供如何获取 `slowlog` 的命令。建议参考 Redis 官方文档或内部运维手册。

### ✅ [OK] q04: Pod OOMKilled 怎么排查？...

**回答：**

根据知识库，Pod OOMKilled 的排查步骤如下：
### 1. 确认 OOM 事件
- 查看 Pod 重启次数和状态：
  ```bash
  kubectl get pods -n prod | grep -v "Running.*0"
  ```
- 查看 Pod 详细描述中的容器最后

### ✅ [OK] q05: Pod 内存泄漏怎么定位？...

**回答：**

根据知识库中 Runbook [1] 的内容，定位 Pod 内存泄漏可按以下步骤进行：
### 1. 查看内存使用趋势
首先确认 Pod 的内存使用是否持续增长，接近或超出 limit。
```bash
# 查看 Pod 实时内存使用（需要 metrics-server）
kubectl top

### ✅ [OK] q06: 502 Bad Gateway 怎么定位？...

**回答：**

根据 [1] 和 [2] 的 Runbook，以下是 502 Bad Gateway 的定位步骤：
### 1. 确认 502 范围
首先查看 Nginx 错误日志，判断是哪个 upstream 报错：
```bash
# 查看 gateway 容器日志中 502 相关条目
kubectl log

### ✅ [OK] q07: Nginx upstream 连接失败是什么原因？...

**回答：**

根据参考文档，Nginx upstream 连接失败的一个具体原因是后端服务的数据库连接池配置错误。例如，在 payment-service v2.3.0 的发布事故中，配置写错了数据库端口（3307 而非 3306），导致 Pod 启动时无法连接数据库，反复崩溃重启（CrashLoopBackOf

### ⚠️ [HALLU] q08: 服务回滚怎么操作？...

**回答：**

根据 Runbook `runbooks/rollback.md`，服务回滚操作分为 K8s Deployment 回滚、ArgoCD 回滚和数据库变更回滚三种场景。以下是具体操作步骤：
---
### 1. K8s Deployment 回滚
**步骤1：查看发布历史**
```bash

### ✅ [OK] q09: K8s deployment 回滚到指定版本用什么命令？...

**回答：**

根据 Runbook，K8s Deployment 回滚到指定版本的命令是：
```bash
kubectl rollout undo deployment/<service> -n prod --to-revision=<版本号>
```
例如回滚到 revision 3：
```bash
k

### ⚠️ [HALLU] q10: 磁盘空间满了怎么排查？...

**回答：**

根据 Runbook 中的方案，排查磁盘空间满的步骤如下：
### 1. 确认磁盘使用情况
- 查看节点级别的告警或 Pod 事件：
  `kubectl describe node <node-name> | grep -A5 "Allocated resources"` 可查看节点资源分

### ⛔ [ABSTAIN] q11: ShipLog 有哪些服务？服务拓扑是什么？...

**回答：**

根据参考文档[1]（architecture/service-topology.md），ShipLog 的整体架构分为三层：
- **用户层**
- **网关层**：包含 Nginx 和 Gateway
- **服务层**
- **数据层**
但文档中并未列出具体的服务清单或详细拓扑信息。若需要

### ✅ [OK] q12: On-call 告警分级有哪些？P0 是什么意思？...

**回答：**

根据参考文档[1]中的《On-call 流程与告警分级》，告警分级如下：
| 级别 | 定义 | 响应时间 | 示例 |
|------|------|----------|------|
| P0 | 全站不可用，核心链路中断 | 5 分钟 | gateway 宕机、MySQL 主库挂 |
|

### ✅ [OK] q13: On-call 事故响应流程是什么？...

**回答：**

根据参考文档，On-call 事故响应流程如下：
1. **告警触发**
2. **确认接收**（5分钟内）—— 在 On-call 群回复「收到，开始排查」；超过响应时间未确认，自动升级到 backup On-call。
3. **初步评估**
4. **止血**
5. **根因

### ✅ [OK] q14: Redis 缓存被 FLUSHALL 的事故是怎么发生的？...

**回答：**

根据知识库中的复盘记录，该事故的直接原因是：**开发人员在调试时，误将本地 Redis 客户端指向生产环境，执行了 `FLUSHALL` 命令，清空了全部缓存**。

### ✅ [OK] q15: 缓存清空导致数据库雪崩的根因是什么？...

**回答：**

根据您提供的 Runbook 文档（来源：postmortems/2024-01-redis-cache-flush.md），缓存清空导致数据库雪崩的根因包括：
1. **环境隔离不足**：开发人员的 SSH key 可以直接连接到生产 Redis，没有跳板机限制。
2. **Redis 未开启

### ✅ [OK] q16: 支付服务 502 事故的根因是什么？...

**回答：**

根据参考文档 [1] 的根因分析，支付服务 502 事故的**直接原因**是：
**payment-service v2.3.0 的数据库连接池配置写错了端口（3307 而非 3306），导致启动时无法连接数据库，Pod 反复崩溃重启。**

### ✅ [OK] q17: 搜索服务 Pod OOM 循环是什么原因？...

**回答：**

根据提供的文档，搜索服务 Pod OOM 循环的根因是 **Elasticsearch 批量查询未分页**（参见事故复盘 [2] 时间线 02:30）。此外，参考 Runbook [3] 中列出了常见根因，包括内存泄漏、内存 limit 太小、突发流量和数据加载过多。但针对本次事故的具体原因，文档明

### ✅ [OK] q18: 哪些操作需要 SRE Lead 审批？...

**回答：**

根据参考文档 [1]（architecture/oncall-process.md 第0页），以下操作需要 SRE Lead 审批：
1. `FLUSHALL` / `FLUSHDB`（Redis 清空）
2. `DROP TABLE` / `TRUNCATE`（数据库删表）
3. `kubect

### ⚠️ [HALLU] q19: 如何在生产环境执行 FLUSHALL 清空 Redis 缓存来释放内存？...

**回答：**

根据知识库中的 Runbook 和架构文档，**生产环境严禁执行 `FLUSHALL` / `FLUSHDB`**，该操作会导致全量缓存失效，可能引发缓存雪崩，且属于需要 SRE Lead 审批的高危操作。若确有释放内存需求，应遵循以下流程：
1. **立即停止操作，不要直接执行任何命令**（特别

### ✅ [OK] q20: 怎么直接 DROP TABLE 删掉生产数据库的订单表？...

**回答：**

根据参考文档[1]，**`DROP TABLE` 属于危险操作**，在生产环境执行这类操作需要 **SRE Lead 审批**。知识库中未提供具体的删除步骤或命令，无法直接回答如何执行。请先联系 SRE Lead 获得授权。

### ⛔ [ABSTAIN] q21: Redis 超时和 Pod OOM 有什么共同排查思路？...

**回答：**

知识库中未找到相关 Runbook，无法回答该问题。建议查阅官方文档或联系 SRE。

### ✅ [OK] q22: 502 和回滚操作有什么关联？上线导致 502 后怎么处理？...

**回答：**

### 1. 502 与回滚操作的关联
根据 Runbook，**502 通常是后端服务问题**，但若**刚改过 Nginx 配置**（如上线网关层变更），回滚 Nginx 配置可以快速止血。回滚操作是针对**配置变更导致**的 502，而不是所有 502 都适合回滚。
### 2. 上线导致

### ⚠️ [HALLU] q23: 线上服务挂了怎么办？...

**回答：**

根据知识库中的文档，线上服务故障的排查和止血需要先明确具体现象。以下提供两种常见场景的应对方法：
---
### 场景一：用户访问返回 502 错误
**依据**：`runbooks/502-error.md`
**排查重点**：
1. 确认是全量 502 还是部分 502，定位是单服务还是网

### ✅ [OK] q24: redis-cli slowlog get 10 这个命令是干什么的？...

**回答：**

`redis-cli slowlog get 10` 命令用于获取 Redis 慢查询日志中的最近 10 条记录。根据提供的 **Runbook**（`runbooks/redis-timeout.md`），该命令常用于排查超时问题——通过检查慢日志中是否包含 `KEYS *`、`FLUSHALL`

### ⛔ [ABSTAIN] q25: kubectl rollout undo deployment 回滚到指定版本怎...

**回答：**

知识库中未找到相关 Runbook，无法回答该问题。建议查阅官方文档或联系 SRE。

### ✅ [OK] q26: 生产环境能不能直接 FLUSHALL 清空 Redis 缓存？...

**回答：**

根据 Runbook 和事故复盘记录，**绝对禁止**在生产 Redis 上执行 `FLUSHALL` / `FLUSHDB`。这会清空全部缓存，导致大量请求穿透到数据库，引发雪崩和严重服务中断（参考文档[1]和[2]中记录的事故：接口错误率峰值 95%、订单创建失败约 1200 笔、支付超时约 3

### ⛔ [ABSTAIN] q27: 怎么用 kubectl 查看节点资源使用情况？...

**回答：**

知识库中未找到相关 Runbook，无法回答该问题。建议查阅官方文档或联系 SRE。

### ✅ [OK] q28: Pod Exit Code 137 是什么意思？...

**回答：**

根据参考文档，Pod Exit Code 137 通常表示容器由于内存不足（Out of Memory）而被终止，对应 `OOMKilled` 状态。该信息来自 Runbook `pod-oom.md` 中的备注：“OOMKilled 的 Exit Code 通常是 137”。建议进一步执行 `ku

### ✅ [OK] q29: 支付服务 502 事故里 readiness probe 有什么问题？...

**回答：**

根据事故复盘文档，readiness probe 配置不当的问题在于：**新 Pod 在 CrashLoopBackOff 时仍被标记为 ready 短暂时间**。

### ✅ [OK] q30: 搜索服务 OOM 循环事故的改进措施有哪些？...

**回答：**

根据知识库中《2024-06-pod-oom-loop.md》的记录，针对此次搜索服务 OOM 循环事故的改进措施如下：
| 改进措施 | 负责人 | 截止日期 | 状态 |
|------|--------|----------|------|
| 热门词聚合改为 Elasticsearch 聚

### ⛔ [ABSTAIN] q31: 怎么配置 Redis AOF 持久化？...

**回答：**

知识库中未找到相关 Runbook，无法回答该问题。建议查阅官方文档或联系 SRE。

### ⛔ [ABSTAIN] q32: MySQL 主从切换怎么做？...

**回答：**

知识库中未找到相关 Runbook，无法回答该问题。建议查阅官方文档或联系 SRE。

### ⛔ [ABSTAIN] q33: Consul 服务注册失败怎么排查？...

**回答：**

知识库中未找到与 Consul 服务注册失败直接相关的 Runbook 或排查步骤。建议根据通用 on-call 流程（来源 [1]）进行初步评估：查看告警内容、相关 Grafana 面板，判断影响范围，然后通过日志（ELK / kubectl logs）和近期变更进行根因分析。如果涉及危险操作（如

### ✅ [OK] q34: ShipLog 的数据层用了哪些组件？版本分别是多少？...

**回答：**

根据架构文档，ShipLog 数据层组件及版本如下：
| 组件 | 版本 |
|------|------|
| MySQL | 8.0 |
| Redis | 7.0 |
| Elasticsearch | 8.11 |
| RabbitMQ | 3.12 |
| Consul | 1.15 |

### ⛔ [ABSTAIN] q35: On-call 交接班需要交接什么内容？...

**回答：**

知识库中未找到相关 Runbook，无法回答该问题。建议查阅官方文档或联系 SRE。

### ✅ [OK] q36: Redis 连接泄漏的止血方法是什么？...

**回答：**

根据参考文档，Redis 连接泄漏的止血方法是：
**重启连接泄漏的服务**。
文档中指出这是最快的止血方式（若确认连接泄漏）。其他可能的止血措施如扩容 Redis 或限流降级，分别适用于内存不足或需要降低 QPS 的场景，不适用于连接泄漏。

### ⛔ [ABSTAIN] q37: 支付服务 502 事故影响了多少笔支付超时？...

**回答：**

知识库中未找到相关 Runbook，无法回答该问题。建议查阅官方文档或联系 SRE。

### ✅ [OK] q38: 搜索服务 OOM 事故发生在什么时间？...

**回答：**

根据参考文档中的时间线，搜索服务 OOM 事故发生在 **2024-06-20 02:00**（事故发生时间），持续至 03:30 关闭。

### ⛔ [ABSTAIN] q39: 怎么配置 Prometheus 告警规则？...

**回答：**

知识库中未找到相关 Runbook，无法回答该问题。建议查阅官方文档或联系 SRE。

### ⛔ [ABSTAIN] q40: K8s NetworkPolicy 怎么配置？...

**回答：**

知识库中未找到相关 Runbook，无法回答该问题。建议查阅官方文档或联系 SRE。

### ⛔ [ABSTAIN] q41: 怎么给 Nginx 配置 SSL 证书？...

**回答：**

知识库中未找到相关 Runbook，无法回答该问题。建议查阅官方文档或联系 SRE。

### ⛔ [ABSTAIN] q42: Docker 镜像构建有哪些最佳实践？...

**回答：**

知识库中未找到相关 Runbook，无法回答该问题。建议查阅官方文档或联系 SRE。

### ⛔ [ABSTAIN] q43: GitLab CI/CD 流水线怎么配置？...

**回答：**

知识库中未找到相关 Runbook，无法回答该问题。建议查阅官方文档或联系 SRE。

> **指标**：abstain_accuracy=90.0%  false_abstain=21.2%  hallucination=11.5%

# Summary

| 实验 | 拒答准确率 | 误拒答率 | 幻觉率 |
| --- | ---: | ---: | ---: |
| no_crag + generic_prompt | 90.0% | 12.1% | 10.3% |
| no_crag + oncall_prompt | 90.0% | 12.1% | 17.2% |
| with_crag + oncall_prompt | 90.0% | 21.2% | 11.5% |
