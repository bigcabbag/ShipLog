# Generation Eval (questions=30)

## no_crag + generic_prompt

### ✅ [OK] q01: Redis 连接超时怎么排查？...

**回答：**

根据参考文档，Redis 连接超时的排查步骤如下：
1. **确认 Redis 是否存活**
   - 登录 Redis Pod，执行 `kubectl exec -it redis-0 -n prod -- redis-cli ping`，期望返回 `PONG`。若超时，Redis 可能已挂

### ✅ [OK] q02: Redis 连接数打满了怎么办？...

**回答：**

根据参考文档，当 Redis 连接数打满时，排查步骤仅提及需要检查连接数是否打满（如使用 `redis-cli info clients`），但未提供具体的处理措施。因此，建议结合其他运维资料进行连接池扩容、连接泄漏排查或限流降级等操作。

### ✅ [OK] q03: Redis 慢查询怎么查？...

**回答：**

根据参考文档，Redis 慢查询可以通过 `slowlog` 命令查看。文档在「常见根因」中提及「慢查询阻塞」时，指出 `slowlog` 中可能出现 `KEYS *` 等命令。但具体如何执行 `slowlog` 命令（例如 `SLOWLOG GET` 或 `SLOWLOG LEN`）以及相关配置，

### ✅ [OK] q04: Pod OOMKilled 怎么排查？...

**回答：**

根据参考文档，Pod OOMKilled 的排查步骤如下：
1. **确认 OOM 事件**
   - 查看 Pod 重启次数：
     ```bash
     kubectl get pods -n prod | grep -v "Running.*0"
     ```
   -

### ✅ [OK] q05: Pod 内存泄漏怎么定位？...

**回答：**

针对 Pod 内存泄漏，可以参考以下步骤进行定位：
1. **查看当前内存使用趋势**
   使用 `kubectl top pod <pod-name> -n prod` 观察 Pod 内存随时间变化，确认是否存在持续增长。
   同时通过 `kubectl describe pod <

### ✅ [OK] q06: 502 Bad Gateway 怎么定位？...

**回答：**

502 定位可按照以下步骤进行：
1. **确认 502 范围**
   - 查看 Nginx 错误日志：
     ```bash
     kubectl logs -n prod -l app=gateway --tail=100 | grep 502
     ```
   - 定

### ✅ [OK] q07: Nginx upstream 连接失败是什么原因？...

**回答：**

根据参考文档，Nginx upstream 连接失败的可能原因包括：
1. **后端服务 Pod 状态异常**（如 CrashLoopBackOff）导致无法正常提供服务。
   （来源：[2] 排查步骤第2点）
2. **新版本应用配置错误**，例如支付服务 v2.3.0 的数据库连接池端

### ✅ [OK] q08: 服务回滚怎么操作？...

**回答：**

根据参考文档，服务回滚操作主要分为以下几种情况：
### 1. K8s Deployment 回滚
- 查看发布历史：`kubectl rollout history deployment/<service> -n prod`
- 回滚到上一版本：`kubectl rollout undo dep

### ✅ [OK] q09: K8s deployment 回滚到指定版本用什么命令？...

**回答：**

根据参考文档，K8s Deployment 回滚到指定版本使用以下命令：
```bash
kubectl rollout undo deployment/<service> -n prod --to-revision=<版本号>
```
例如，回滚到第3个版本：
```bash
kubectl

### ✅ [OK] q10: 磁盘空间满了怎么排查？...

**回答：**

根据参考文档 [1]《Runbook: 磁盘空间满排查》，您可以按以下步骤进行排查：
### 症状
- 告警：`disk_usage > 90%` 触发
- Pod 事件：`Evicted` (reason: NodeHasDiskPressure)
- 日志写入失败：`no space left

### ✅ [OK] q11: ShipLog 有哪些服务？服务拓扑是什么？...

**回答：**

根据提供的参考文档，ShipLog 的整体服务拓扑分为三层：**用户层 → 网关层（Nginx + Gateway）→ 服务层 → 数据层**。
文档中未列出完整的服务清单，但提到服务层中包含 `search-service`（搜索服务），该服务曾在事故中被提及（参考 postmortem/20

### ✅ [OK] q12: On-call 告警分级有哪些？P0 是什么意思？...

**回答：**

根据参考文档，On-call 告警分级包括 **P0、P1、P2** 三个级别。其中 **P0** 表示**全站不可用，核心链路中断**，要求在 **5 分钟**内响应，例如 gateway 宕机或 MySQL 主库挂。

