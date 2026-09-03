# Generation Eval (questions=30)

## no_crag + generic_prompt

### ✅ [OK] q01: Redis 连接超时怎么排查？...

**回答：**

根据参考文档，Redis 连接超时可按以下步骤排查：
1. **确认 Redis 是否存活**
   - 登录 Redis Pod，执行 `redis-cli ping`，期望返回 `PONG`。若超时，Redis 可能已挂或网络不通。
   - 使用 `redis-cli info se

### ⚠️ [HALLU] q02: Redis 连接数打满了怎么办？...

**回答：**

根据参考文档，当 Redis 连接数打满时，建议执行以下排查步骤：
1. 登录 Redis Pod 检查当前连接数：
   ```bash
   kubectl exec -it redis-0 -n prod -- redis-cli info clients
   ```
   查看 `con

### ✅ [OK] q03: Redis 慢查询怎么查？...

**回答：**

根据参考文档，Redis 慢查询可以通过 `slowlog` 功能查看。文档中提及慢查询阻塞的根因示例为 `slowlog 有 KEYS * 等命令`。具体查询命令（如 `SLOWLOG GET`）未在文档中详细说明，建议参考 Redis 官方文档进一步了解。

### ⚠️ [HALLU] q04: Pod OOMKilled 怎么排查？...

**回答：**

根据参考文档，排查 Pod OOMKilled 的步骤如下：
1. **确认 OOM 事件**
   - 使用 `kubectl get pods` 查看重启次数大于 0 的 Pod。
   - 使用 `kubectl describe pod <pod-name>` 查看 `Last S

### ✅ [OK] q05: Pod 内存泄漏怎么定位？...

**回答：**

根据参考文档，定位 Pod 内存泄漏可采取以下步骤：
1. **查看内存使用趋势**
   使用 `kubectl top pod <pod-name> -n prod` 监控 Pod 内存变化，并用 `kubectl describe pod` 查看容器内存 limit 和实际使用情况。

### ✅ [OK] q06: 502 Bad Gateway 怎么定位？...

**回答：**

502 Bad Gateway 的定位可以按照以下步骤进行：
1. **确认 502 范围**：查看 Nginx 错误日志，找出报 502 的 upstream。
   示例命令：
   `kubectl logs -n prod -l app=gateway --tail=100 | g

### ✅ [OK] q07: Nginx upstream 连接失败是什么原因？...

**回答：**

根据参考文档，Nginx upstream 连接失败的常见原因包括：
- **后端服务崩溃或异常**：如 Pod 处于 `CrashLoopBackOff` 状态，导致无法接受新连接（参考[3]中 payment-service 因数据库连接配置错误引发的故障）。
- **数据库连接配置错误**：

### ✅ [OK] q08: 服务回滚怎么操作？...

**回答：**

根据参考文档，服务回滚操作分为以下几种常见场景：
### 1. K8s Deployment 回滚
```bash
# 查看发布历史
kubectl rollout history deployment/<service> -n prod
# 回滚到上一版本
kubectl rollout un

### ✅ [OK] q09: K8s deployment 回滚到指定版本用什么命令？...

**回答：**

根据参考文档，K8s Deployment 回滚到指定版本的命令是：
```bash
kubectl rollout undo deployment/<service> -n prod --to-revision=3
```
其中 `<service>` 为服务名称，`--to-revision

### ✅ [OK] q10: 磁盘空间满了怎么排查？...

**回答：**

根据参考文档，磁盘空间满的排查步骤如下：
### 1. 确认磁盘使用情况
- 查看节点磁盘使用：
  ```bash
  kubectl describe node <node-name> | grep -A5 "Allocated resources"
  ```
- SSH 到节点查看：

### ✅ [OK] q11: ShipLog 有哪些服务？服务拓扑是什么？...

**回答：**

根据参考文档，ShipLog 的服务拓扑分为三层：用户层 → 网关层 (Nginx + Gateway) → 服务层 → 数据层。文档中未列出所有服务的完整清单，但提到了一个具体的服务 `search-service`（见事故分析文档）。

### ✅ [OK] q12: On-call 告警分级有哪些？P0 是什么意思？...

**回答：**

根据参考文档，On-call 告警分级包括 P0、P1、P2 三个级别：
- **P0**：全站不可用，核心链路中断，响应时间为 5 分钟，示例包括 gateway 宕机、MySQL 主库挂。
- **P1**：核心功能受损，部分用户受影响，响应时间为 15 分钟，示例包括支付成功率下降 >5%、

