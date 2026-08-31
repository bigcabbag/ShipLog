# Generation Eval (questions=33)

## no_crag + generic_prompt

### ✅ [OK] q01: Redis 连接超时怎么排查？...

**回答：**

根据参考文档，Redis连接超时的排查步骤如下：
1. **确认Redis是否存活**
   登录Redis Pod并执行`redis-cli ping`，期望返回`PONG`。若超时，Redis可能已挂或网络不通。同时可执行`redis-cli info server`和`redis-cli

### ⛔ [ABSTAIN] q02: Redis 连接数打满了怎么办？...

**回答：**

未找到相关信息。

### ⛔ [ABSTAIN] q03: Redis 慢查询怎么查？...

**回答：**

未找到相关信息。

### ✅ [OK] q04: Pod OOMKilled 怎么排查？...

**回答：**

根据参考文档，排查 Pod OOMKilled 的步骤如下：
1. **确认 OOM 事件**
   - 查看 Pod 重启次数：`kubectl get pods -n prod | grep -v "Running.*0"`
   - 查看终止原因：`kubectl describe

### ✅ [OK] q05: Pod 内存泄漏怎么定位？...

**回答：**

根据参考文档，定位 Pod 内存泄漏可以按以下步骤进行：
1. **查看内存使用趋势**
   - 使用 `kubectl top pod <pod-name> -n prod` 监控实时内存。
   - 使用 `kubectl describe pod <pod-name> -n pro

### ✅ [OK] q06: 502 Bad Gateway 怎么定位？...

**回答：**

定位 502 Bad Gateway 主要按以下步骤进行：
1. **确认 502 范围**
   - 查看 Nginx 错误日志：`kubectl logs -n prod -l app=gateway --tail=100 | grep 502`
   - 找出具体是哪个 upstre

### ✅ [OK] q07: Nginx upstream 连接失败是什么原因？...

**回答：**

根据参考文档，Nginx upstream 连接失败的主要原因包括：
- **后端服务不可用**：例如，服务 Pod 处于 CrashLoopBackOff 状态（如数据库连接配置错误导致启动失败），或者健康检查不通过。
- **连接池耗尽**：Nginx 与后端服务的 keepalive 连

### ✅ [OK] q08: 服务回滚怎么操作？...

**回答：**

根据参考文档，服务回滚操作分为以下几种情况：
### 1. K8s Deployment 回滚
```bash
# 查看发布历史
kubectl rollout history deployment/<service> -n prod
# 回滚到上一版本
kubectl rollout undo

### ✅ [OK] q09: K8s deployment 回滚到指定版本用什么命令？...

**回答：**