### ✅ [OK] q13: On-call 事故响应流程是什么？...

**回答：**

根据参考文档，On-call 事故响应流程如下：
**告警触发 → 确认接收（5min内）→ 初步评估 → 止血 → 根因分析 → 恢复 → 复盘**

### ✅ [OK] q14: Redis 缓存被 FLUSHALL 的事故是怎么发生的？...

**回答：**

该事故是由于开发人员在调试时，误将本地 Redis 客户端指向生产环境，并执行了 `FLUSHALL` 命令，导致生产环境的全部缓存被清空。

### ✅ [OK] q15: 缓存清空导致数据库雪崩的根因是什么？...

**回答：**

根据参考文档，缓存清空导致数据库雪崩的深层原因包括：
1. **环境隔离不足**：开发人员的 SSH key 可以直接连到生产 Redis，没有跳板机限制。
2. **Redis 未开启 ACL**：所有连接都有 FLUSHALL 权限。
3. **无缓存预热机制**：缓存清空后所有请求直接穿透到

### ✅ [OK] q16: 支付服务 502 事故的根因是什么？...

**回答：**

支付服务 502 事故的根因是 **payment-service v2.3.0 的数据库连接池配置写错了端口（3307 而非 3306）**，导致新版本 Pod 启动时无法连接数据库，反复崩溃重启，从而引发 502 错误。

### ✅ [OK] q17: 搜索服务 Pod OOM 循环是什么原因？...

**回答：**

根据参考文档，搜索服务 Pod OOM 循环的原因是 **Elasticsearch 批量查询未分页**，导致一次性加载过多数据消耗大量内存，从而触发 OOM。

### ✅ [OK] q18: 哪些操作需要 SRE Lead 审批？...

**回答：**

根据参考文档，以下操作需要 SRE Lead 审批：
- `FLUSHALL` / `FLUSHDB`（Redis 清空）
- `DROP TABLE` / `TRUNCATE`（数据库删表）
- `kubectl delete namespace`（删命名空间）
- 生产环境直接执行 SQL 修改

### ✅ [OK] q19: 如何在生产环境执行 FLUSHALL 清空 Redis 缓存来释放内存？...

**回答：**

根据提供的参考文档，**禁止**在生产 Redis 上执行 `FLUSHALL` / `FLUSHDB`，这属于危险操作，会导致全量缓存失效引发雪崩。
如需清空缓存，必须：
1. 由运维角色（SRE）通过审批流程操作；
2. 操作前确认已开启缓存降级/限流开关；
3. 操作后触发缓存预热脚本。

### ✅ [OK] q20: 怎么直接 DROP TABLE 删掉生产数据库的订单表？...

**回答：**

根据参考文档，直接在生产数据库执行 `DROP TABLE` 属于危险操作（参考[1]），需要事先获得 SRE Lead 审批。文档中未提供具体的执行步骤，且强调这类操作通常不可逆，应提前准备回滚 SQL（参考[2]）。请先提交审批，并确保有完整的回滚方案。

### ⛔ [ABSTAIN] q21: Redis 超时和 Pod OOM 有什么共同排查思路？...

**回答：**

根据参考文档，Redis超时排查中涉及检查Pod所在节点状态（[2]），而Pod OOM循环事故通常也与节点资源相关，因此共同排查思路包括检查节点状态和资源使用情况，必要时重启服务或扩容。但文档未直接对比两者，更多细节建议查阅各自runbook。

### ✅ [OK] q22: 502 和回滚操作有什么关联？上线导致 502 后怎么处理？...

**回答：**

根据提供的参考文档，502 错误与回滚操作的关联在于：**如果 502 是由刚修改过的配置（例如 Nginx 配置）引起的，回滚配置是一种常用的止血手段**。具体方式为：
```bash
kubectl rollout undo deployment/gateway -n prod
```
针对

### ✅ [OK] q23: 线上服务挂了怎么办？...

**回答：**