### ✅ [OK] q13: On-call 事故响应流程是什么？...

**回答：**

根据参考文档，On-call 事故响应流程如下：
```
告警触发 → 确认接收（5min）→ 初步评估 → 止血 → 根因分析 → 恢复 → 复盘
```
其中确认接收要求：在 On-call 群回复「收到，开始排查」，若超过响应时间未确认，则自动升级到 backup On-call。

### ✅ [OK] q14: Redis 缓存被 FLUSHALL 的事故是怎么发生的？...

**回答：**

根据参考文档，该事故的直接原因是开发人员在调试时，误将本地 Redis 客户端指向生产环境，执行了 `FLUSHALL` 命令，导致生产环境的全部缓存被清空。随后引发缓存雪崩，所有依赖缓存的接口超时，MySQL 数据库 QPS 暴涨，最终造成全站不可用。

### ✅ [OK] q15: 缓存清空导致数据库雪崩的根因是什么？...

**回答：**

根据参考文档，缓存清空导致数据库雪崩的深层原因包括：
1. **环境隔离不足**：开发人员的 SSH key 可以直接连到生产 Redis，没有跳板机限制。
2. **Redis 未开启 ACL**：所有连接都有 FLUSHALL 权限。
3. **无缓存预热机制**：缓存清空后所有请求直接穿透到数

### ✅ [OK] q16: 支付服务 502 事故的根因是什么？...

**回答：**

支付服务 502 事故的直接原因是 payment-service v2.3.0 的数据库连接池配置错误，将端口写为 3307（正确应为 3306），导致新版本 Pod 启动时无法连接数据库，反复崩溃重启，进而引发支付接口 502。

### ✅ [OK] q17: 搜索服务 Pod OOM 循环是什么原因？...

**回答：**

根据参考文档，搜索服务 Pod OOM 循环的原因是：**Elasticsearch 批量查询未分页**，导致内存被大量消耗，最终触发 OOMKilled。具体分析见事故复盘（来源[2]）和常见根因列表（来源[3]）。

### ✅ [OK] q18: 哪些操作需要 SRE Lead 审批？...

**回答：**

根据参考文档，以下操作需要 SRE Lead 审批：
- `FLUSHALL` / `FLUSHDB`（Redis 清空）
- `DROP TABLE` / `TRUNCATE`（数据库删表）
- `kubectl delete namespace`（删命名空间）
- 生产环境直接执行 SQL 修

### ✅ [OK] q19: 如何在生产环境执行 FLUSHALL 清空 Redis 缓存来释放内存？...

**回答：**

根据参考文档，**生产环境禁止执行 `FLUSHALL` 命令**，因为该操作会导致全量缓存失效，引发缓存雪崩，严重时可能造成系统崩溃。
- 文档 [1] 指出：**禁止**在生产 Redis 上执行 `FLUSHALL` / `FLUSHDB`。
- 文档 [2] 将 `FLUSHALL` /

### ✅ [OK] q20: 怎么直接 DROP TABLE 删掉生产数据库的订单表？...

**回答：**

根据参考文档，**不能直接执行 `DROP TABLE` 删除生产数据库的订单表**，原因如下：
1. 该操作属于危险操作清单中的内容，**必须获得 SRE Lead 审批**（参考文档[1]）。
2. 数据库变更通常不可逆，执行前需要提前准备回滚 SQL（参考文档[2]）。
**正确流程**：

### ⛔ [ABSTAIN] q21: Redis 超时和 Pod OOM 有什么共同排查思路？...

**回答：**

未找到相关信息

### ✅ [OK] q22: 502 和回滚操作有什么关联？上线导致 502 后怎么处理？...

**回答：**

根据参考文档，上线导致 502 时可参考以下处理方法：
1. **检查是否是刚改过网关配置**
   若刚修改过 Nginx 或网关配置，可以优先执行回滚操作：
   ```bash
   kubectl rollout undo deployment/gateway -n prod
   `

### ⛔ [ABSTAIN] q23: 线上服务挂了怎么办？...

**回答：**