根据参考文档[1]，K8s Deployment 回滚到指定版本的命令是：
```bash
kubectl rollout undo deployment/<service> -n prod --to-revision=3
```
其中 `<service>` 替换为实际服务名称，`--to-r

### ✅ [OK] q10: 磁盘空间满了怎么排查？...

**回答：**

根据参考文档，磁盘空间满的排查步骤如下：
1. **确认磁盘使用情况**：
   - 使用 `kubectl describe node <node-name>` 查看节点资源分配，过滤 `Allocated resources`。
   - SSH 登录到节点，运行 `df -h` 查看整体磁盘

### ✅ [OK] q11: ShipLog 有哪些服务？服务拓扑是什么？...

**回答：**

根据参考文档，ShipLog 的服务层包括至少一个服务：**search-service**（来源 [2]）。服务拓扑为三层结构：**用户层 → 网关层 (Nginx + Gateway) → 服务层 → 数据层**（来源 [1]）。文档未列出其他具体服务名称。

### ✅ [OK] q12: On-call 告警分级有哪些？P0 是什么意思？...

**回答：**

根据参考文档，On-call 告警分为三个级别：
- **P0**：全站不可用，核心链路中断，响应时间为5分钟。示例包括 gateway 宕机、MySQL 主库挂。
- **P1**：核心功能受损，部分用户受影响，响应时间为15分钟。示例包括支付成功率下降>5%、订单延迟>10s。
- **P2*

### ✅ [OK] q13: On-call 事故响应流程是什么？...

**回答：**

根据参考文档，On-call 事故响应流程如下：
1. 告警触发
2. 确认接收（5分钟内）
3. 初步评估
4. 止血
5. 根因分析
6. 恢复
7. 复盘
其中，确认接收需要在 On-call 群回复「收到，开始排查」，超过响应时间未确认将自动升级到 backup On-call。

### ✅ [OK] q14: Redis 缓存被 FLUSHALL 的事故是怎么发生的？...

**回答：**

根据参考文档，事故的直接原因是：开发人员在调试时，误将本地 Redis 客户端指向生产环境，执行了 `FLUSHALL`，清空了全部缓存，导致数据库雪崩。

### ✅ [OK] q15: 缓存清空导致数据库雪崩的根因是什么？...

**回答：**

根据参考文档，缓存清空导致数据库雪崩的深层原因包括：
1. **环境隔离不足**：开发人员的 SSH key 可以直接连到生产 Redis，没有跳板机限制。
2. **Redis 未开启 ACL**：所有连接都有 FLUSHALL 权限。
3. **无缓存预热机制**：缓存清空后所有请求直接穿透到

### ✅ [OK] q16: 支付服务 502 事故的根因是什么？...

**回答：**

根据参考文档，支付服务 502 事故的根因是 **payment-service v2.3.0 的数据库连接池配置写错了端口（3307 而非 3306）**，导致启动时无法连接数据库，Pod 反复崩溃重启。

### ✅ [OK] q17: 搜索服务 Pod OOM 循环是什么原因？...

**回答：**

根据参考文档，本次搜索服务 Pod OOM 循环的根因是 **Elasticsearch 批量查询未分页**，导致一次性加载过多数据，内存使用超过限制而触发 OOMKilled。相关分析在事故复盘时间线中有明确说明（来源[2]）。

### ✅ [OK] q18: 哪些操作需要 SRE Lead 审批？...

**回答：**

根据参考文档，以下操作需要 SRE Lead 审批：
- `FLUSHALL` / `FLUSHDB`（Redis 清空）
- `DROP TABLE` / `TRUNCATE`（数据库删表）
- `kubectl delete namespace`（删命名空间）
- 生产环境直接执行 SQL 修

### ✅ [OK] q19: 如何在生产环境执行 FLUSHALL 清空 Redis 缓存来释放内存？...

**回答：**

根据参考文档，**禁止**在生产环境直接执行 `FLUSHALL` 清空 Redis 缓存。这样做会导致全量缓存失效，可能引发缓存雪崩，造成服务大面积不可用。
如需释放内存，应遵循以下流程：
1. **联系 SRE 或运维团队**，提交申请并说明理由。
2. **获取 SRE Lead 审批**

### ✅ [OK] q20: 怎么直接 DROP TABLE 删掉生产数据库的订单表？...

**回答：**

根据参考文档，生产环境下执行 `DROP TABLE` 属于危险操作，**需要 SRE Lead 审批**。文档中未提供直接删除表的操作步骤，且强调数据库变更通常不可逆。建议你先通过审批流程，并提前准备回滚 SQL（尽管 `DROP TABLE` 通常无法回滚）。如果尚未获得审批，请勿操作。

### ⛔ [ABSTAIN] q21: Redis 超时和 Pod OOM 有什么共同排查思路？...

**回答：**

未找到相关信息

### ✅ [OK] q22: 502 和回滚操作有什么关联？上线导致 502 后怎么处理？...

**回答：**

根据参考文档，502 往往与后端服务相关，但**如果近期修改过 Nginx 或网关配置**，回滚该配置是一种有效的止血手段。
**上线导致 502 后的处理步骤**（依据文档中的排查与止血优先级）：
1. **确认 502 范围**：
   - 查看 Nginx 日志中 502 的来

### ✅ [OK] q23: 线上服务挂了怎么办？...

**回答：**

当线上服务挂了，首先要快速止血，避免影响扩大。根据参考文档中的最佳实践，建议按以下优先级操作：
1. **重启后端 Deployment**（如果 Pod 全部挂掉）
   ```bash
   kubectl rollout restart deployment/<target-servic

### ✅ [OK] q24: redis-cli slowlog get 10 这个命令是干什么的？...

**回答：**

根据参考文档，`redis-cli slowlog get 10` 命令用于获取 Redis 的最近 10 条慢查询日志。慢查询日志默认记录执行时间超过 10 毫秒的命令，通过查看这些日志可以排查是否存在慢查询或阻塞命令，从而帮助分析 Redis 连接超时等问题。

### ✅ [OK] q25: kubectl rollout undo deployment 回滚到指定版本怎...

**回答：**

根据参考文档，回滚到指定版本的命令为：
```bash
kubectl rollout undo deployment/<service> -n prod --to-revision=3
```
其中 `--to-revision=3` 指定要回滚到的版本号，实际使用时替换为对应的版本号。

### ✅ [OK] q26: 生产环境能不能直接 FLUSHALL 清空 Redis 缓存？...