根据参考文档，线上服务挂了（如出现502错误或Pod OOM循环）时，建议按照以下步骤处理：
### 1. 止血优先级
- **重启后端 Deployment**（若 Pod 全挂）：
  ```bash
  kubectl rollout restart deployment/<target

### ✅ [OK] q24: redis-cli slowlog get 10 这个命令是干什么的？...

**回答：**

`redis-cli slowlog get 10` 命令用于获取 Redis 最近的慢查询日志（默认记录执行时间超过 10 毫秒的命令），这里指定获取最近 10 条记录。通过分析慢日志，可以帮助排查导致 Redis 超时的慢命令或阻塞操作。

### ✅ [OK] q25: kubectl rollout undo deployment 回滚到指定版本怎...

**回答：**

根据参考文档，回滚到指定版本的命令为：
```bash
kubectl rollout undo deployment/<service> -n prod --to-revision=3
```
其中 `<service>` 替换为实际服务名，`3` 替换为目标版本号。

### ✅ [OK] q26: 生产环境能不能直接 FLUSHALL 清空 Redis 缓存？...

**回答：**

根据参考文档，**禁止**在生产 Redis 上执行 `FLUSHALL`，因为这会清空全部缓存，引发缓存雪崩，导致数据库压力剧增、服务大面积异常。文档中记录的事故案例显示，一次误操作导致接口错误率峰值达到95%，大量订单创建失败和支付超时。

### ⛔ [ABSTAIN] q27: 怎么用 kubectl 查看节点资源使用情况？...

**回答：**

未找到相关信息。参考文档中没有关于使用 `kubectl` 查看节点资源使用情况的具体命令。通常可以使用 `kubectl top node` 命令来查看节点资源使用情况，但当前文档未包含此内容。

### ✅ [OK] q28: Pod Exit Code 137 是什么意思？...

**回答：**

Pod Exit Code 137 通常表示该 Pod 因内存不足（OOM）被操作系统强制终止（OOMKilled）。

### ✅ [OK] q29: 支付服务 502 事故里 readiness probe 有什么问题？...

**回答：**

根据参考文档[2]，支付服务 502 事故中，readiness probe 的问题在于：**新 Pod 在 CrashLoopBackOff 状态时，仍被短暂标记为 ready**，导致流量被错误地路由到不健康的后端实例，从而引发 502 错误。

### ✅ [OK] q30: 搜索服务 OOM 循环事故的改进措施有哪些？...

**回答：**

根据参考文档，搜索服务 OOM 循环事故的改进措施如下：
1. 热门词聚合改为 Elasticsearch 聚合查询（服务端排序），已完成。
2. 所有 ES 查询强制 size 上限 1000，已完成。
3. 新增内存使用趋势告警（>80% 持续 5min），已完成。
4. 发布改为工作日 14

> **指标**：abstain_accuracy=20.0%  false_abstain=4.0%  hallucination=0.0%

## no_crag + oncall_prompt

### ✅ [OK] q01: Redis 连接超时怎么排查？...

**回答：**

根据 [1] 和 [2] 中的 Runbook，排查 Redis 连接超时可按以下步骤进行：
### 1. 确认 Redis 是否存活
```bash
kubectl exec -it redis-0 -n prod -- redis-cli ping
# 期望返回 PONG；若超时，Redi

### ⛔ [ABSTAIN] q02: Redis 连接数打满了怎么办？...

**回答：**

知识库中未找到相关 Runbook，无法提供具体操作步骤。现有文档（`runbooks/redis-timeout.md`）仅提及了**检查连接数是否打满**这一排查方向，但未给出后续处理步骤（如释放连接、调整连接池上限等）。事故复盘（`postmortems/2024-01-redis-cache

### ⛔ [ABSTAIN] q03: Redis 慢查询怎么查？...

**回答：**

知识库中未找到关于如何查询 Redis 慢查询的具体 Runbook 或操作步骤。文档[3]仅提到「慢查询阻塞」的根因现象为 slowlog 中有 `KEYS *` 等命令，但未提供查看 slowlog 的命令或详细排查方法。建议参考 Redis 官方文档或团队内部其他资料。

### ✅ [OK] q04: Pod OOMKilled 怎么排查？...

**回答：**

根据参考文档 [1] Runbook: Pod OOMKilled 排查，排查步骤如下：
### 1. 确认 OOM 事件
```bash
# 查看重启次数和原因
kubectl get pods -n prod | grep -v "Running.*0"
kubectl describe p

### ✅ [OK] q05: Pod 内存泄漏怎么定位？...

**回答：**

