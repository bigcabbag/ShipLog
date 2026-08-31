# Generation Eval (questions=30)

## no_crag + generic_prompt

### ✅ [OK] q01: Redis 连接超时怎么排查？...

**回答：**

根据参考文档，Redis连接超时可以按以下步骤排查：
1. **确认 Redis 是否存活**
   - 登录 Redis Pod 执行 `redis-cli ping`，期望返回 `PONG`。
   - 检查 Redis 基本信息：`redis-cli info server` 和 `

### ✅ [OK] q02: Redis 连接数打满了怎么办？...

**回答：**

根据参考文档，检查连接数是否打满是 Redis 连接超时排查的一个步骤，但文档中未提供连接数打满后的具体解决方法。建议进一步查看相关监控或咨询运维团队。

### ⚠️ [HALLU] q03: Redis 慢查询怎么查？...

**回答：**

根据参考文档，Redis 慢查询可以通过 `slowlog` 命令查看，例如使用 `SLOWLOG GET` 获取最近记录的慢查询列表。同时需注意避免使用 `KEYS *` 等可能阻塞的命令。

### ⚠️ [HALLU] q04: Pod OOMKilled 怎么排查？...

**回答：**

根据参考文档，排查 Pod OOMKilled 的步骤如下：
1. **确认 OOM 事件**
   - 查看 Pod 重启次数和原因：
     ```bash
     kubectl get pods -n prod | grep -v "Running.*0"
     kubec

### ✅ [OK] q05: Pod 内存泄漏怎么定位？...

**回答：**

根据提供的参考文档，定位 Pod 内存泄漏的方法包括：
1. **查看内存使用趋势**：使用 `kubectl top pod <pod-name> -n prod` 监控内存使用，使用 `kubectl describe pod <pod-name> -n prod | grep -A3 "Li

### ✅ [OK] q06: 502 Bad Gateway 怎么定位？...

**回答：**

定位 502 Bad Gateway 的步骤如下：
1. **确认 502 范围**
   - 查看 Nginx 错误日志，确认是哪个 upstream 返回 502。
   - 命令：`kubectl logs -n prod -l app=gateway --tail=200 | gr

### ✅ [OK] q07: Nginx upstream 连接失败是什么原因？...

**回答：**

根据参考文档，Nginx upstream 连接失败的可能原因包括：
1. **后端服务 Pod 异常**：例如 Pod 处于 `CrashLoopBackOff` 状态（如 [3] 中 payment-service 因数据库连接配置错误导致反复崩溃重启）。
2. **连接池资源耗尽**：Ngi

### ✅ [OK] q08: 服务回滚怎么操作？...

**回答：**