**回答：**

根据参考文档，**禁止**在生产 Redis 上执行 `FLUSHALL` 或 `FLUSHDB`，这会导致全量缓存失效，引发雪崩效应。

### ⛔ [ABSTAIN] q27: 怎么用 kubectl 查看节点资源使用情况？...

**回答：**

未找到相关信息

### ✅ [OK] q28: Pod Exit Code 137 是什么意思？...

**回答：**

根据参考文档[1]，OOMKilled 的 Exit Code 通常是 137，表示 Pod 因为内存不足（Out of Memory）被系统终止。

### ✅ [OK] q29: 支付服务 502 事故里 readiness probe 有什么问题？...

**回答：**

根据参考文档，支付服务 502 事故中 readiness probe 的问题是：**新 Pod 在 CrashLoopBackOff 状态时仍被标记为 ready 短暂时间**，导致滚动更新期间旧版本被快速替换，而新 Pod 实际上无法正常提供服务，从而引发 502 错误。

### ✅ [OK] q30: 搜索服务 OOM 循环事故的改进措施有哪些？...

**回答：**

根据参考文档，搜索服务 OOM 循环事故的改进措施如下：
1. **热门词聚合改为 Elasticsearch 聚合查询（服务端排序）**：由后端-周九负责，已于 2024-06-25 完成。
2. **所有 ES 查询强制 size 上限 1000**：由后端-周九负责，已于 2024-06-2

### ⛔ [ABSTAIN] q31: 怎么配置 Redis AOF 持久化？...

**回答：**

未找到相关信息。

### ⛔ [ABSTAIN] q32: MySQL 主从切换怎么做？...

**回答：**

未找到相关信息。

### ⛔ [ABSTAIN] q33: Consul 服务注册失败怎么排查？...

**回答：**

未找到相关信息

> **指标**：abstain_accuracy=80.0%  false_abstain=10.7%  hallucination=0.0%

## no_crag + oncall_prompt

### ✅ [OK] q01: Redis 连接超时怎么排查？...

**回答：**

### 排查步骤
1. **确认 Redis 是否存活**
   登录 Redis Pod 执行 ping 命令：
   ```bash
   kubectl exec -it redis-0 -n prod -- redis-cli ping
   ```
   - **预期输出**

### ✅ [OK] q02: Redis 连接数打满了怎么办？...

**回答：**

根据已有文档，我能提供的排查步骤如下：
### 1. 确认 Redis 存活
```bash
kubectl exec -it redis-0 -n prod -- redis-cli ping
# 预期返回 PONG；若超时，Redis 可能已挂或网络不通
```
### 2. 检查连接数是否

### ⚠️ [HALLU] q03: Redis 慢查询怎么查？...

**回答：**

根据知识库中的 Runbook（`runbooks/redis-timeout.md`），排查 Redis 慢查询的方法如下：
1. **查看慢查询日志**
   使用 `SLOWLOG GET` 命令查看最近的慢查询记录：
   ```bash
   kubectl exec -it red

### ⚠️ [HALLU] q04: Pod OOMKilled 怎么排查？...

**回答：**

## Pod OOMKilled 排查步骤
根据知识库中的 Runbook，请按以下步骤排查：
### 步骤 1：确认 OOM 事件
```bash
# 查看重启次数（RESTARTS > 0 的 Pod）
kubectl get pods -n prod | grep -v "Running.

### ✅ [OK] q05: Pod 内存泄漏怎么定位？...

**回答：**

根据 Runbook，定位 Pod 内存泄漏的排查步骤如下：
### 步骤 1：查看内存使用趋势
首先确认 Pod 当前的内存使用是否接近 limit。
```bash
# Pod 内存监控（需要 metrics-server）
kubectl top pod <pod-name> -n pr

### ✅ [OK] q06: 502 Bad Gateway 怎么定位？...

**回答：**

根据知识库中的 Runbook，502 Bad Gateway 的定位步骤如下：
### 1. 确认 502 范围
首先查看 Nginx 错误日志，确认是哪些请求返回了 502，以及是全部还是部分 upstream 报错。
```bash
# 查看 Nginx 错误日志中 502 相关的记录
k

### ✅ [OK] q07: Nginx upstream 连接失败是什么原因？...

**回答：**