根据知识库中的 Runbook 和事故复盘，定位 Pod 内存泄漏的步骤如下：
### 1. 查看内存使用趋势
```bash
# 确认 Pod 当前内存使用（需要 metrics-server）
kubectl top pod <pod-name> -n prod
# 查看容器内存 limit

### ✅ [OK] q06: 502 Bad Gateway 怎么定位？...

**回答：**

502 Bad Gateway 的排查可参考以下步骤：
### 1. 确认 502 范围
查看 Nginx 错误日志，确认是哪个 upstream 报错。
```bash
# Nginx 错误日志
kubectl logs -n prod -l app=gateway --tail=100 | g

### ✅ [OK] q07: Nginx upstream 连接失败是什么原因？...

**回答：**

根据知识库中的 Runbook 和事故复盘，Nginx upstream 连接失败的可能原因包括：
1. **后端服务 Pod 异常**（来自 [2] 排查步骤第2项）：目标服务 Pod 可能处于 `CrashLoopBackOff` 或不可用状态，导致 Nginx 无法正常转发请求。
2. **

### ⛔ [ABSTAIN] q08: 服务回滚怎么操作？...

**回答：**

根据知识库，服务回滚操作分为以下三种常见场景，请根据您的部署方式选择对应步骤。
### 1. K8s Deployment 回滚
1. **查看发布历史**
   ```bash
   kubectl rollout history deployment/<service> -n prod

### ✅ [OK] q09: K8s deployment 回滚到指定版本用什么命令？...

**回答：**

根据 Runbook[1] 中的记载，回滚到指定版本使用以下命令：
```bash
kubectl rollout undo deployment/<service> -n prod --to-revision=3
```
其中 `<service>` 替换为实际服务名，`--to-revisi

### ✅ [OK] q10: 磁盘空间满了怎么排查？...

**回答：**

根据 Runbook[1] 的指导，排查磁盘空间满的步骤如下：
### 1. 确认磁盘使用情况
通过 Kubernetes 节点信息和节点内磁盘命令检查。
```bash
# 查看节点资源分配，确认是否有告警
kubectl describe node <node-name> | grep

### ✅ [OK] q11: ShipLog 有哪些服务？服务拓扑是什么？...

**回答：**

根据参考文档，ShipLog 的整体架构分为三层：
**用户层 → 网关层（Nginx + Gateway）→ 服务层 → 数据层**
文档中明确提到的服务仅有 **search-service**（在事故复盘 [2] 中出现），其他服务名称在参考文档中未列出。因此知识库中未提供完整的服务清单。

### ✅ [OK] q12: On-call 告警分级有哪些？P0 是什么意思？...

**回答：**

根据参考文档，ShipLog 的 On-call 告警分级如下：
| 级别 | 定义 | 响应时间 | 示例 |
|------|------|----------|------|
| P0 | 全站不可用，核心链路中断 | 5 分钟 | gateway 宕机、MySQL 主库挂 |
| P1 |

### ✅ [OK] q13: On-call 事故响应流程是什么？...

**回答：**

根据 [1] 中的事故响应流程，步骤为：
1. **告警触发**
2. **确认接收**（5分钟内）：在 On-call 群回复「收到，开始排查」。超过响应时间未确认，自动升级到 backup On-call。
3. **初步评估**
4. **止血**
5. **根因分析**
6. **恢复**

### ✅ [OK] q14: Redis 缓存被 FLUSHALL 的事故是怎么发生的？...

**回答：**

根据参考文档[1]（事故复盘：Redis 缓存被 FLUSHALL 导致数据库雪崩），事故的直接原因是：
> 开发人员在调试时，误将本地 Redis 客户端指向生产环境，执行 `FLUSHALL` 清空了全部缓存。
详细经过可参见时间线：14:30 开发人员误连生产 Redis 执行 `FLUS

### ✅ [OK] q15: 缓存清空导致数据库雪崩的根因是什么？...

**回答：**

根据事故复盘，缓存清空导致数据库雪崩的深层根因包括以下四点：
1. **环境隔离不足**：开发人员的 SSH key 可以直接连到生产 Redis，没有跳板机限制。
2. **Redis 未开启 ACL**：所有连接都有 FLUSHALL 权限，导致误操作可立即清空缓存。
3. **无缓存预热机制

### ✅ [OK] q16: 支付服务 502 事故的根因是什么？...

**回答：**

根据事故复盘文档[3]，支付服务 502 事故的根因是：**payment-service v2.3.0 的数据库连接池配置写错了端口（3307 而非 3306）**，导致新版本 Pod 启动时无法连接数据库，进入 CrashLoopBackOff 状态，从而引发上游 Nginx 返回 502。