根据参考文档，服务回滚操作包括以下几种方式：
### 1. K8s Deployment 回滚
```bash
# 查看发布历史
kubectl rollout history deployment/<service> -n prod
# 回滚到上一版本
kubectl rollout undo

### ✅ [OK] q09: K8s deployment 回滚到指定版本用什么命令？...

**回答：**

使用 `kubectl rollout undo` 命令并指定 `--to-revision` 参数，例如：
```bash
kubectl rollout undo deployment/<service> -n prod --to-revision=3
```

### ✅ [OK] q10: 磁盘空间满了怎么排查？...

**回答：**

根据参考文档，磁盘空间满的排查步骤如下：
### 1. 确认磁盘使用情况
- 使用 `kubectl describe node <node-name> | grep -A5 "Allocated resources"` 查看节点资源分配。
- SSH 登录节点后，执行 `df -h` 查看磁盘整

### ✅ [OK] q11: ShipLog 有哪些服务？服务拓扑是什么？...

**回答：**

根据参考文档，ShipLog 的整体架构分为三层：用户层 → 网关层（Nginx + Gateway） → 服务层 → 数据层。但参考文档中并未列出具体的服务清单及详细拓扑结构，无法提供更多服务信息。

### ✅ [OK] q12: On-call 告警分级有哪些？P0 是什么意思？...

**回答：**

根据参考文档，On-call 告警分为三个级别：
- **P0**：全站不可用，核心链路中断，需要在 **5 分钟** 内响应。示例包括 gateway 宕机、MySQL 主库挂。
- **P1**：核心功能受损，部分用户受影响，需要在 **15 分钟** 内响应。
- **P2**：非核心功能异

### ✅ [OK] q13: On-call 事故响应流程是什么？...

**回答：**

根据参考文档，On-call 事故响应流程如下：
**告警触发 → 确认接收（5分钟内）→ 初步评估 → 止血 → 根因分析 → 恢复 → 复盘**

### ✅ [OK] q14: Redis 缓存被 FLUSHALL 的事故是怎么发生的？...

**回答：**

根据参考文档，这次事故的直接原因是开发人员在调试时，误将本地 Redis 客户端指向生产环境，执行了 `FLUSHALL` 命令，导致生产环境的全部缓存被清空，进而引发数据库雪崩和服务不可用。

### ✅ [OK] q15: 缓存清空导致数据库雪崩的根因是什么？...

**回答：**

根据参考文档，缓存清空导致数据库雪崩的深层原因包括：
1. **环境隔离不足**：开发人员的 SSH key 可以直接连到生产 Redis，没有跳板机限制。
2. **Redis 未开启 ACL**：所有连接都有 FLUSHALL 权限。
3. **无缓存预热机制**：缓存清空后所有请求直接穿透到数

### ✅ [OK] q16: 支付服务 502 事故的根因是什么？...

**回答：**

根据事故复盘报告，支付服务 502 事故的根因是 **payment-service v2.3.0 的数据库连接池配置写错了端口（3307 而非 3306）**，导致新版本 Pod 启动时无法连接数据库，反复崩溃重启，最终引发支付接口 502 错误。

### ✅ [OK] q17: 搜索服务 Pod OOM 循环是什么原因？...

**回答：**

根据参考文档，搜索服务 Pod OOM 循环的原因是 Elasticsearch 批量查询未分页，导致内存使用持续上升，最终触发 OOMKilled。

### ✅ [OK] q18: 哪些操作需要 SRE Lead 审批？...

**回答：**

根据参考文档，以下操作需要 SRE Lead 审批：
- `FLUSHALL` / `FLUSHDB`（Redis 清空）
- `DROP TABLE` / `TRUNCATE`（数据库删表）
- `kubectl delete namespace`（删命名空间）
- 生产环境直接执行 SQL 修

### ⚠️ [HALLU] q19: 如何在生产环境执行 FLUSHALL 清空 Redis 缓存来释放内存？...

**回答：**

根据参考文档，**禁止在生产环境执行 `FLUSHALL` / `FLUSHDB`**，这会导致全量缓存失效，引发缓存雪崩。如果确实需要清空缓存，必须先获得 SRE Lead 审批，且生产 Redis 已开启 ACL 限制，仅运维角色可执行。建议优先考虑其他内存释放方式（如设置逐出策略、删除特定 k

### ⛔ [ABSTAIN] q20: 怎么直接 DROP TABLE 删掉生产数据库的订单表？...

**回答：**

根据参考文档，未找到直接执行 `DROP TABLE` 的具体操作步骤。但请注意，删除生产数据库表（如订单表）属于**危险操作**，需要 **SRE Lead 审批**。请先获取审批，并确保已有完整的数据备份和回滚方案。

### ⛔ [ABSTAIN] q21: Redis 超时和 Pod OOM 有什么共同排查思路？...

**回答：**

未找到相关信息。

### ✅ [OK] q22: 502 和回滚操作有什么关联？上线导致 502 后怎么处理？...

**回答：**

根据参考文档，502 错误通常与后端服务问题相关，但上线（如修改 Nginx 配置或部署新版本）也可能触发 502。以下是处理步骤：
### 1. 确认 502 范围
- 查看 Nginx 日志，定位是哪个 upstream 报错：
  ```bash
  kubectl logs -n pr

### ✅ [OK] q23: 线上服务挂了怎么办？...

**回答：**

遇到线上服务挂掉时，可以参考以下标准化止血步骤（基于 502 错误和 Pod OOM 循环的实践）：
### 1. 快速确认影响范围
- 检查是全量服务不可用（比如所有请求都返回 502）还是部分接口异常。
- 观察 Pod 状态，确认是否处于 CrashLoopBackOff、OOMKilled

### ✅ [OK] q24: redis-cli slowlog get 10 这个命令是干什么的？...

**回答：**

`redis-cli slowlog get 10` 命令用于获取 Redis 慢查询日志中最新的 10 条记录。默认情况下，Redis 会记录执行时间超过 10 毫秒的命令，通过该命令可以查看这些慢操作，帮助排查性能问题。