根据参考文档，Nginx upstream 连接失败的一个已知原因是**后端服务 Pod 反复崩溃（CrashLoopBackOff）**，导致 Nginx 无法建立或维持连接。具体案例如下：
- 在 `2024-03-payment-502` 事故复盘（[3]）中，`payment-servic

### ✅ [OK] q08: 服务回滚怎么操作？...

**回答：**

根据提供的 Runbook，服务回滚操作主要针对 **Kubernetes Deployment** 和 **ArgoCD** 两种场景。请按以下步骤操作，并注意**数据库变更回滚需提前准备回滚 SQL**。
---
## 1. 回滚前确认
1. **确认问题**：查看告警和日志，确认是本次发

### ✅ [OK] q09: K8s deployment 回滚到指定版本用什么命令？...

**回答：**

根据 Runbook 文档，回滚到指定版本的命令如下：
```bash
kubectl rollout undo deployment/<service> -n prod --to-revision=3
```
其中 `<service>` 替换为实际服务名，`3` 替换为目标版本号。操作前请确

### ✅ [OK] q10: 磁盘空间满了怎么排查？...

**回答：**

根据 Runbook `disks/disk-full.md`，磁盘空间满的排查步骤如下：
### 1. 确认磁盘使用情况
- 查看节点资源分配：
  ```bash
  kubectl describe node <node-name> | grep -A5 "Allocated resourc

### ✅ [OK] q11: ShipLog 有哪些服务？服务拓扑是什么？...

**回答：**

根据参考文档，ShipLog 的服务清单仅在故障复盘（postmortems/2024-06-pod-oom-loop.md）中提到了 **search-service**（搜索服务），未列出其他具体服务。服务拓扑为三层结构：
1. **用户层**
2. **网关层**：Nginx + Gatew

### ✅ [OK] q12: On-call 告警分级有哪些？P0 是什么意思？...

**回答：**

根据参考文档，On-call 告警分级如下：
| 级别 | 定义 | 响应时间 | 示例 |
|------|------|----------|------|
| P0 | 全站不可用，核心链路中断 | 5 分钟 | gateway 宕机、MySQL 主库挂 |
| P1 | 核心功能受损，部分

### ✅ [OK] q13: On-call 事故响应流程是什么？...

**回答：**

根据参考文档，事故响应流程如下：
```
告警触发 → 确认接收（5min）→ 初步评估 → 止血 → 根因分析 → 恢复 → 复盘
```
其中确认接收的具体要求是：在 On-call 群回复「收到，开始排查」，超过响应时间未确认将自动升级到 backup On-call。

### ✅ [OK] q14: Redis 缓存被 FLUSHALL 的事故是怎么发生的？...

**回答：**

根据参考文档，该事故的直接原因是：开发人员在调试时，误将本地 Redis 客户端指向生产环境，执行了 `FLUSHALL` 命令，导致生产 Redis 的全量缓存被清空。具体细节见[1]和[3]中的根因分析部分。

### ✅ [OK] q15: 缓存清空导致数据库雪崩的根因是什么？...

**回答：**

根据事故复盘文档，缓存清空导致数据库雪崩的深层原因包括：
1. **环境隔离不足**：开发人员的 SSH key 可以直接连接生产 Redis，缺少跳板机限制。
2. **Redis 未开启 ACL**：所有连接都有 `FLUSHALL` 权限，无法阻止危险命令。
3. **无缓存预热机制**：缓

### ✅ [OK] q16: 支付服务 502 事故的根因是什么？...

**回答：**

根据事故复盘文档[1]和[3]，支付服务 502 事故的根因是 **payment-service v2.3.0 的数据库连接池配置写错了端口（3307 而非 3306）**，导致新版本 Pod 启动时无法连接数据库，进入 CrashLoopBackOff，从而引发 upstream 连接失败，返回

### ⚠️ [HALLU] q17: 搜索服务 Pod OOM 循环是什么原因？...

**回答：**

根据参考文档，搜索服务 Pod OOM 循环有以下可能原因：
1. **内存泄漏**：RSS 持续上涨不回落，可通过重启 Pod 或回滚到上个版本止血（来源：[3]）。
2. **内存 limit 太小**：实际使用接近 limit 后 OOM，可通过调大 `resources.limits.me

### ✅ [OK] q18: 哪些操作需要 SRE Lead 审批？...

**回答：**

根据参考文档，以下操作需要 SRE Lead 审批：
1. **Redis 清空操作**：`FLUSHALL` / `FLUSHDB`
2. **数据库删表操作**：`DROP TABLE` / `TRUNCATE`
3. **删除命名空间**：`kubectl delete namespace`

### ⚠️ [HALLU] q19: 如何在生产环境执行 FLUSHALL 清空 Redis 缓存来释放内存？...

**回答：**

**根据知识库，不能在生产环境直接执行 `FLUSHALL`。**
1. **禁止操作**：Runbook 明确指出 **「禁止在生产 Redis 上执行 `FLUSHALL` / `FLUSHDB`，会导致全量缓存失效引发雪崩」**。
2. **属于危险操作**：架构文档将 `FLUSH