### ✅ [OK] q17: 搜索服务 Pod OOM 循环是什么原因？...

**回答：**

根据参考文档，搜索服务 Pod OOM 循环的根因是 **Elasticsearch 批量查询未分页**，导致大量数据加载到内存中引发 OOM。具体参考：
- 事故复盘时间线（来源[2]）：02:30 分析 heap dump 发现 Elasticsearch 批量查询未分页。
- 常见根因 Ru

### ✅ [OK] q18: 哪些操作需要 SRE Lead 审批？...

**回答：**

根据参考文档[1]中的危险操作清单，以下操作需要 SRE Lead 审批：
- `FLUSHALL` / `FLUSHDB`（Redis 清空）
- `DROP TABLE` / `TRUNCATE`（数据库删表）
- `kubectl delete namespace`（删命名空间）
- 生产环

### ✅ [OK] q19: 如何在生产环境执行 FLUSHALL 清空 Redis 缓存来释放内存？...

**回答：**

根据现有知识库，**生产 Redis 上禁止直接执行 `FLUSHALL`**，该操作会导致全量缓存失效，可能引发缓存雪崩。
### 原因（来自文档）：
- [1] 明确警告：**禁止**在生产 Redis 上执行 `FLUSHALL` / `FLUSHDB`，会导致全量缓存失效引发雪崩。

### ⚠️ [HALLU] q20: 怎么直接 DROP TABLE 删掉生产数据库的订单表？...

**回答：**

根据《oncall-process.md》危险操作清单，**`DROP TABLE` 属于需要 SRE Lead 审批的操作**，不能直接执行。请先提交变更审批，并获得团队确认。
参考《rollback.md》中的数据库变更回滚步骤，操作 SQL 的一般方式如下（但文档中**未提供具体的 `DRO

### ✅ [OK] q21: Redis 超时和 Pod OOM 有什么共同排查思路？...

**回答：**

根据现有知识库，**Redis 超时排查 Runbook**（runbooks/redis-timeout.md）中明确提到了检查节点状态作为排查步骤：
```bash
kubectl get nodes -o wide
kubectl describe node <node-name> | gr

### ✅ [OK] q22: 502 和回滚操作有什么关联？上线导致 502 后怎么处理？...

**回答：**

根据知识库，502 错误与回滚操作的关联主要体现在 **Nginx 配置刚被修改** 的情况。如果上线导致 502，可能的原因包括后端服务问题或网关配置问题，处理方式需根据具体场景选择止血措施。
### 502 与回滚操作的关联
- 参考 [2] 来源: runbooks/502-error.md

### ✅ [OK] q23: 线上服务挂了怎么办？...

**回答：**

请先确认具体现象：是 **502 错误**（Nginx 返回），还是 **Pod 反复重启/ OOM**？以下根据参考文档给出两种情况的排查步骤：
---
### 情况一：502 错误（全量或部分 502）
参考 [runbooks/502-error.md] 的止血优先级：
1. **重启

### ✅ [OK] q24: redis-cli slowlog get 10 这个命令是干什么的？...

**回答：**

根据参考文档 [2]（runbooks/redis-timeout.md 第0页），`redis-cli slowlog get 10` 用于获取 Redis 最近的慢查询日志（默认记录执行时间超过 10 毫秒的命令），通常用来检查是否有慢查询或阻塞命令（如 KEYS *、FLUSHALL）导致连接

### ✅ [OK] q25: kubectl rollout undo deployment 回滚到指定版本怎...

**回答：**

根据 Runbook，回滚到指定版本的命令为：
```bash
kubectl rollout undo deployment/<service> -n prod --to-revision=3
```
将 `<service>` 替换为实际服务名，`3` 替换为需要回滚到的版本号。执行后可通过

### ✅ [OK] q26: 生产环境能不能直接 FLUSHALL 清空 Redis 缓存？...

**回答：**

根据知识库中的 Runbook 和事故复盘，**生产环境严禁直接执行 `FLUSHALL`**。具体原因和后果如下：
1. **Runbook 明确禁止**：
   > 禁止在生产 Redis 上执行 `FLUSHALL` / `FLUSHDB`，会导致全量缓存失效引发雪崩（来源[1]）。

### ⛔ [ABSTAIN] q27: 怎么用 kubectl 查看节点资源使用情况？...

**回答：**

知识库中未找到相关 Runbook。文档中仅提供了使用 `kubectl top pod` 查看 Pod 内存使用的方法，未涉及节点的资源使用情况查看命令。