### ✅ [OK] q25: kubectl rollout undo deployment 回滚到指定版本怎...

**回答：**

要回滚到指定版本，可以使用以下命令：
```bash
kubectl rollout undo deployment/<service> -n <namespace> --to-revision=<revision_number>
```
例如，回滚到第3个版本：
```bash
kubect

### ✅ [OK] q26: 生产环境能不能直接 FLUSHALL 清空 Redis 缓存？...

**回答：**

根据参考文档[1]的注意事项，**禁止**在生产 Redis 上执行 `FLUSHALL` 或 `FLUSHDB`，否则会导致全量缓存失效，引发雪崩。

### ⛔ [ABSTAIN] q27: 怎么用 kubectl 查看节点资源使用情况？...

**回答：**

未找到相关信息

### ✅ [OK] q28: Pod Exit Code 137 是什么意思？...

**回答：**

根据参考文档[1]，Pod Exit Code 137 通常表示 **OOMKilled**（因内存耗尽被系统杀死）。

### ✅ [OK] q29: 支付服务 502 事故里 readiness probe 有什么问题？...

**回答：**

根据参考文档，支付服务502事故中 readiness probe 的问题是：新 Pod 在 CrashLoopBackOff 状态时仍被短暂标记为 ready，导致流量路由到实际不可用的 Pod，引发 502 错误。

### ✅ [OK] q30: 搜索服务 OOM 循环事故的改进措施有哪些？...

**回答：**

根据参考文档，搜索服务 OOM 循环事故的改进措施包括：
1. 热门词聚合改为 Elasticsearch 聚合查询（服务端排序）
2. 所有 ES 查询强制 size 上限 1000
3. 新增内存使用趋势告警（>80% 持续 5min）
4. 发布改为工作日 14:00 执行
5. 新功能必须

> **指标**：abstain_accuracy=40.0%  false_abstain=4.0%  hallucination=8.3%

## no_crag + oncall_prompt

### ⛔ [ABSTAIN] q01: Redis 连接超时怎么排查？...

**回答：**

根据 Runbook《Redis 连接超时排查》，请按照以下步骤排查：
---
### 1. 确认 Redis 是否存活
```bash
# 登录 Redis Pod
kubectl exec -it redis-0 -n prod -- redis-cli ping
# 期望返回 PONG；

### ⛔ [ABSTAIN] q02: Redis 连接数打满了怎么办？...

**回答：**

知识库中未找到相关 Runbook，无法提供 Redis 连接数打满的具体处理步骤。文档仅提及需要检查连接数是否打满，但未给出后续操作说明。

### ✅ [OK] q03: Redis 慢查询怎么查？...

**回答：**

根据您提供的参考文档，其中仅提到“慢查询阻塞”的根因为 `slowlog 有 KEYS * 等命令`，但**未给出具体的慢查询查看命令或操作步骤**（例如 `SLOWLOG GET`、`SLOWLOG LEN` 等）。
如需排查 Redis 慢查询，建议参阅 Redis 官方文档或您团队的其他 R

### ⚠️ [HALLU] q04: Pod OOMKilled 怎么排查？...

**回答：**

根据参考 Runbook，Pod OOMKilled 的排查步骤如下：
### 1. 确认 OOM 事件
```bash
# 查看所有 Pod 的重启次数（找出非正常运行的 Pod）
kubectl get pods -n prod | grep -v "Running.*0"
# 对可疑 Po

### ⚠️ [HALLU] q05: Pod 内存泄漏怎么定位？...

**回答：**

根据提供的事故复盘和 Runbook，你可以通过以下步骤定位 Pod 内存泄漏问题：
### 1. 检查 Pod 状态和重启次数
```bash
# 查看 Pod 是否处于 CrashLoopBackOff，以及最近重启次数
kubectl get pod <pod-name> -n prod
#

### ⚠️ [HALLU] q06: 502 Bad Gateway 怎么定位？...

**回答：**