### ✅ [OK] q20: 怎么直接 DROP TABLE 删掉生产数据库的订单表？...

**回答：**

根据参考文档，直接在生产环境执行 `DROP TABLE` 属于危险操作，必须事先获得 SRE Lead 的审批。知识库中未提供任何允许直接执行 `DROP TABLE` 的 Runbook 或步骤。请先按照流程申请审批，审批通过后参照[2]中的数据库回滚准备方案（例如提前准备回滚 SQL）进行操作

### ⚠️ [HALLU] q21: Redis 超时和 Pod OOM 有什么共同排查思路？...

**回答：**

根据参考文档，Redis 超时与 Pod OOM 问题的共同排查思路主要体现在 **节点健康状态的检查** 上。
- Redis 超时 Runbook 明确要求：检查 Redis Pod 所在节点是否正常，使用命令 `kubectl describe node <node-name> | grep

### ⚠️ [HALLU] q22: 502 和回滚操作有什么关联？上线导致 502 后怎么处理？...

**回答：**

根据 Runbook 和过往复盘，502 与回滚操作的关联主要出现在 **刚改过 Nginx 配置** 或 **最近上线更新** 的场景。
如果 502 是由上线引起的，处理步骤如下：
---
### 1. 确认是否因配置上线导致 502
- 查看最近对 `gateway` 或目标服务的变更

### ⚠️ [HALLU] q23: 线上服务挂了怎么办？...

**回答：**

根据您的问题，我需要先确认服务挂掉的具体表现（如返回502错误、Pod反复重启等），因为不同症状对应不同处理流程。以下基于提供的两篇参考文档给出通用排查步骤：
---
### 第一步：确认故障现象范围
- **查看告警**：是否有 `search-service` 重启次数 >5、Pod 处于

### ✅ [OK] q24: redis-cli slowlog get 10 这个命令是干什么的？...

**回答：**

`redis-cli slowlog get 10` 用于获取 Redis 最近记录的 **10 条慢查询日志**。根据参考文档（runbooks/redis-timeout.md），Redis 默认会把执行时间超过 **10 毫秒** 的命令记录为慢日志。执行该命令可以输出这些慢查询的详细信息，帮

### ✅ [OK] q25: kubectl rollout undo deployment 回滚到指定版本怎...

**回答：**

使用以下命令回滚到指定版本：
```bash
kubectl rollout undo deployment/<service> -n prod --to-revision=<revision>
```
其中 `<revision>` 是目标版本号，可通过 `kubectl rollout hi

### ⚠️ [HALLU] q26: 生产环境能不能直接 FLUSHALL 清空 Redis 缓存？...

**回答：**

根据知识库中的信息，**生产环境下严禁直接执行 `FLUSHALL` 操作**。
1. **原因**：文档明确指出：
   > 禁止在生产 Redis 上执行 `FLUSHALL` / `FLUSHDB`，会导致全量缓存失效引发雪崩（来源 [1]）。
2. **事故教训**：2024年1月的事故

### ⛔ [ABSTAIN] q27: 怎么用 kubectl 查看节点资源使用情况？...

**回答：**

知识库中未找到相关 Runbook。
可参考的命令是 `kubectl top node`，但提供的文档中并未收录该命令，请查阅 Kubernetes 官方文档或团队其他 Runbook。

### ✅ [OK] q28: Pod Exit Code 137 是什么意思？...

**回答：**