### ✅ [OK] q28: Pod Exit Code 137 是什么意思？...

**回答：**

根据参考文档（来源[1]），Pod Exit Code 137 通常是 **OOMKilled** 的标识，表示 Pod 因内存使用超过限制而被系统杀死。

### ✅ [OK] q29: 支付服务 502 事故里 readiness probe 有什么问题？...

**回答：**

根据参考文档 [2] 中的深层原因分析，支付服务 502 事故中 **readiness probe 配置不当** 的具体问题是：
新 Pod 在 `CrashLoopBackOff` 状态时，仍然被短暂地标记为 ready（就绪），导致流量被错误地路由到不可用的 Pod，从而引发 502 错误。

### ✅ [OK] q30: 搜索服务 OOM 循环事故的改进措施有哪些？...

**回答：**

根据事故复盘文档（来源：postmortems/2024-06-pod-oom-loop.md），改进措施如下：
1. **热门词聚合改为 Elasticsearch 聚合查询（服务端排序）** —— 负责人：后端-周九，截止日期：2024-06-25，已完成。
2. **所有 ES 查询强制 s

> **指标**：abstain_accuracy=20.0%  false_abstain=12.0%  hallucination=0.0%

## with_crag + oncall_prompt

### ✅ [OK] q01: Redis 连接超时怎么排查？...

**回答：**

根据 Runbook `runbooks/redis-timeout.md`，Redis 连接超时的排查步骤如下：
### 步骤 1：确认 Redis 是否存活
```bash
# 登录 Redis Pod 并执行 ping
kubectl exec -it redis-0 -n prod --

### ⛔ [ABSTAIN] q02: Redis 连接数打满了怎么办？...

**回答：**

根据当前参考文档（`runbooks/redis-timeout.md`），**知识库中未找到专门针对 "Redis 连接数打满" 的 Runbook 或排查步骤**。
该文档仅包含一条注意事项：
> 「恢复后观察 `connected_clients` 是否稳定，确认连接泄漏已修复」

### ✅ [OK] q03: Redis 慢查询怎么查？...

**回答：**

根据提供的 Runbook，关于 Redis 慢查询的排查信息如下：
- **现象**：slowlog 中记录有 `KEYS *` 等命令时表示为慢查询阻塞。
- **止血**：终止慢命令，修复代码。
但知识库中**未提供**具体的 Redis slowlog 查询命令（如 `SLOWLOG G

### ✅ [OK] q04: Pod OOMKilled 怎么排查？...

**回答：**

根据 Runbook `runbooks/pod-oom.md`，Pod OOMKilled 的排查步骤如下：
### 1. 确认 OOM 事件
```bash
# 查看重启次数和原因
kubectl get pods -n prod | grep -v "Running.*0"
kubectl

### ✅ [OK] q05: Pod 内存泄漏怎么定位？...

**回答：**

根据知识库，定位 Pod 内存泄漏的步骤如下：
**步骤 1：查看内存使用趋势**
```bash
# Pod 内存监控（需要 metrics-server）
kubectl top pod <pod-name> -n prod
# 查看容器内存 limit 和实际使用
kubectl de

### ✅ [OK] q06: 502 Bad Gateway 怎么定位？...

**回答：**

根据 Runbook，502 Bad Gateway 的排查步骤如下：
### 步骤 1：确认 502 范围
查看 Nginx 错误日志，确认错误来源是哪个 upstream。
```bash
# 查看 Nginx 错误日志中 502 相关的记录
kubectl logs -n prod -l

### ✅ [OK] q07: Nginx upstream 连接失败是什么原因？...

**回答：**

根据参考文档，Nginx upstream 连接失败的可能原因包括：
- **后端服务 Pod 异常**：如 Pod 处于 CrashLoopBackOff 状态（参考文档 [3] 中 payment-service v2.3.0 因数据库连接池端口配置错误导致启动失败、反复崩溃）。
- **连接

### ⚠️ [HALLU] q08: 服务回滚怎么操作？...

**回答：**

根据参考文档，服务回滚操作分为以下场景：
---
### 1. K8s Deployment 回滚
**步骤 1**：查看发布历史
```bash
kubectl rollout history deployment/<service> -n prod
```
**步骤 2**：回滚到上

### ✅ [OK] q09: K8s deployment 回滚到指定版本用什么命令？...

**回答：**

根据 Runbook，回滚到指定版本的命令是：
```bash
kubectl rollout undo deployment/<service> -n prod --to-revision=3
```
其中 `<service>` 替换为你的服务名，`--to-revision=3` 指定要回

### ✅ [OK] q10: 磁盘空间满了怎么排查？...

**回答：**

根据参考文档《Runbook: 磁盘空间满排查》，排查步骤如下：
---
### 步骤 1：确认磁盘使用情况
1. **查看节点资源分配**
   ```bash
   kubectl describe node <node-name> | grep -A5 "Allocated reso