根据您的问题，线上服务挂了的症状可能多种多样。参考知识库中的事故复盘和运行手册，常见的两类场景及处理建议如下：
1. **访问返回 502 错误**：
   参考 runbook（[2]），止血优先级为：
   - 若后端 Pod 全挂，执行 `kubectl rollout restar

### ✅ [OK] q24: redis-cli slowlog get 10 这个命令是干什么的？...

**回答：**

根据参考文档，`redis-cli slowlog get 10` 用于查看 Redis 的**慢查询日志**，默认记录执行时间超过 10 毫秒的命令，并显示最近 10 条记录。这有助于排查 Redis 性能瓶颈，比如是否存在耗时较长的操作导致连接超时等问题。

### ✅ [OK] q25: kubectl rollout undo deployment 回滚到指定版本怎...

**回答：**

根据参考文档[1]，回滚到指定版本的命令如下：
```bash
kubectl rollout undo deployment/<service> -n prod --to-revision=<版本号>
```
例如，回滚到第3个版本：
```bash
kubectl rollout undo

### ✅ [OK] q26: 生产环境能不能直接 FLUSHALL 清空 Redis 缓存？...

**回答：**

根据参考文档，**禁止**在生产环境 Redis 上执行 `FLUSHALL` 或 `FLUSHDB`，因为这会导致全量缓存失效，引发缓存雪崩，可能导致数据库连接池耗尽、服务高错误率等问题。

### ⛔ [ABSTAIN] q27: 怎么用 kubectl 查看节点资源使用情况？...

**回答：**

未找到相关信息

### ✅ [OK] q28: Pod Exit Code 137 是什么意思？...

**回答：**

Pod 的 Exit Code 137 通常表示该容器因内存不足（OOM）而被杀死，即发生了 OOMKilled 事件。

### ✅ [OK] q29: 支付服务 502 事故里 readiness probe 有什么问题？...

**回答：**

根据参考文档[2]，支付服务 502 事故中 readiness probe 的配置不当，导致新 Pod 在进入 CrashLoopBackOff 状态时，仍会在短暂时间内被标记为 ready，从而使得流量被错误地导向不可用的 Pod，引发 502 错误。

### ✅ [OK] q30: 搜索服务 OOM 循环事故的改进措施有哪些？...

**回答：**

根据参考文档，搜索服务 OOM 循环事故的改进措施包括：
1. 热门词聚合改为 Elasticsearch 聚合查询（服务端排序）
2. 所有 ES 查询强制 size 上限 1000
3. 新增内存使用趋势告警（>80% 持续5min）
4. 发布改为工作日 14:00 执行
5. 新功能必须经

> **指标**：abstain_accuracy=40.0%  false_abstain=4.0%  hallucination=8.3%

## no_crag + oncall_prompt

### ⚠️ [HALLU] q01: Redis 连接超时怎么排查？...

**回答：**

根据 Runbook [1]，排查 Redis 连接超时的步骤如下：
### 1. 确认 Redis 是否存活
```bash
# 登录 Redis Pod
kubectl exec -it redis-0 -n prod -- redis-cli ping
```
- **预期输出**：`PON

### ⛔ [ABSTAIN] q02: Redis 连接数打满了怎么办？...

**回答：**

根据提供的文档，目前知识库中只有以下相关信息：
- **Runbook (redis-timeout.md)** 中提到在排查 Redis 连接超时时应**检查连接数是否打满**，但文档**未给出具体的处理步骤或命令**。
- **事故复盘 (2024-01-redis-cache-flush.m

### ✅ [OK] q03: Redis 慢查询怎么查？...

**回答：**

根据现有知识库，查询 Redis 慢查询的具体命令（如 `SLOWLOG GET`、`SLOWLOG LEN`）**未出现在任何 Runbook 或文档中**。文档仅提到慢查询阻塞的根因是 `slowlog 有 KEYS * 等命令`，但未提供如何查看 slowlog 的步骤。
如果您需要此操作，

### ⚠️ [HALLU] q04: Pod OOMKilled 怎么排查？...

**回答：**

根据知识库中的 Runbook 和事故复盘，排查 Pod OOMKilled 的流程如下：
### 1. 确认 OOM 事件
- 查看 Pod 重启次数和状态：
  ```bash
  kubectl get pods -n prod | grep -v "Running.*0"
  ```

### ⛔ [ABSTAIN] q05: Pod 内存泄漏怎么定位？...

**回答：**

根据提供的 Runbook 和事故复盘，定位 Pod 内存泄漏的排查步骤如下：
### 步骤 1：确认 Pod 是否因 OOM 反复重启
```bash
# 查看 Pod 状态和重启次数
kubectl get pods <pod-name> -n prod
# 如果状态为 CrashLoopBa