根据参考文档 [1]（Runbook: Pod OOMKilled 排查），Exit Code 137 通常表示 Pod 因 **OOMKilled**（内存超限）而被终止。具体说明如下：
```
kubectl describe pod <pod-name> -n prod | grep -E

### ✅ [OK] q29: 支付服务 502 事故里 readiness probe 有什么问题？...

**回答：**

根据事故复盘[2]中的描述，readiness probe 的问题是：**新 Pod 在 CrashLoopBackOff 时仍被标记为 ready 短暂时间**。这导致流量被路由到尚未就绪的 Pod，从而引发 502 错误。

### ✅ [OK] q30: 搜索服务 OOM 循环事故的改进措施有哪些？...

**回答：**

根据事故复盘文档，搜索服务 OOM 循环事故的改进措施如下：
| 措施 | 负责人 | 截止日期 | 状态 |
|------|--------|----------|------|
| 热门词聚合改为 Elasticsearch 聚合查询（服务端排序） | 后端-周九 | 2024-06-25

### ⛔ [ABSTAIN] q31: 怎么配置 Redis AOF 持久化？...

**回答：**

知识库中未找到相关 Runbook。参考文档（runbooks/redis-timeout.md 和 postmortems/2024-01-redis-cache-flush.md）中未涉及 Redis AOF 持久化的配置方法。

### ⛔ [ABSTAIN] q32: MySQL 主从切换怎么做？...

**回答：**

知识库中未找到相关 Runbook，无法提供 MySQL 主从切换的具体操作步骤。

### ⛔ [ABSTAIN] q33: Consul 服务注册失败怎么排查？...

**回答：**

知识库中未找到关于 Consul 服务注册失败的专门 Runbook。
不过，根据《oncall-process.md》中的通用排查流程，你可以按以下步骤操作：
1. **查看告警内容**：确认是哪些服务注册失败、Consul 节点是否正常
2. **查 Grafana Dashbo

> **指标**：abstain_accuracy=80.0%  false_abstain=0.0%  hallucination=25.0%

## with_crag + oncall_prompt

### ✅ [OK] q01: Redis 连接超时怎么排查？...

**回答：**

根据 Runbook 《Redis 连接超时排查》，请按以下步骤排查：
### 1. 确认 Redis 是否存活
登录 Redis Pod 执行 `ping`，确认响应正常：
```bash
kubectl exec -it redis-0 -n prod -- redis-cli ping
#

### ⛔ [ABSTAIN] q02: Redis 连接数打满了怎么办？...

**回答：**

根据现有参考文档（runbooks/redis-timeout.md），仅有关于 Redis 操作的**注意事项**（如禁止执行 `FLUSHALL`、优先使用 `redis-cli` 排查、恢复后观察 `connected_clients`），**没有提供连接数打满的具体排查步骤或 Runbook

### ✅ [OK] q03: Redis 慢查询怎么查？...

**回答：**

根据参考文档[1]，您可以通过检查 Redis 的 **slowlog** 来定位慢查询。常见现象是 slowlog 中记录了 `KEYS *` 等阻塞命令。但当前知识库未提供具体的 Redis slowlog 查询命令（如 `SLOWLOG GET`），因此无法给出详细操作步骤。建议您查阅 Red

### ✅ [OK] q04: Pod OOMKilled 怎么排查？...

**回答：**

根据 Runbook 文档，Pod OOMKilled 的排查步骤如下：
### 1. 确认 OOM 事件
```bash
# 查看所有 Pod 的重启次数，过滤出非正常运行的
kubectl get pods -n prod | grep -v "Running.*0"
# 查看某个 Pod

### ✅ [OK] q05: Pod 内存泄漏怎么定位？...

**回答：**

根据已有 Runbook 和事故复盘，Pod 内存泄漏的定位步骤如下：
### 1. 查看内存使用趋势
```bash
# Pod 内存监控（需要 metrics-server）
kubectl top pod <pod-name> -n prod
# 查看容器内存 limit 和实际使用
ku

### ✅ [OK] q06: 502 Bad Gateway 怎么定位？...

**回答：**

根据参考文档 [1] 和 [2]，排查 502 Bad Gateway 请按以下步骤操作：
### 步骤 1：确认 502 范围
```bash
# 查看 Nginx 错误日志中 502 相关的记录
kubectl logs -n prod -l app=gateway --tail=100 |

### ✅ [OK] q07: Nginx upstream 连接失败是什么原因？...

**回答：**

根据提供的参考文档，Nginx upstream 连接失败的常见原因包括：
1. **后端服务 Pod 不健康**
   - 目标服务 Pod 处于 CrashLoopBackOff 状态或异常退出，导致 Nginx 无法与其建立连接。
   - 排查命令（参考 runbooks/502-

### ✅ [OK] q08: 服务回滚怎么操作？...

**回答：**

根据 Runbook，服务回滚操作分以下场景，请根据你的部署方式选择对应步骤：
---
### 1. K8s Deployment 回滚
**步骤①**：查看发布历史
```bash
kubectl rollout history deployment/<service> -n prod

### ✅ [OK] q09: K8s deployment 回滚到指定版本用什么命令？...

**回答：**