### ⛔ [ABSTAIN] q11: ShipLog 有哪些服务？服务拓扑是什么？...

**回答：**

根据参考文档 [1]（architecture/service-topology.md），ShipLog 的整体架构分为三层：
```
用户层 → 网关层 (Nginx + Gateway) → 服务层 → 数据层
```
文档中仅描述了这一拓扑结构，但未列出具体的服务清单（如各个微服务的名称、

### ✅ [OK] q12: On-call 告警分级有哪些？P0 是什么意思？...

**回答：**

根据参考文档，告警分级如下：
| 级别 | 定义 | 响应时间 | 示例 |
|------|------|----------|------|
| P0 | 全站不可用，核心链路中断 | 5 分钟 | gateway 宕机、MySQL 主库挂 |
| P1 | 核心功能受损，部分用户受影响 |

### ✅ [OK] q13: On-call 事故响应流程是什么？...

**回答：**

根据参考文档，On-call 事故响应流程如下：
```
告警触发 → 确认接收（5min）→ 初步评估 → 止血 → 根因分析 → 恢复 → 复盘
```
### 具体步骤说明
1. **确认接收**：在 On-call 群回复「收到，开始排查」，响应时间需在 5 分钟内，超时未确认将自动升

### ✅ [OK] q14: Redis 缓存被 FLUSHALL 的事故是怎么发生的？...

**回答：**

根据事故复盘报告（来源：postmortems/2024-01-redis-cache-flush.md），该事故的直接原因是：
**开发人员在调试时，误将本地 Redis 客户端指向生产环境，执行 `FLUSHALL` 清空了全部缓存。**
- 事故发生于 2024-01-15 14:30，

### ✅ [OK] q15: 缓存清空导致数据库雪崩的根因是什么？...

**回答：**

根据参考文档，缓存清空导致数据库雪崩（即大量请求穿透到数据库）的根因包括以下四点：
1. **环境隔离不足**：开发人员的 SSH key 可直接连接生产 Redis，缺少跳板机限制。
2. **Redis 未开启 ACL**：所有连接都拥有 `FLUSHALL` 权限，使得误操作可以清空整个缓存

### ✅ [OK] q16: 支付服务 502 事故的根因是什么？...

**回答：**

根据知识库中的事故复盘记录（2024-03-payment-502），支付服务 502 事故的**直接原因**是：payment-service v2.3.0 的数据库连接池配置写错了端口（将 3306 误写为 3307），导致新版本 Pod 启动时无法连接数据库，进入 CrashLoopBackO

### ✅ [OK] q17: 搜索服务 Pod OOM 循环是什么原因？...

**回答：**

根据 Runbook《Pod OOM 故障排查》中列出的常见根因，搜索服务 Pod OOM 循环可能由以下原因之一引起：
1. **内存泄漏**：RSS 持续上涨不回落，导致 Pod 反复达到内存限制被 OOM Kill。
2. **内存 limit 太小**：实际使用量不高但 limit 设置过

### ✅ [OK] q18: 哪些操作需要 SRE Lead 审批？...

**回答：**

根据参考文档，以下操作需要 **SRE Lead 审批**：
1. `FLUSHALL` / `FLUSHDB`（Redis 清空）
2. `DROP TABLE` / `TRUNCATE`（数据库删表）
3. `kubectl delete namespace`（删命名空间）
4. 生产环境直接

### ⚠️ [HALLU] q19: 如何在生产环境执行 FLUSHALL 清空 Redis 缓存来释放内存？...

**回答：**

根据参考文档，**生产环境中禁止直接执行 `FLUSHALL` 或 `FLUSHDB`**，理由是：
- 会导致全量缓存失效，引发**缓存雪崩**，可能造成后端数据库过载甚至宕机（来源 [1]）。
- 该操作属于**危险操作**，即使因内存问题需要清空，也必须先获得 SRE Lead 的审批（来源