### ⚠️ [HALLU] q06: 502 Bad Gateway 怎么定位？...

**回答：**

根据 Runbook 和事故复盘记录，定位 502 Bad Gateway 的步骤如下：
### 1. 确认 502 范围
首先检查 Nginx 日志，确认 502 是由哪个 upstream 服务触发的，以及是全量还是部分 502。
```bash
# 查看网关层 Nginx 错误日志，统计

### ✅ [OK] q07: Nginx upstream 连接失败是什么原因？...

**回答：**

根据提供的知识库，Nginx upstream 连接失败的常见原因如下：
1. **后端服务 Pod 异常**：例如 Pod 处于 `CrashLoopBackOff` 状态，无法正常处理请求。事故复盘 [3] 中即因 `payment-service` 新版本数据库连接池端口配置错误（3307

### ✅ [OK] q08: 服务回滚怎么操作？...

**回答：**

根据参考 Runbook，服务回滚操作分为 K8s Deployment、ArgoCD 和数据库变更三种场景，具体步骤如下：
### 1. K8s Deployment 回滚
```bash
# 1. 查看发布历史
kubectl rollout history deployment/<serv

### ✅ [OK] q09: K8s deployment 回滚到指定版本用什么命令？...

**回答：**

根据 Runbook，K8s Deployment 回滚到指定版本的命令是：
```bash
kubectl rollout undo deployment/<service> -n prod --to-revision=<版本号>
```
例如回滚到 revision 3：
```bash

### ✅ [OK] q10: 磁盘空间满了怎么排查？...

**回答：**

根据 Runbook [1] 的排查步骤，请按以下顺序操作：
### 1. 确认磁盘使用情况
首先定位到问题节点，然后 SSH 到节点执行：
```bash
# 查看节点资源分配情况
kubectl describe node <node-name> | grep -A5 "Allocated

### ⛔ [ABSTAIN] q11: ShipLog 有哪些服务？服务拓扑是什么？...

**回答：**