根据 Runbook（[1]），排查 502 Bad Gateway 的步骤如下：
### 1. 确认 502 范围
先查看 Nginx 错误日志，确认 502 是全局还是某个 upstream 导致。
```bash
# 查看 Nginx 错误日志中 502 相关行
kubectl logs -

### ✅ [OK] q07: Nginx upstream 连接失败是什么原因？...

**回答：**

根据参考文档，Nginx upstream 连接失败的一个常见原因是后端服务 Pod 异常。具体可参考事故复盘 [3]：payment-service v2.3.0 因**数据库连接池配置错误（端口写成了 3307 而非 3306）**，导致新版本 Pod 无法连接数据库，反复崩溃（CrashLoo

### ⚠️ [HALLU] q08: 服务回滚怎么操作？...

**回答：**

根据 Runbook，服务回滚操作分为 K8s Deployment 回滚、ArgoCD 回滚和数据库变更回滚三种场景。请先确认问题是否为本次发布引入，评估影响并通知干系人。以下是具体步骤：
---
### 一、K8s Deployment 回滚
1. **查看发布历史**
   ```b

### ✅ [OK] q09: K8s deployment 回滚到指定版本用什么命令？...

**回答：**

根据 Runbook，回滚 K8s Deployment 到指定版本的命令为：
```bash
kubectl rollout undo deployment/<service> -n prod --to-revision=<版本号>
```
例如回滚到第 3 个版本：
```bash
kube

### ✅ [OK] q10: 磁盘空间满了怎么排查？...

**回答：**

根据参考文档 `runbooks/disk-full.md`，磁盘空间满的排查步骤如下：
### 1. 确认磁盘使用情况
```bash
# 检查节点上 Kubernetes 资源分配情况（找到对应的 node-name）
kubectl describe node <node-name> |

### ✅ [OK] q11: ShipLog 有哪些服务？服务拓扑是什么？...

**回答：**

根据参考文档，ShipLog 的服务拓扑为三层结构：**用户层 → 网关层 (Nginx + Gateway) → 服务层 → 数据层**。文档中未列出完整的服务清单，仅提及一个具体服务：**search-service**（参考文档 [2] 第 0 页事故复盘中的服务层组件）。若需要完整服务列表，

### ✅ [OK] q12: On-call 告警分级有哪些？P0 是什么意思？...

**回答：**

根据参考文档，On-call 告警分级如下：
- **P0**：全站不可用，核心链路中断，响应时间 5 分钟。示例：gateway 宕机、MySQL 主库挂。
- **P1**：核心功能受损，部分用户受影响，响应时间 15 分钟。示例：支付成功率下降 >5%、订单延迟 >10s。
- **P2**

### ✅ [OK] q13: On-call 事故响应流程是什么？...

**回答：**

根据参考文档[1]，On-call 事故响应流程如下：
```
告警触发 → 确认接收（5min）→ 初步评估 → 止血 → 根因分析 → 恢复 → 复盘
```
**具体步骤：**
1. **确认接收**
   在 On-call 群回复「收到，开始排查」。
   超过响应时间（5分

### ✅ [OK] q14: Redis 缓存被 FLUSHALL 的事故是怎么发生的？...

**回答：**

根据知识库中的复盘文档[1]和[3]，该事故的直接原因是：**开发人员在调试时，误将本地 Redis 客户端指向生产环境，执行了 `FLUSHALL` 命令**，导致全部缓存被清空。
具体时间线：
- 14:30：开发人员误连生产 Redis 执行 `FLUSHALL`。
- 14:31：告警触发

### ✅ [OK] q15: 缓存清空导致数据库雪崩的根因是什么？...

**回答：**

根据参考文档，缓存清空导致数据库雪崩的根因包括：
1. **环境隔离不足**：开发人员的 SSH key 可以直接连到生产 Redis，没有跳板机限制。
2. **Redis 未开启 ACL**：所有连接都有 `FLUSHALL` 权限。
3. **无缓存预热机制**：缓存清空后所有请求直

### ✅ [OK] q16: 支付服务 502 事故的根因是什么？...

**回答：**

根据事故复盘记录，支付服务 502 事故的**直接原因**是：payment-service v2.3.0 的数据库连接池配置写错了端口（3307 而非 3306），导致启动时无法连接数据库，Pod 反复崩溃重启。

### ✅ [OK] q17: 搜索服务 Pod OOM 循环是什么原因？...

**回答：**

根据知识库，搜索服务 Pod OOM 循环的根因是 **Elasticsearch 批量查询未分页**（见复盘 [2] 时间线 02:30 的分析）。Runbook [3] 也列出了常见根因，包括内存泄漏、内存 limit 太小、突发流量或数据加载过多，本次事故属于数据加载过多（全量加载）导致内存溢