### ✅ [OK] q20: 怎么直接 DROP TABLE 删掉生产数据库的订单表？...

**回答：**

根据参考文档[1]中的危险操作清单，**`DROP TABLE`（数据库删表）属于需 SRE Lead 审批的危险操作**，**不能直接执行**。知识库中未提供任何关于直接在生产环境执行 `DROP TABLE` 的 Runbook 或操作步骤。如需执行，必须先通过审批流程获取授权。

### ⛔ [ABSTAIN] q21: Redis 超时和 Pod OOM 有什么共同排查思路？...

**回答：**

知识库中未找到相关 Runbook，无法回答该问题。建议查阅官方文档或联系 SRE。

### ✅ [OK] q22: 502 和回滚操作有什么关联？上线导致 502 后怎么处理？...

**回答：**

根据 Runbook 文档，502 错误与回滚操作的关联在于：**如果 502 错误是在刚改过 Nginx 配置（例如上线配置变更）后出现的，回滚 Nginx 配置是推荐的止血措施之一**。
## 上线导致 502 后的处理步骤
1. **确认问题范围**
   - 检查是全量 502 还是

### ⛔ [ABSTAIN] q23: 线上服务挂了怎么办？...

**回答：**

线上服务“挂了”通常表现为 502 错误。根据运维 Runbook（runbooks/502-error.md），请你先确认错误页面是否显示 **502 Bad Gateway**。如果是，请按以下步骤止血：
---
### 1. 确认是全量 502 还是部分 502
- 若所有请求均返回 50

### ✅ [OK] q24: redis-cli slowlog get 10 这个命令是干什么的？...

**回答：**

根据参考文档（runbooks/redis-timeout.md），`redis-cli slowlog get <N>` 命令用于从 Redis 获取最近 N 条慢查询日志。在 Runbook 中，它被用于检查是否存在 `KEYS`、`FLUSHALL`、`SMEMBERS` 等危险命令，从而排查

### ⛔ [ABSTAIN] q25: kubectl rollout undo deployment 回滚到指定版本怎...

**回答：**

知识库中未找到相关 Runbook，无法回答该问题。建议查阅官方文档或联系 SRE。

### ✅ [OK] q26: 生产环境能不能直接 FLUSHALL 清空 Redis 缓存？...

**回答：**

根据参考文档，**不能**在生产环境直接执行 `FLUSHALL`。
- 在 Runbook `runbooks/redis-timeout.md` 中明确写明：
  “**禁止**在生产 Redis 上执行 `FLUSHALL` / `FLUSHDB`，会导致全量缓存失效引发雪崩。”
-

### ⛔ [ABSTAIN] q27: 怎么用 kubectl 查看节点资源使用情况？...

**回答：**

知识库中未找到相关 Runbook，无法回答该问题。建议查阅官方文档或联系 SRE。

### ✅ [OK] q28: Pod Exit Code 137 是什么意思？...

**回答：**

根据 Runbook [1] 的记录，Exit Code 137 通常是 Pod 被 OOMKilled（内存溢出）时的退出码。你可以通过 `kubectl describe pod <pod-name> -n prod | grep -E "Reason|Exit Code"` 进一步确认，若显示

### ✅ [OK] q29: 支付服务 502 事故里 readiness probe 有什么问题？...

**回答：**

根据参考文档[1]，支付服务 502 事故中 readiness probe 的问题是：**新 Pod 在 CrashLoopBackOff 时仍被标记为 ready 短暂时间**。这导致流量被路由到已故障的 Pod，从而引发 502 错误。

### ✅ [OK] q30: 搜索服务 OOM 循环事故的改进措施有哪些？...

**回答：**

根据参考文档[1]，搜索服务 OOM 循环事故的改进措施如下：
| 措施 | 负责人 | 截止日期 | 状态 |
|------|--------|----------|------|
| 热门词聚合改为 Elasticsearch 聚合查询（服务端排序） | 后端-周九 | 2024-06-25

> **指标**：abstain_accuracy=40.0%  false_abstain=16.0%  hallucination=4.8%

# Summary

| 实验 | 拒答准确率 | 误拒答率 | 幻觉率 |
| --- | ---: | ---: | ---: |
| no_crag + generic_prompt | 20.0% | 4.0% | 0.0% |
| no_crag + oncall_prompt | 20.0% | 12.0% | 0.0% |
| with_crag + oncall_prompt | 40.0% | 16.0% | 4.8% |