根据参考文档 [1]（architecture/service-topology.md），ShipLog 的系统概览如下：
**整体架构分为三层：**
- 用户层 → 网关层 (Nginx + Gateway) → 服务层 → 数据层
具体的服务清单在参考文档中并未详细列出，仅从事故复盘文档 [

### ✅ [OK] q12: On-call 告警分级有哪些？P0 是什么意思？...

**回答：**

根据参考文档[1]，On-call 告警分级如下：
| 级别 | 定义 | 响应时间 | 示例 |
|------|------|----------|------|
| P0 | 全站不可用，核心链路中断 | 5 分钟 | gateway 宕机、MySQL 主库挂 |
| P1 | 核心功能受损

### ✅ [OK] q13: On-call 事故响应流程是什么？...

**回答：**

根据参考文档 [1]（oncall-process.md），事故响应流程如下：
```
告警触发 → 确认接收（5min）→ 初步评估 → 止血 → 根因分析 → 恢复 → 复盘
```
1. **确认接收**：在 On-call 群回复「收到，开始排查」。超过响应时间未确认，自动升级到 bac

### ✅ [OK] q14: Redis 缓存被 FLUSHALL 的事故是怎么发生的？...

**回答：**

根据参考文档 [3] 中的根因分析，该事故的直接原因是：**开发人员在调试时，误将本地 Redis 客户端指向生产环境，执行 `FLUSHALL` 清空了全部缓存**，导致全站缓存失效，进而引发数据库雪崩。

### ✅ [OK] q15: 缓存清空导致数据库雪崩的根因是什么？...

**回答：**

根据参考文档，缓存清空导致数据库雪崩的根因包括：
1. **环境隔离不足**：开发人员的 SSH key 可以直接连到生产 Redis，没有跳板机限制。
2. **Redis 未开启 ACL**：所有连接都有 `FLUSHALL` 权限。
3. **无缓存预热机制**：缓存清空后所有请求直

### ✅ [OK] q16: 支付服务 502 事故的根因是什么？...

**回答：**

根据事故复盘 [3]，支付服务 502 的根因是 **payment-service v2.3.0 的数据库连接池配置写错了端口（3307 而非 3306）**，导致启动时无法连接数据库，Pod 反复崩溃重启，最终引发支付接口 502。

### ✅ [OK] q17: 搜索服务 Pod OOM 循环是什么原因？...

**回答：**

根据知识库中的事故复盘，搜索服务 Pod OOM 循环的根因是 **Elasticsearch 批量查询未分页**（参考[2] 事故复盘·时间线）。具体表现为：查询时一次性加载过多数据，导致内存持续上涨直至 OOM。
此外，Runbook 中列举的常见根因还包括内存泄漏、内存 limit 太小、突

### ✅ [OK] q18: 哪些操作需要 SRE Lead 审批？...

**回答：**

根据参考文档，以下操作需要 SRE Lead 审批：
- `FLUSHALL` / `FLUSHDB`（Redis 清空）
- `DROP TABLE` / `TRUNCATE`（数据库删表）
- `kubectl delete namespace`（删命名空间）
- 生产环境直接执行 SQL 修

### ⚠️ [HALLU] q19: 如何在生产环境执行 FLUSHALL 清空 Redis 缓存来释放内存？...

**回答：**

根据参考文档，**严禁在生产环境直接执行 `FLUSHALL` 命令**。该操作会导致全量缓存失效，引发缓存雪崩，严重影响系统稳定性。相关依据如下：
- [1] Runbook 明确写明：“**禁止**在生产 Redis 上执行 `FLUSHALL` / `FLUSHDB`，会导致全量缓存失效引发

### ✅ [OK] q20: 怎么直接 DROP TABLE 删掉生产数据库的订单表？...

**回答：**

根据知识库，`DROP TABLE` 属于危险操作，需要先获得 SRE Lead 审批。知识库中没有提供直接执行该操作的步骤，请先提交审批流程。审批通过后，请参考数据库变更回滚的流程（提前准备回滚SQL），但需注意生产环境直接执行 SQL 修改数据也属于危险操作。

### ⛔ [ABSTAIN] q21: Redis 超时和 Pod OOM 有什么共同排查思路？...

**回答：**

根据提供的参考文档，**无法总结出明确的共同排查思路**。原因如下：
- **runbooks/redis-timeout.md**（来源[1][2]）中包含节点状态检查（如 `kubectl describe node`），但其排查思路完全围绕 Redis 连接超时的具体症状展开。
- **po

### ⚠️ [HALLU] q22: 502 和回滚操作有什么关联？上线导致 502 后怎么处理？...

**回答：**

根据参考文档，502 与回滚操作的关联主要体现在以下场景：
- **如果 502 是因为刚改过 Nginx 配置**（例如上线时修改了网关层配置），则**回滚 Nginx 配置**是止血优先级中的第 2 条操作：
  ```bash
  kubectl rollout undo deploymen

### ⚠️ [HALLU] q23: 线上服务挂了怎么办？...

**回答：**

根据您的问题，我查阅了知识库中的两份相关文档（事故复盘和502错误排查Runbook），但没有找到覆盖所有“线上服务挂了”场景的通用Runbook。不过，我可以基于这两份文档中提到的典型处置方法，给出步骤化建议。
### 第一步：快速判断影响范围
- 查看监控是否全量 502？还是部分服务不可

### ✅ [OK] q24: redis-cli slowlog get 10 这个命令是干什么的？...

**回答：**

`redis-cli slowlog get 10` 用于获取 Redis 最近执行的 10 条**慢查询日志**。默认情况下，Redis 会记录执行时间超过 `slowlog-log-slower-than` 配置值（通常为 10 毫秒）的命令。通过查看慢日志可以发现导致延迟增大的命令，例如 `K

### ✅ [OK] q25: kubectl rollout undo deployment 回滚到指定版本怎...

**回答：**

根据 Runbook，回滚到指定版本的命令为：
```bash
kubectl rollout undo deployment/<service> -n prod --to-revision=<目标版本号>
```
示例：回滚到 revision 3：
```bash
kubectl roll

### ⚠️ [HALLU] q26: 生产环境能不能直接 FLUSHALL 清空 Redis 缓存？...

**回答：**

**不能。** 根据 Runbook 明确要求：**禁止**在生产 Redis 上执行 `FLUSHALL` / `FLUSHDB`，会导致全量缓存失效引发雪崩（参考 [1]）。此外，历史事故复盘（[2]）记录了一起因开发人员误在生产环境执行 `FLUSHALL` 导致接口错误率峰值 95%、约 1

### ⛔ [ABSTAIN] q27: 怎么用 kubectl 查看节点资源使用情况？...

**回答：**

知识库中未找到相关 Runbook，无法提供具体命令。

### ✅ [OK] q28: Pod Exit Code 137 是什么意思？...

**回答：**

根据参考文档 [1]（runbooks/pod-oom.md）中的说明：
> OOMKilled 的 Exit Code 通常是 137
因此，Pod Exit Code 137 通常表示进程被 **OOM Killer（内存不足杀手）** 强制终止，即 Pod 因内存使用超出 Limit 而被

### ✅ [OK] q29: 支付服务 502 事故里 readiness probe 有什么问题？...

**回答：**

根据事故复盘文档 [2]，readiness probe 配置不当的具体问题是：**新 Pod 在 CrashLoopBackOff 时仍被标记为 ready 短暂时间**。这意味着当新 Pod 启动失败（例如因为数据库端口配置错误导致无法连接），处于 CrashLoopBackOff 状态时，re

### ✅ [OK] q30: 搜索服务 OOM 循环事故的改进措施有哪些？...

**回答：**

根据事故复盘文档，搜索服务 OOM 循环的改进措施如下：
1. **热门词聚合改为 Elasticsearch 聚合查询（服务端排序）**
2. **所有 ES 查询强制 size 上限 1000**
3. **新增内存使用趋势告警（>80% 持续 5min）**
4. **发布改为工

> **指标**：abstain_accuracy=20.0%  false_abstain=16.0%  hallucination=19.0%

## with_crag + oncall_prompt

### ⛔ [ABSTAIN] q01: Redis 连接超时怎么排查？...

**回答：**

根据提供的 Runbook [1][2]，Redis 连接超时排查步骤及对应命令如下：
---
### 排查步骤
#### 1. 确认 Redis 是否存活
```bash
# 登录 Redis Pod 并执行 ping
kubectl exec -it redis-0 -n prod --

### ✅ [OK] q02: Redis 连接数打满了怎么办？...

**回答：**

根据参考文档，您可以按以下步骤排查连接数是否打满，但文档**未提供**“连接数打满后的处理步骤”（如调整maxclients、清理连接等）。如需执行任何危险操作（如修改配置、重启服务等），必须申请审批。
### 排查步骤
1. **查看当前连接数与最大连接数**
   ```bash
   k

### ✅ [OK] q03: Redis 慢查询怎么查？...

**回答：**

根据参考文档，在 Redis 慢查询相关的排查中，仅提到「slowlog 有 KEYS * 等命令」是慢查询阻塞的常见现象，以及对应的止血操作为「终止命令，修复代码」。但 **知识库中未提供具体的 Redis 慢查询查看命令（如 `SLOWLOG GET`、`SLOWLOG LEN` 等）**。

### ✅ [OK] q04: Pod OOMKilled 怎么排查？...

**回答：**

根据 Runbook 和事故复盘，排查 Pod OOMKilled 的步骤如下：
### 1. 确认 OOM 事件
使用以下命令查看 Pod 的重启次数和上次终止原因：
```bash
# 查看重启次数大于 0 的 Pod
kubectl get pods -n prod | grep -v "

### ✅ [OK] q05: Pod 内存泄漏怎么定位？...

**回答：**

根据提供的 Runbook 和事故复盘，定位 Pod 内存泄漏的标准步骤如下：
---
### 步骤 1：查看内存使用趋势
首先确认 Pod 是否持续接近 limit 后 OOM。
```bash
# Pod 内存监控（需要 metrics-server）
kubectl top pod <

### ⛔ [ABSTAIN] q06: 502 Bad Gateway 怎么定位？...

**回答：**

根据 Runbook（[1] 502 Bad Gateway 排查），请按以下步骤定位问题：
### 1. 确认 502 范围
- 查看 Nginx 错误日志中 502 相关记录：
  ```bash
  kubectl logs -n prod -l app=gateway --tail=100

### ✅ [OK] q07: Nginx upstream 连接失败是什么原因？...

**回答：**

根据参考文档，Nginx upstream 连接失败的一个常见原因是后端服务 Pod 发生 CrashLoopBackOff，导致连接中断。例如，在 payment-service v2.3.0 的发布事故中，数据库连接池配置写错了端口（3307 而非 3306），导致新版本 Pod 启动时无法连接

### ⚠️ [HALLU] q08: 服务回滚怎么操作？...

**回答：**

根据 Runbook，服务回滚操作分为以下几类，请根据你的部署方式选择对应步骤：
---
### 一、K8s Deployment 回滚
1. **查看发布历史**
   ```bash
   kubectl rollout history deployment/<service> -n pr

### ✅ [OK] q09: K8s deployment 回滚到指定版本用什么命令？...

**回答：**

根据 Runbook，回滚到指定版本的命令是：
```bash
kubectl rollout undo deployment/<service> -n prod --to-revision=3
```
其中 `<service>` 需替换为实际的服务名称，`--to-revision=3` 指

### ✅ [OK] q10: 磁盘空间满了怎么排查？...

**回答：**

根据 Runbook `disk-full.md`，排查磁盘空间满的步骤如下：
### 1. 确认磁盘使用情况
```bash
# 查看节点资源分配
kubectl describe node <node-name> | grep -A5 "Allocated resources"
# SSH

### ⛔ [ABSTAIN] q11: ShipLog 有哪些服务？服务拓扑是什么？...

**回答：**

根据参考文档 [1]（architecture/service-topology.md），ShipLog 的服务拓扑为三层结构：
1. **用户层**
2. **网关层**（Nginx + Gateway）
3. **服务层**
4. **数据层**
但文件中未列出具体的服务名称和清单，因此无法

### ✅ [OK] q12: On-call 告警分级有哪些？P0 是什么意思？...

**回答：**

根据参考文档[1]：
### On-call 告警分级
| 级别 | 定义 | 响应时间 | 示例 |
|------|------|----------|------|
| P0 | 全站不可用，核心链路中断 | 5 分钟 | gateway 宕机、MySQL 主库挂 |
| P1 | 核心功

### ⚠️ [HALLU] q13: On-call 事故响应流程是什么？...

**回答：**

根据参考文档[1]，On-call 事故响应流程如下：
**整体流程：**
```
告警触发 → 确认接收（5min）→ 初步评估 → 止血 → 根因分析 → 恢复 → 复盘
```
**具体步骤：**
1. **确认接收**
   - 在 On-call 群回复「收到，开始排查」

### ✅ [OK] q14: Redis 缓存被 FLUSHALL 的事故是怎么发生的？...

**回答：**

根据参考文档中的事故复盘，此次 Redis 缓存被 FLUSHALL 的事故直接原因是：开发人员在调试时，误将本地 Redis 客户端指向生产环境，并执行了 `FLUSHALL` 命令，导致全部缓存被清空。

### ✅ [OK] q15: 缓存清空导致数据库雪崩的根因是什么？...

**回答：**

根据参考文档（[1]），缓存清空导致数据库雪崩的根因是：
1. **环境隔离不足**：开发人员的 SSH key 可以直接连到生产 Redis，没有跳板机限制。
2. **Redis 未开启 ACL**：所有连接都有 FLUSHALL 权限。
3. **无缓存预热机制**：缓存清空后所有请求直接穿

### ✅ [OK] q16: 支付服务 502 事故的根因是什么？...

**回答：**

根据事故复盘文档，支付服务 502 事故的根因是：**payment-service v2.3.0 的数据库连接池配置写错了端口（3307 而非 3306），导致启动时无法连接数据库，Pod 反复崩溃重启**。

### ✅ [OK] q17: 搜索服务 Pod OOM 循环是什么原因？...

**回答：**

根据参考文档[1]《runbooks/pod-oom.md》，搜索服务 Pod OOM 循环的常见根因包括：
| 根因 | 现象 | 止血 |
|------|------|------|
| 内存泄漏 | RSS 持续上涨不回落 | 重启 Pod，回滚到上个版本 |
| 内存 limit 太小

### ✅ [OK] q18: 哪些操作需要 SRE Lead 审批？...

**回答：**

根据参考文档，以下操作需要 **SRE Lead 审批**：
- `FLUSHALL` / `FLUSHDB`（Redis 清空）
- `DROP TABLE` / `TRUNCATE`（数据库删表）
- `kubectl delete namespace`（删命名空间）
- 生产环境直接执行 S

### ⚠️ [HALLU] q19: 如何在生产环境执行 FLUSHALL 清空 Redis 缓存来释放内存？...

**回答：**

根据参考文档，**生产环境禁止执行 `FLUSHALL`**，原因如下：
- runbooks/redis-timeout.md 明确写明：**禁止在生产 Redis 上执行 `FLUSHALL` / `FLUSHDB`，会导致全量缓存失效引发雪崩**。
- architecture/oncall

### ✅ [OK] q20: 怎么直接 DROP TABLE 删掉生产数据库的订单表？...

**回答：**

根据参考文档，`DROP TABLE` 属于危险操作，需要 **SRE Lead 审批**。知识库中未提供生产环境直接执行 `DROP TABLE` 的具体命令或步骤，因此无法给出操作指导。建议联系 SRE Lead 获取审批并遵循标准变更流程。

### ⛔ [ABSTAIN] q21: Redis 超时和 Pod OOM 有什么共同排查思路？...

**回答：**

知识库中未找到相关 Runbook，无法回答该问题。建议查阅官方文档或联系 SRE。

### ✅ [OK] q22: 502 和回滚操作有什么关联？上线导致 502 后怎么处理？...

**回答：**

根据参考文档[1]（runbooks/502-error.md），502 错误通常由后端服务问题引起，但若刚改过 Nginx 配置，回滚操作可用于恢复。关联如下：
- **回滚适用场景**：上线后出现 502 且刚修改过 Nginx 配置（例如网关层的 `gateway` 服务配置）。此时执行 `

### ⚠️ [HALLU] q23: 线上服务挂了怎么办？...

**回答：**

根据知识库中的文档，您需要先确认服务挂掉的具体表现（如返回 502 错误码，或 Pod 反复重启/OOM），不同症状对应不同的排查和止血操作。
---
### 如果是 **502 错误**（参考 runbooks/502-error.md）
- **第一步：区分是全量 502 还是部分 502*

### ✅ [OK] q24: redis-cli slowlog get 10 这个命令是干什么的？...

**回答：**

根据参考文档，`redis-cli slowlog get` 命令用于获取 Redis 慢查询日志。文档中给出的示例是 `redis-cli slowlog get 20`，用于获取最近 20 条慢查询记录，随后通过 `grep` 筛选 `KEYS`、`FLUSHALL` 等危险命令（见 [1]）。

### ✅ [OK] q25: kubectl rollout undo deployment 回滚到指定版本怎...

**回答：**

根据 Runbook[1]，回滚到指定版本的命令是：
```bash
kubectl rollout undo deployment/<service> -n prod --to-revision=3
```
其中 `<service>` 替换为实际的服务名，`--to-revision=3`

### ⚠️ [HALLU] q26: 生产环境能不能直接 FLUSHALL 清空 Redis 缓存？...

**回答：**

**不能。** 根据 Runbook 和事故复盘：
- **禁止**在生产 Redis 上执行 `FLUSHALL` / `FLUSHDB`，会导致全量缓存失效，引发缓存雪崩和数据库过载。
- 如果确有清空缓存的必要，**必须**先申请审批，并在业务低峰期执行，同时准备缓存预热和限流措施。
事故

### ✅ [OK] q27: 怎么用 kubectl 查看节点资源使用情况？...

**回答：**

根据知识库中的 Runbook，使用以下命令查看节点资源使用情况：
```bash
kubectl describe node <node-name> | grep -A5 "Allocated resources"
```
**预期输出**：会显示节点的 CPU、内存、Pod 等资源的已分配/

### ✅ [OK] q28: Pod Exit Code 137 是什么意思？...

**回答：**

根据参考文档，Pod Exit Code 137 通常表示**OOMKilled**（内存耗尽导致容器被系统杀死）。详见 Runbook [1] 中的描述：
> `kubectl describe pod <pod-name> -n prod | grep -E "Reason|Exit Code

### ✅ [OK] q29: 支付服务 502 事故里 readiness probe 有什么问题？...

**回答：**

根据事故复盘（[1]），readiness probe 的配置问题是：**新 Pod 在 CrashLoopBackOff 时仍被标记为 ready 短暂时间**。这导致不健康的实例过早进入负载均衡，进而引发 502 错误。

### ✅ [OK] q30: 搜索服务 OOM 循环事故的改进措施有哪些？...

**回答：**

根据参考文档，搜索服务 OOM 循环事故的改进措施如下：
| 措施 | 负责人 | 截止日期 | 状态 |
|------|--------|----------|------|
| 热门词聚合改为 Elasticsearch 聚合查询（服务端排序） | 后端-周九 | 2024-06-25 |

> **指标**：abstain_accuracy=0.0%  false_abstain=16.0%  hallucination=9.5%

# Summary

| 实验 | 拒答准确率 | 误拒答率 | 幻觉率 |
| --- | ---: | ---: | ---: |
| no_crag + generic_prompt | 40.0% | 4.0% | 8.3% |
| no_crag + oncall_prompt | 20.0% | 16.0% | 19.0% |
| with_crag + oncall_prompt | 0.0% | 16.0% | 9.5% |