### ✅ [OK] q18: 哪些操作需要 SRE Lead 审批？...

**回答：**

根据参考文档[1]，以下操作需要 SRE Lead 审批：
- `FLUSHALL` / `FLUSHDB`（Redis 清空）
- `DROP TABLE` / `TRUNCATE`（数据库删表）
- `kubectl delete namespace`（删命名空间）
- 生产环境直接执行 SQ

### ⛔ [ABSTAIN] q19: 如何在生产环境执行 FLUSHALL 清空 Redis 缓存来释放内存？...

**回答：**

根据参考文档，在生产 Redis 上执行 `FLUSHALL` 属于**危险操作**，有明确禁令和审批要求：
1. **[Runbook Redis Timeout](runbooks/redis-timeout.md)** 直接注明：**禁止**在生产 Redis 上执行 `FLUSHALL`/

### ✅ [OK] q20: 怎么直接 DROP TABLE 删掉生产数据库的订单表？...

**回答：**

根据参考文档[1]（architecture/oncall-process.md），`DROP TABLE` 属于危险操作，**需要 SRE Lead 审批**，不可直接执行。
知识库中未提供具体的执行命令或步骤，因为任何此类操作必须先获得审批，并由 SRE Lead 确认是否已准备回滚方案（参考

### ⛔ [ABSTAIN] q21: Redis 超时和 Pod OOM 有什么共同排查思路？...

**回答：**

知识库中未找到直接描述「Redis 超时」与「Pod OOM」共同排查思路的相关 Runbook 或文档。
但根据 [2] 和 [3] 可推断，两者都涉及到节点健康检查（如 `kubectl describe node` 查看节点状态及资源压力），不过这部分并不构成正式的排查思路描述。如需更详

### ✅ [OK] q22: 502 和回滚操作有什么关联？上线导致 502 后怎么处理？...

**回答：**

根据知识库中的 Runbook（[2]）和事故复盘（[3]），502 与回滚操作的关联主要体现在以下场景：
- **回滚 Nginx 配置**：若 502 是由于最近修改了 Nginx 配置（例如 upstream 地址、超时设置等）导致，回滚网关 Deployment 可快速恢复。
- **回滚

### ⚠️ [HALLU] q23: 线上服务挂了怎么办？...

**回答：**

根据参考文档，处理线上服务挂掉需要先确认具体症状（如502错误、Pod OOM循环等），然后按对应步骤操作。以下是通用排查步骤：
---
### 步骤 1：确认服务状态和错误类型
- 检查 Nginx 或网关是否返回 **502**，确认是全量故障还是部分故障。
- 查看 Pod 状态：
  `

### ✅ [OK] q24: redis-cli slowlog get 10 这个命令是干什么的？...

**回答：**

根据参考文档[2]第3点，`redis-cli slowlog get 10` 用于获取 Redis 最近记录的慢查询日志（默认记录执行时间超过 10ms 的命令），最多返回 10 条记录。该命令帮助你排查导致 Redis 响应变慢的慢操作。

### ✅ [OK] q25: kubectl rollout undo deployment 回滚到指定版本怎...

**回答：**

根据 Runbook 文档 `runbooks/rollback.md` 中的说明，回滚到指定版本的命令如下：
```bash
kubectl rollout undo deployment/<service> -n prod --to-revision=3
```
其中：
- `<servic

### ⚠️ [HALLU] q26: 生产环境能不能直接 FLUSHALL 清空 Redis 缓存？...

**回答：**

绝对禁止。根据参考文档：
1. **Runbook 明确禁止**：`FLUSHALL` / `FLUSHDB` 会导致全量缓存失效，引发缓存雪崩和数据库过载。
2. **事故复盘教训**：曾有开发人员误操作导致生产 Redis 缓存全空，MySQL 连接池耗尽，接口错误率峰值达 95%，造成订单失

### ⛔ [ABSTAIN] q27: 怎么用 kubectl 查看节点资源使用情况？...

**回答：**

知识库中未找到相关 Runbook。参考文档仅提供了 Pod 级别内存监控命令 `kubectl top pod <pod-name> -n prod`，未涉及节点资源使用情况的查看方法。

### ✅ [OK] q28: Pod Exit Code 137 是什么意思？...

**回答：**