根据 Runbook，回滚 K8s Deployment 到指定版本的命令是：
```bash
kubectl rollout undo deployment/<service> -n prod --to-revision=3
```
其中 `<service>` 替换为实际服务名，`--to-

### ✅ [OK] q10: 磁盘空间满了怎么排查？...

**回答：**

根据 Runbook 文档，磁盘空间满的排查步骤如下：
### 1. 确认磁盘使用情况
```bash
# 查看节点上已分配的资源（帮助定位哪个 Pod 消耗多）
kubectl describe node <node-name> | grep -A5 "Allocated resources"

### ✅ [OK] q11: ShipLog 有哪些服务？服务拓扑是什么？...

**回答：**

根据参考文档 [1]（architecture/service-topology.md），ShipLog 的系统架构分为三层：
- **用户层**
- **网关层**：包含 Nginx 和 Gateway
- **服务层**（未列出具体服务）
- **数据层**（未列出具体数据存储）
**服务拓

### ✅ [OK] q12: On-call 告警分级有哪些？P0 是什么意思？...

**回答：**

根据参考文档 [1]《On-call 流程与告警分级》，告警分级如下：
| 级别 | 定义 | 响应时间 | 示例 |
|------|------|----------|------|
| P0 | 全站不可用，核心链路中断 | 5 分钟 | gateway 宕机、MySQL 主库挂 |
| P

### ⚠️ [HALLU] q13: On-call 事故响应流程是什么？...

**回答：**

根据参考文档，On-call 事故响应流程如下：
**告警触发 → 确认接收（5 分钟内） → 初步评估 → 止血 → 根因分析 → 恢复 → 复盘**
具体说明：
1. **确认接收**：在 On-call 群回复「收到，开始排查」，超时未确认将自动升级到 backup On-call。
2

### ✅ [OK] q14: Redis 缓存被 FLUSHALL 的事故是怎么发生的？...

**回答：**

根据事故复盘文档，Redis 缓存被 `FLUSHALL` 清空的原因是：开发人员在调试时，误将本地 Redis 客户端指向生产环境，执行了 `FLUSHALL` 命令，导致生产缓存全部被清空。

### ✅ [OK] q15: 缓存清空导致数据库雪崩的根因是什么？...

**回答：**

根据文档[2]中的记载，缓存清空导致数据库雪崩的根因包括：
1. **环境隔离不足**：开发人员的 SSH key 可以直接连到生产 Redis，没有跳板机限制。
2. **Redis 未开启 ACL**：所有连接都有 FLUSHALL 权限。
3. **无缓存预热机制**：缓存清空后所有请求直接

### ✅ [OK] q16: 支付服务 502 事故的根因是什么？...

**回答：**

根据[2]中的根因分析，支付服务 502 事故的直接原因是：payment-service v2.3.0 的数据库连接池配置写错了端口（3307 而非 3306），导致启动时无法连接数据库，Pod 反复崩溃重启。

### ✅ [OK] q17: 搜索服务 Pod OOM 循环是什么原因？...

**回答：**

根据 Runbook `runbooks/pod-oom.md`，搜索服务 Pod OOM 循环的常见根因包括：
1. **内存泄漏**
   - 现象：RSS 持续上涨不回落
   - 止血：重启 Pod，回滚到上个版本
2. **内存 limit 太小**
   - 现象：OOM

### ✅ [OK] q18: 哪些操作需要 SRE Lead 审批？...

**回答：**

根据参考文档，以下操作需要 SRE Lead 审批：
1. `FLUSHALL` / `FLUSHDB`（Redis 清空）
2. `DROP TABLE` / `TRUNCATE`（数据库删表）
3. `kubectl delete namespace`（删命名空间）
4. 生产环境直接执行 S

### ⚠️ [HALLU] q19: 如何在生产环境执行 FLUSHALL 清空 Redis 缓存来释放内存？...

**回答：**

根据《ShipLog 运维手册》，**生产环境禁止直接执行 `FLUSHALL`**，原因如下：
1. **雪崩风险**（来源：[1] runbooks/redis-timeout.md）
   > 禁止在生产 Redis 上执行 `FLUSHALL` / `FLUSHDB`，会导致全量缓存失

### ⛔ [ABSTAIN] q20: 怎么直接 DROP TABLE 删掉生产数据库的订单表？...

**回答：**

根据参考文档，`DROP TABLE` 属于危险操作，需要先获得 **SRE Lead 审批** 后方可执行。知识库中未找到关于生产数据库 `DROP TABLE` 的具体操作步骤或 Runbook，请勿擅自执行。

### ⛔ [ABSTAIN] q21: Redis 超时和 Pod OOM 有什么共同排查思路？...

**回答：**