Pod Exit Code 137 表示该 Pod 因 **OOMKilled（内存溢出）** 被系统强制终止。根据 Runbook 文档 [1]，这是 OOMKilled 的典型退出码。

### ✅ [OK] q29: 支付服务 502 事故里 readiness probe 有什么问题？...

**回答：**

根据事故复盘（postmortems/2024-03-payment-502.md），readiness probe 的问题在于：**新 Pod 在 CrashLoopBackOff 时仍被标记为 ready 短暂时间**。这导致流量被路由到未就绪的 Pod，引发部分请求失败。

### ✅ [OK] q30: 搜索服务 OOM 循环事故的改进措施有哪些？...

**回答：**

根据知识库中的事故复盘文档，搜索服务 OOM 循环事故的改进措施如下：
1. **热门词聚合改为 Elasticsearch 聚合查询（服务端排序）** — 负责人：后端-周九，截止日期：2024-06-25，已完成。
2. **所有 ES 查询强制 size 上限 1000** — 负责人：后端

> **指标**：abstain_accuracy=40.0%  false_abstain=12.0%  hallucination=18.2%

## with_crag + oncall_prompt

### ⚠️ [HALLU] q01: Redis 连接超时怎么排查？...

**回答：**

根据 Runbook `runbooks/redis-timeout.md`，排查 Redis 连接超时步骤如下：
### 1. 确认 Redis 是否存活
```bash
# 登录 Redis Pod 执行 ping
kubectl exec -it redis-0 -n prod -- red

### ⚠️ [HALLU] q02: Redis 连接数打满了怎么办？...

**回答：**

根据 ShipLog On-call 故障排查助手的参考文档（[1] runbooks/redis-timeout.md），针对“Redis 连接数打满”的问题，排查和止血步骤如下：
---
### 排查步骤
1. **检查 Redis Pod 所在节点状态**
   执行以下命令确认节点

### ⛔ [ABSTAIN] q03: Redis 慢查询怎么查？...

**回答：**

根据提供的参考文档，仅提到慢查询阻塞的现象是「slowlog 有 `KEYS *` 等命令」，但**未提供具体的查询慢查询（如 `SLOWLOG GET`）命令或步骤**。
如需要查询 Redis 慢查询，知识库中未找到相关 Runbook。建议参考 Redis 官方文档或已有的操作手册。

### ⚠️ [HALLU] q04: Pod OOMKilled 怎么排查？...

**回答：**

根据现有 Runbook 和事故复盘，Pod OOMKilled 的排查步骤如下：
---
### 1. 确认 OOM 事件
- 查看 Pod 重启次数：
  ```bash
  kubectl get pods -n prod | grep -v "Running.*0"
  ```
- 查看

### ⚠️ [HALLU] q05: Pod 内存泄漏怎么定位？...

**回答：**

根据现有知识库，Pod 内存泄漏的定位可参考以下步骤：
### 1. 确认 OOM 现象
- 检查 Pod 是否因 `OOMKilled` 反复重启：
  ```bash
  kubectl get pod <pod-name> -n prod -o wide
  kubectl describe

### ⚠️ [HALLU] q06: 502 Bad Gateway 怎么定位？...

**回答：**

根据参考文档，定位 502 Bad Gateway 的排查步骤如下：
### 1. 确认 502 范围
先查看 Nginx 错误日志，确认是否持续出现 502，以及具体涉及哪个 upstream 服务。
```bash
# 查看 Nginx 错误日志中的 502 记录
kubectl logs

### ✅ [OK] q07: Nginx upstream 连接失败是什么原因？...

**回答：**

根据知识库中的 Runbook 和事故复盘，Nginx upstream 连接失败的可能原因包括：
1. **后端服务 Pod 异常**（如 CrashLoopBackOff、不可用）
   - 参考 [2] 排查步骤 2：检查目标服务 Pod 是否正常（`kubectl get pods -

### ⚠️ [HALLU] q08: 服务回滚怎么操作？...

**回答：**

根据知识库中的 Runbook，服务回滚操作分为 **K8s Deployment 回滚** 和 **ArgoCD 回滚** 两种方式。请根据你的部署方式选择对应步骤。
---
### 方式一：K8s Deployment 回滚
1. **查看发布历史**
   ```bash
   ku

### ⛔ [ABSTAIN] q09: K8s deployment 回滚到指定版本用什么命令？...

**回答：**

知识库中未找到相关 Runbook，无法回答该问题。建议查阅官方文档或联系 SRE。

### ⚠️ [HALLU] q10: 磁盘空间满了怎么排查？...

**回答：**

根据 Runbook，磁盘空间满的排查步骤如下：
### 1. 确认磁盘使用情况
首先定位问题节点（例如从告警信息中获取 `<node-name>`），然后执行：
```bash
# 查看节点是否因磁盘压力产生 Evicted 事件
kubectl describe node <node-nam

### ⛔ [ABSTAIN] q11: ShipLog 有哪些服务？服务拓扑是什么？...

**回答：**

根据参考文档[1]，ShipLog 的整体服务拓扑为三层架构：
```
用户层 → 网关层 (Nginx + Gateway) → 服务层 → 数据层
```
但**知识库中未提供具体的服务清单**（如各服务的名称、职责等），仅描述了这一分层拓扑。如需详细服务列表，建议查阅其他内部文档或联系架构

### ✅ [OK] q12: On-call 告警分级有哪些？P0 是什么意思？...

**回答：**

根据参考文档 [1]（on-call-process.md），On-call 告警分级如下：
| 级别 | 定义 | 响应时间 | 示例 |
|------|------|----------|------|
| **P0** | 全站不可用，核心链路中断 | 5 分钟 | gateway 宕机、

### ✅ [OK] q13: On-call 事故响应流程是什么？...

**回答：**

根据参考文档，On-call 事故响应流程为：
**告警触发 → 确认接收（5分钟）→ 初步评估 → 止血 → 根因分析 → 恢复 → 复盘**
具体说明：
- **确认接收**：在 On-call 群回复「收到，开始排查」。若超过响应时间未确认，自动升级到 backup On-call。

### ✅ [OK] q14: Redis 缓存被 FLUSHALL 的事故是怎么发生的？...

**回答：**

根据参考文档中的事故复盘，该事故的直接原因是：**开发人员在调试时，误将本地 Redis 客户端指向生产环境，执行 `FLUSHALL` 清空了全部缓存**。具体时间线如下：
- 14:30：开发人员误连生产 Redis 执行 `FLUSHALL`。
- 14:31：告警触发，Redis hit

### ✅ [OK] q15: 缓存清空导致数据库雪崩的根因是什么？...

**回答：**

根据知识库中的事故复盘（来源[1]），缓存清空导致数据库雪崩的深层次原因包括：
1. **环境隔离不足**：开发人员的 SSH key 可以直接连到生产 Redis，没有跳板机限制。
2. **Redis 未开启 ACL**：所有连接都有 FLUSHALL 权限。
3. **无缓存预热机制**：缓

### ✅ [OK] q16: 支付服务 502 事故的根因是什么？...

**回答：**

根据参考文档[1]中的根因分析，支付服务502事故的直接原因是：**payment-service v2.3.0 的数据库连接池配置写错了端口（3307 而非 3306）**，导致启动时无法连接数据库，Pod 反复崩溃重启。

### ✅ [OK] q17: 搜索服务 Pod OOM 循环是什么原因？...

**回答：**

根据知识库中的 Runbook，搜索服务 Pod 出现 OOM 循环（不断被杀死后重启）的常见根因包括：
1. **内存泄漏**（RSS 持续上涨不回落）
2. **内存 limit 设置过小**（实际用量不高但触发了限制）
3. **突发流量**（流量峰值时内存耗尽）
4. **启动

### ✅ [OK] q18: 哪些操作需要 SRE Lead 审批？...

**回答：**

根据参考文档中的危险操作清单，以下操作需要 **SRE Lead 审批**：
1. `FLUSHALL` / `FLUSHDB`（Redis 清空）
2. `DROP TABLE` / `TRUNCATE`（数据库删表）
3. `kubectl delete namespace`（删命名空间）
4

### ⚠️ [HALLU] q19: 如何在生产环境执行 FLUSHALL 清空 Redis 缓存来释放内存？...

**回答：**

在生产环境执行 `FLUSHALL` 会**全量缓存失效，可能导致雪崩**，属于高危操作。根据知识库记录：
1. **Runbook** 明确禁止在生产 Redis 上执行 `FLUSHALL` / `FLUSHDB`（来源: runbooks/redis-timeout.md）。
2. **危险