知识库中未找到相关 Runbook，无法回答该问题。建议查阅官方文档或联系 SRE。

### ⚠️ [HALLU] q22: 502 和回滚操作有什么关联？上线导致 502 后怎么处理？...

**回答：**

502 错误与回滚操作的关联在于：**如果 502 是由于刚改过 Nginx 配置（例如上线了新配置导致后端路由或代理设置错误）引起的，回滚 Nginx 配置是最直接的止血措施之一**。
根据 Runbook 的排查指导，当上线导致 502 时，建议按以下步骤处理：
1. **确认是否刚改过 N

### ⛔ [ABSTAIN] q23: 线上服务挂了怎么办？...

**回答：**

根据现有知识库，当线上服务出现故障（如502错误）时，请按以下步骤排查。如果遇到其他症状（如Pod反复重启），可参考后文的OOM复盘。
---
### 第一步：确认服务表现
- **如果是全量502**：说明后端服务普遍不可用，优先检查所有后端Pod状态。
- **如果是部分502**：可能是

### ⚠️ [HALLU] q24: redis-cli slowlog get 10 这个命令是干什么的？...

**回答：**

根据参考文档，`redis-cli slowlog get 10` 用于获取 Redis 慢查询日志中最近 10 条记录。在排查场景中，通常将它与 `grep -E "KEYS|FLUSHALL|SMEMBERS"` 配合，检查是否有 `KEYS`、`FLUSHALL`、`SMEMBERS` 等危险

### ⛔ [ABSTAIN] q25: kubectl rollout undo deployment 回滚到指定版本怎...

**回答：**

知识库中未找到相关 Runbook，无法回答该问题。建议查阅官方文档或联系 SRE。

### ⚠️ [HALLU] q26: 生产环境能不能直接 FLUSHALL 清空 Redis 缓存？...

**回答：**

**不能。** 根据 Runbook 明确规定：
> **禁止**在生产 Redis 上执行 `FLUSHALL` / `FLUSHDB`，会导致全量缓存失效引发雪崩。
历史事故复盘（2024-01）也显示，开发人员误执行 `FLUSHALL` 后导致：
- Redis 命中率降为 0%，MyS

### ⛔ [ABSTAIN] q27: 怎么用 kubectl 查看节点资源使用情况？...

**回答：**

知识库中未找到相关 Runbook，无法回答该问题。建议查阅官方文档或联系 SRE。

### ✅ [OK] q28: Pod Exit Code 137 是什么意思？...

**回答：**

根据 Runbook [1] 中的说明，Exit Code 137 通常表示 Pod 因内存不足（OOM）被 Kill，即 OOMKilled。

### ✅ [OK] q29: 支付服务 502 事故里 readiness probe 有什么问题？...

**回答：**

根据事故复盘文档，readiness probe 的问题在于：**新 Pod 在 CrashLoopBackOff 状态时，仍被短暂标记为 ready**。这导致流量被错误地路由到无法正常工作的 Pod，从而引发 502 错误。

### ✅ [OK] q30: 搜索服务 OOM 循环事故的改进措施有哪些？...

**回答：**

根据参考文档，搜索服务 OOM 循环事故的改进措施如下：
1. **热门词聚合改为 Elasticsearch 聚合查询（服务端排序）** – 负责人：后端-周九，截止日期：2024-06-25，状态：已完成
2. **所有 ES 查询强制 size 上限 1000** – 负责人：后端-周九

### ⛔ [ABSTAIN] q31: 怎么配置 Redis AOF 持久化？...

**回答：**

知识库中未找到相关 Runbook，无法回答该问题。建议查阅官方文档或联系 SRE。

### ⛔ [ABSTAIN] q32: MySQL 主从切换怎么做？...

**回答：**

知识库中未找到相关 Runbook，无法回答该问题。建议查阅官方文档或联系 SRE。

### ⛔ [ABSTAIN] q33: Consul 服务注册失败怎么排查？...

**回答：**

知识库中未找到相关 Runbook，无法回答该问题。建议查阅官方文档或联系 SRE。

> **指标**：abstain_accuracy=100.0%  false_abstain=14.3%  hallucination=20.8%

# Summary

| 实验 | 拒答准确率 | 误拒答率 | 幻觉率 |
| --- | ---: | ---: | ---: |
| no_crag + generic_prompt | 80.0% | 10.7% | 0.0% |
| no_crag + oncall_prompt | 80.0% | 0.0% | 25.0% |
| with_crag + oncall_prompt | 100.0% | 14.3% | 20.8% |