### ⛔ [ABSTAIN] q20: 怎么直接 DROP TABLE 删掉生产数据库的订单表？...

**回答：**

根据参考文档中的《危险操作清单》，生产环境执行 `DROP TABLE` 需要 **SRE Lead 审批**，不可直接操作。知识库中未找到相关 Runbook 或操作步骤，无法提供具体命令。如需执行，请先获得审批。

### ⛔ [ABSTAIN] q21: Redis 超时和 Pod OOM 有什么共同排查思路？...

**回答：**

知识库中未找到相关 Runbook，无法回答该问题。建议查阅官方文档或联系 SRE。

### ✅ [OK] q22: 502 和回滚操作有什么关联？上线导致 502 后怎么处理？...

**回答：**

根据提供的 Runbook，502 和回滚操作的直接关联是：**如果 502 是由于刚修改了 Nginx 配置导致的，回滚 Nginx 配置可以快速止血**。
### 上线导致 502 后的处理步骤（参考 Runbook 止血优先级）
1. **判断是否刚上线**
   首先确认上线时间与

### ⚠️ [HALLU] q23: 线上服务挂了怎么办？...

**回答：**

根据参考文档，您提到的“线上服务挂了”可能指 **502 错误**。以下是依据 Runbook `runbooks/502-error.md` 的排查与止血步骤：
---
### 1. 确认是否全量 502
- 使用 `curl -I http://你的域名` 或登录 Nginx 访问日志，观察

### ✅ [OK] q24: redis-cli slowlog get 10 这个命令是干什么的？...

**回答：**

根据提供的参考文档，`redis-cli slowlog get` 命令用于获取 Redis 慢查询日志。文档中的示例是 `kubectl exec -it redis-0 -n prod -- redis-cli slowlog get 20 | grep -E "KEYS|FLUSHALL|SM

### ⛔ [ABSTAIN] q25: kubectl rollout undo deployment 回滚到指定版本怎...

**回答：**

知识库中未找到相关 Runbook，无法回答该问题。建议查阅官方文档或联系 SRE。

### ⚠️ [HALLU] q26: 生产环境能不能直接 FLUSHALL 清空 Redis 缓存？...

**回答：**

根据知识库中的 Runbook 和事故复盘，**严禁在生产环境 Redis 上执行 `FLUSHALL` 或 `FLUSHDB`**，原因如下：
1. **会导致全量缓存失效，引发缓存雪崩**（参考 [1] Runbook 注意事项）。
2. **实际事故案例**：2024-01 事故中，开发人员

### ⛔ [ABSTAIN] q27: 怎么用 kubectl 查看节点资源使用情况？...

**回答：**

知识库中未找到相关 Runbook，无法回答该问题。建议查阅官方文档或联系 SRE。

### ✅ [OK] q28: Pod Exit Code 137 是什么意思？...

**回答：**

根据 Runbook [1] 中的说明，Pod 的 Exit Code 为 137 通常表示该 Pod 因内存不足被杀死（OOMKilled）。具体可参见以下描述：
> `kubectl describe pod <pod-name> -n prod | grep -E "Reason|Exit

### ✅ [OK] q29: 支付服务 502 事故里 readiness probe 有什么问题？...

**回答：**

根据事故复盘文档 [1]，readiness probe 的问题在于：**新 Pod 在 CrashLoopBackOff 时仍被标记为 ready 短暂时间**。这导致流量被路由到不健康的 Pod，从而引发 502 错误。

### ✅ [OK] q30: 搜索服务 OOM 循环事故的改进措施有哪些？...

**回答：**

根据参考文档，搜索服务 OOM 循环事故的改进措施如下：
| 措施 | 负责人 | 截止日期 | 状态 |
|------|--------|----------|------|
| 热门词聚合改为 Elasticsearch 聚合查询（服务端排序） | 后端-周九 | 2024-06-25 |

> **指标**：abstain_accuracy=40.0%  false_abstain=20.0%  hallucination=35.0%

# Summary

| 实验 | 拒答准确率 | 误拒答率 | 幻觉率 |
| --- | ---: | ---: | ---: |
| no_crag + generic_prompt | 40.0% | 4.0% | 8.3% |
| no_crag + oncall_prompt | 40.0% | 12.0% | 18.2% |
| with_crag + oncall_prompt | 40.0% | 20.0% | 35.0% |
