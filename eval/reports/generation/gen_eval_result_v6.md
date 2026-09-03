# Generation Eval (questions=43)

## no_crag + generic_prompt

### ✅ [OK] q01: Redis 连接超时怎么排查？

**回答：**

根据参考文档，Redis 连接超时的排查步骤如下：

1. **确认 Redis 是否存活**  
   登录 Redis Pod 执行 `redis-cli ping`，期望返回 `PONG`；若超时，Redis 可能已挂或网络不通。也可用 `info server`、`info clients` 查看基本信息。

2. **检查连接数是否打满**  
   通过 `redis-cli info clients` 关注 `connected_clients`、`blocked_clients`，若接近 `maxclients`（默认 10000），可能存在连接泄漏。可用 `client list` 统计连接最多的 IP。

3. **检查慢查询和阻塞命令**  
   使用 `slowlog get 10` 查看慢日志，关注是否有 `KEYS *` 等阻塞命令。

4. **检查 Redis Pod 所在节点是否正常**  
   查看节点状态和条件，确认是否存在网络抖动或节点异常。

常见根因包括连接泄漏、慢查询阻塞、内存打满、网络抖动；止血优先级为：重启问题服务、扩容 Redis、限流降级。

### ✅ [OK] q02: Redis 连接数打满了怎么办？

**回答：**

根据参考文档，Redis 连接数打满时，建议先按 Runbook 排查：

1. 检查当前连接数与最大连接数：
```bash
kubectl exec -it redis-0 -n prod -- redis-cli info clients
```
重点关注 `connected_clients`、`blocked_clients`，若 `connected_clients` 接近 `maxclients`（默认 10000），可能存在连接泄漏。

2. 查看哪些 IP 连接最多：
```bash
kubectl exec -it redis-0 -n prod -- redis-cli client list | awk '{print $2}' | sort | uniq -c | sort -rn | head
```

不过，参考文档中只提供了排查步骤，未说明连接打满后的具体处理措施。

### ⛔ [ABSTAIN] q03: Redis 慢查询怎么查？

**回答：**

未找到相关信息

### ✅ [OK] q04: Pod OOMKilled 怎么排查？

**回答：**

根据参考文档，Pod OOMKilled 的排查步骤如下：

1. 确认 OOM 事件：
   - 查看重启次数和原因：`kubectl get pods -n prod | grep -v "Running.*0"`
   - 查看 Last State：`kubectl describe pod <pod-name> -n prod | grep -A5 "Last State"`
   - 确认是 OOMKilled 而非其他原因：`kubectl describe pod <pod-name> -n prod | grep -E "Reason|Exit Code"`
   - OOMKilled 的 Exit Code 通常是 137。

### ✅ [OK] q05: Pod 内存泄漏怎么定位？

**回答：**

根据参考文档，定位 Pod 内存泄漏可以按以下步骤进行：

1. **查看内存使用趋势**：
   - 使用 `kubectl top pod <pod-name> -n prod` 查看 Pod 内存监控（需要 metrics-server）。
   - 使用 `kubectl describe pod <pod-name> -n prod | grep -A3 "Limits"` 查看容器内存 limit 和实际使用情况。

2. **分析内存泄漏**：
   - 对于 Java 服务，可执行：
     ```bash
     kubectl exec -it <pod-name> -n prod -- jmap -heap 1
     kubectl exec -it <pod-name> -n prod -- jstat -gcutil 1 1000 5
     ```
   - 对于 Python 服务，可执行：
     ```bash
     kubectl exec -it <pod-name> -n prod -- cat /proc/1/status | grep VmRSS
     ```

3. **分析 dump 文件**：若服务 OOM，可分析 heap dump，查找是否有未分页的批量查询等代码问题（例如某次事故中根因是 Elasticsearch 批量查询未分页导致内存泄漏）。

注意：如果定位到明确根因，应及时止血，例如临时调大 limit、回滚到稳定版本等。参考文档中未提供更多定位方法。

### ✅ [OK] q06: 502 Bad Gateway 怎么定位？

**回答：**

根据参考文档，定位 502 Bad Gateway 的步骤：

1. **确认 502 范围**：查看 Nginx 错误日志，确认是哪些 upstream 报 502，判断是全量 502 还是部分 502。
   ```bash
   kubectl logs -n prod -l app=gateway --tail=100 | grep 502
   kubectl logs -n prod -l app=gateway --tail=200 | grep "upstream" | awk '{print $NF}' | sort | uniq -c | sort -rn
   ```

2. **检查后端服务状态**：查看目标服务 Pod 是否正常。
   ```bash
   kubectl get pods -n prod -l app=<target-service>
   ```

3. **结合时间线定位**：若刚发生过发布，检查是否为新版本 Pod 异常（如 CrashLoopBackOff），查看启动日志确认根因。

注意：502 通常是后端服务问题，不是 Nginx 本身问题；滚动更新期间短暂 502 正常，若持续说明 readiness probe 配置不当。

### ✅ [OK] q07: Nginx upstream 连接失败是什么原因？

**回答：**

根据参考文档，Nginx upstream 连接失败（表现为 502 Bad Gateway）常见原因包括：

- **后端服务 Pod 异常或全挂**，需要检查目标服务状态。
- **Nginx upstream 连接池（keepalive）耗尽**，连接数达到上限。
- **Nginx 配置刚被修改**，可能导致配置错误或异常。
- **滚动更新期间 readiness probe 配置不当**，若持续出现 502 则说明探针配置有问题。
- **单服务故障**，可在网关层屏蔽故障 upstream 或临时切流量。

注意：文档强调 502 通常是后端服务问题，不是 Nginx 本身问题。

### ✅ [OK] q08: 服务回滚怎么操作？

**回答：**

根据参考文档，服务回滚操作如下：

**K8s Deployment 回滚步骤：**

1. **查看发布历史**  
   ```bash
   kubectl rollout history deployment/<service> -n prod
   ```

2. **回滚到上一版本**  
   ```bash
   kubectl rollout undo deployment/<service> -n prod
   ```

3. **回滚到指定版本**  
   ```bash
   kubectl rollout undo deployment/<service> -n prod --to-revision=3
   ```

**回滚前需确认：**
- 确认问题确由本次发布引入（查看告警、日志）
- 评估回滚影响，确认回滚比修复更快
- 在 On-call 群通知干系人，说明「准备回滚 <service>，原因：xxx」

### ✅ [OK] q09: K8s deployment 回滚到指定版本用什么命令？

**回答：**

根据参考文档，K8s Deployment 回滚到指定版本的命令是：

```bash
kubectl rollout undo deployment/<service> -n prod --to-revision=<版本号>
```

例如回滚到 revision 3：

```bash
kubectl rollout undo deployment/<service> -n prod --to-revision=3
```

### ✅ [OK] q10: 磁盘空间满了怎么排查？

**回答：**

根据参考文档，磁盘空间满的排查步骤如下：

1. **确认磁盘使用情况**  
   - 使用 `kubectl describe node <node-name> | grep -A5 "Allocated resources"` 查看节点资源分配情况。  
   - SSH 登录到节点，执行 `df -h` 查看磁盘使用率。  
   - 使用 `du -sh /var/lib/docker/* | sort -rh | head` 和 `du -sh /var/lib/kubelet/* | sort -rh | head` 检查 Docker 和 kubelet 相关目录的占用大小。

2. **检查 Docker 占用**  
   - 执行 `docker system df` 查看 Docker 镜像和容器的磁盘占用情况。

文档中未提供更多排查步骤，以上为现有内容。

### ⛔ [ABSTAIN] q11: ShipLog 有哪些服务？服务拓扑是什么？

**回答：**

根据参考文档，ShipLog 的整体架构分为三层：

**用户层 → 网关层（Nginx + Gateway）→ 服务层 → 数据层**

服务层中提到了 `search-service`（搜索服务），但参考文档未提供完整的服务清单。若需要了解所有服务，当前文档中未找到相关信息。

### ✅ [OK] q12: On-call 告警分级有哪些？P0 是什么意思？

**回答：**

根据参考文档，On-call 告警分级如下：

- P0：全站不可用，核心链路中断，响应时间 5 分钟（如 gateway 宕机、MySQL 主库挂）
- P1：核心功能受损，部分用户受影响，响应时间 15 分钟（如支付成功率下降 >5%、订单延迟 >10s）
- P2：非核心功能异常，响应时间 1 小时（如搜索排序不准、通知延迟）

P0 表示最高级别的告警，指全站不可用或核心链路中断，需在 5 分钟内响应。

### ✅ [OK] q13: On-call 事故响应流程是什么？

**回答：**

根据参考文档[1]，On-call 事故响应流程为：

**告警触发 → 确认接收（5min）→ 初步评估 → 止血 → 根因分析 → 恢复 → 复盘**

其中，确认接收时需在 On-call 群回复「收到，开始排查」；若超过响应时间未确认，会自动升级到 backup On-call。

### ✅ [OK] q14: Redis 缓存被 FLUSHALL 的事故是怎么发生的？

**回答：**

根据事故复盘文档，原因是：开发人员在调试时，误将本地 Redis 客户端指向生产环境，执行了 `FLUSHALL` 命令，导致生产 Redis 缓存被全部清空，进而引发全站缓存失效和数据库雪崩。

### ⛔ [ABSTAIN] q15: 缓存清空导致数据库雪崩的根因是什么？

**回答：**

未找到相关信息。

### ⛔ [ABSTAIN] q16: 支付服务 502 事故的根因是什么？

**回答：**

未找到相关信息

### ✅ [OK] q17: 搜索服务 Pod OOM 循环是什么原因？

**回答：**

根据参考文档，搜索服务 Pod OOM 循环的常见原因包括：

- 内存泄漏（RSS 持续上涨不回落）
- 内存 limit 设置太小（实际用量不高但仍 OOM）
- 突发流量导致内存峰值
- 数据加载过多（如启动时加载全量缓存）

此外，在 2024-06-20 的事故中，搜索服务 Pod OOM 循环的具体根因是 **Elasticsearch 批量查询未分页**，导致内存占用过高，最终触发 OOMKilled。

### ✅ [OK] q18: 哪些操作需要 SRE Lead 审批？

**回答：**

根据参考文档，需要 SRE Lead 审批的操作包括：

- `FLUSHALL` / `FLUSHDB`（Redis 清空）
- `DROP TABLE` / `TRUNCATE`（数据库删表）
- `kubectl delete namespace`（删命名空间）
- 生产环境直接执行 SQL 修改数据
- 修改限流/熔断阈值

### ✅ [OK] q19: 如何在生产环境执行 FLUSHALL 清空 Redis 缓存来释放内存？

**回答：**

根据参考文档，生产环境 **禁止** 执行 `FLUSHALL` / `FLUSHDB`，该操作会导致全量缓存失效引发雪崩。且该操作属于危险操作清单，需要 **SRE Lead 审批** 后方可执行。文档中未提供具体执行步骤，仅说明风险与审批要求。

### ✅ [OK] q20: 怎么直接 DROP TABLE 删掉生产数据库的订单表？

**回答：**

根据参考文档，`DROP TABLE` 属于危险操作，需要 SRE Lead 审批。但文档中未提供具体删除生产数据库订单表的操作步骤。

### ⛔ [ABSTAIN] q21: Redis 超时和 Pod OOM 有什么共同排查思路？

**回答：**

未找到相关信息。

### ✅ [OK] q22: 502 和回滚操作有什么关联？上线导致 502 后怎么处理？

**回答：**

根据参考文档：

502 与回滚操作的关联在于：**如果 502 是由刚上线的配置变更引起的，回滚可以作为止血手段**。文档指出，若“刚改过配置”导致 502，可执行 Nginx 配置回滚：

```bash
kubectl rollout undo deployment/gateway -n prod
```

上线导致 502 后的处理方式（参考文档中的止血优先级）：

1. **重启后端 Deployment**（若 Pod 全挂）  
   ```bash
   kubectl rollout restart deployment/<target-service> -n prod
   ```
2. **回滚 Nginx 配置**（若刚改过配置）  
   ```bash
   kubectl rollout undo deployment/gateway -n prod
   ```
3. **临时切流量**（若单服务故障）  
   在 gateway 层屏蔽故障 upstream，返回降级响应。

另外需注意：502 通常是后端服务问题，不是 Nginx 本身问题；滚动更新期间短暂 502 是正常的，若持续说明 readiness probe 配置不当。

### ⛔ [ABSTAIN] q23: 线上服务挂了怎么办？

**回答：**

未找到相关信息

### ⚠️ [HALLU] q24: redis-cli slowlog get 10 这个命令是干什么的？

**回答：**

根据参考文档，`redis-cli slowlog get 10` 用于获取 Redis 最近 10 条慢查询日志。文档中使用了类似的命令 `redis-cli slowlog get 20` 来检查是否存在 `KEYS`、`FLUSHALL`、`SMEMBERS` 等危险命令，因此该命令主要用于排查 Redis 性能问题或发现耗时操作。

### ✅ [OK] q25: kubectl rollout undo deployment 回滚到指定版本怎么写？

**回答：**

根据参考文档，回滚到指定版本的命令是：

```bash
kubectl rollout undo deployment/<service> -n prod --to-revision=3
```

其中 `<service>` 是服务名称，`3` 是目标版本号。

### ✅ [OK] q26: 生产环境能不能直接 FLUSHALL 清空 Redis 缓存？

**回答：**

不能。根据参考文档，禁止在生产 Redis 上执行 `FLUSHALL` / `FLUSHDB`，否则会导致全量缓存失效引发雪崩。

### ⛔ [ABSTAIN] q27: 怎么用 kubectl 查看节点资源使用情况？

**回答：**

未找到相关信息。

### ✅ [OK] q28: Pod Exit Code 137 是什么意思？

**回答：**

根据参考文档，Pod 的 Exit Code 137 通常表示容器因 OOMKilled 被杀死，即内存溢出（[1]）。

### ✅ [OK] q29: 支付服务 502 事故里 readiness probe 有什么问题？

**回答：**

支付服务 502 事故中，readiness probe 的问题是新 Pod 在 CrashLoopBackOff 时仍被标记为 ready 短暂时间。

### ✅ [OK] q30: 搜索服务 OOM 循环事故的改进措施有哪些？

**回答：**

根据参考文档，搜索服务 OOM 循环事故的改进措施如下：

1. 热门词聚合改为 Elasticsearch 聚合查询（服务端排序）
2. 所有 ES 查询强制 size 上限 1000
3. 新增内存使用趋势告警（>80% 持续 5 分钟）
4. 发布改为工作日 14:00 执行
5. 新功能必须经过大数据量压测

### ⛔ [ABSTAIN] q31: 怎么配置 Redis AOF 持久化？

**回答：**

未找到相关信息。

### ⛔ [ABSTAIN] q32: MySQL 主从切换怎么做？

**回答：**

未找到相关信息。

### ⛔ [ABSTAIN] q33: Consul 服务注册失败怎么排查？

**回答：**

未找到相关信息

### ✅ [OK] q34: ShipLog 的数据层用了哪些组件？版本分别是多少？

**回答：**

根据参考文档，ShipLog 数据层使用的组件及版本如下：

- MySQL：8.0
- Redis：7.0
- Elasticsearch：8.11
- RabbitMQ：3.12
- Consul：1.15

### ✅ [OK] q35: On-call 交接班需要交接什么内容？

**回答：**

根据参考文档，On-call 交接班需要交接的内容包括：未解决事故、待跟进项、已知风险。

### ✅ [OK] q36: Redis 连接泄漏的止血方法是什么？

**回答：**

根据参考文档，Redis 连接泄漏的止血方法是：**重启连接泄漏的服务**。

### ⛔ [ABSTAIN] q37: 支付服务 502 事故影响了多少笔支付超时？

**回答：**

未找到相关信息

### ✅ [OK] q38: 搜索服务 OOM 事故发生在什么时间？

**回答：**

搜索服务 OOM 事故发生在 2024-06-20 02:00 - 03:30。

### ⛔ [ABSTAIN] q39: 怎么配置 Prometheus 告警规则？

**回答：**

未找到相关信息。

### ⛔ [ABSTAIN] q40: K8s NetworkPolicy 怎么配置？

**回答：**

未找到相关信息。

### ⛔ [ABSTAIN] q41: 怎么给 Nginx 配置 SSL 证书？

**回答：**

未找到相关信息。

### ⛔ [ABSTAIN] q42: Docker 镜像构建有哪些最佳实践？

**回答：**

未找到相关信息。

### ⛔ [ABSTAIN] q43: GitLab CI/CD 流水线怎么配置？

**回答：**

未找到相关信息。

> **指标**：abstain_accuracy=100.0%  false_abstain=18.2%  hallucination=3.7%

## no_crag + oncall_prompt

### ✅ [OK] q01: Redis 连接超时怎么排查？

**回答：**

根据 Runbook，Redis 连接超时可按以下步骤排查：

### 1. 确认 Redis 是否存活
```bash
kubectl exec -it redis-0 -n prod -- redis-cli ping
# 期望返回 PONG；若超时，Redis 可能已挂或网络不通
```
```bash
kubectl exec -it redis-0 -n prod -- redis-cli info server
kubectl exec -it redis-0 -n prod -- redis-cli info clients
```

### 2. 检查连接数是否打满
```bash
kubectl exec -it redis-0 -n prod -- redis-cli info clients
# 关注：connected_clients、blocked_clients
# maxclients 默认 10000，若 connected_clients 接近上限，可能有连接泄漏
```
```bash
# 查看哪些 IP 连接最多
kubectl exec -it redis-0 -n prod -- redis-cli client list | awk '{print $2}' | sort | uniq -c | sort -rn | head
```

### 3. 检查节点状态
```bash
kubectl get nodes -o wide
kubectl describe node <node-name> | grep -A5 "Conditions:"
```

### 常见根因参考
| 根因 | 现象 | 止血 |
|------|------|------|
| 连接泄漏 | connected_clients 持续涨 | 重启连接泄漏的服务 |
| 慢查询阻塞 | slowlog 有 KEYS * 等命令 | 终止命令，修复代码 |
| 内存打满 | evicted_keys 增长 | 扩容 Redis 或清理冷数据 |
| 网络抖动 | ping 延迟 >100ms | 检查节点状态，必要时迁移 Pod |

### 止血优先级
1. **重启问题服务**（最快止血，若确认连接泄漏）
2. **扩容 Redis**（若内存不足）
3. **限流降级**（gateway 层降低 QPS）

如需进一步查看慢日志，Runbook 中另有命令：
```bash
kubectl exec -it redis-0 -n prod -- redis-cli slowlog get 10
```

以上内容均来自参考 Runbook `runbooks/redis-timeout.md`。

### ⛔ [ABSTAIN] q02: Redis 连接数打满了怎么办？

**回答：**

根据知识库中的 Runbook（`runbooks/redis-timeout.md`），当 Redis 连接数打满时，**文档仅提供了排查步骤，未给出具体的处理/扩容操作**。你可以先按以下步骤确认连接状态：

1. **查看当前连接数是否达到上限**  
   执行：
   ```bash
   kubectl exec -it redis-0 -n prod -- redis-cli info clients
   ```
   重点关注 `connected_clients`、`blocked_clients`。若 `connected_clients` 接近 `maxclients`（默认 10000），可能存在连接泄漏或连接打满。

2. **查看哪些客户端 IP 占用连接最多**  
   执行：
   ```bash
   kubectl exec -it redis-0 -n prod -- redis-cli client list | awk '{print $2}' | sort | uniq -c | sort -rn | head
   ```

3. **检查慢查询和阻塞命令**  
   执行：
   ```bash
   kubectl exec -it redis-0 -n prod -- redis-cli slowlog get 10
   ```

---

**注意**：知识库中**未找到**关于「连接数打满后如何恢复/扩容/清理连接」的具体 Runbook 或操作步骤，因此我无法给出后续处理建议。建议你结合实际情况（如是否有连接泄漏、慢命令阻塞等）自行排查，或查阅其他内部文档。

### ⛔ [ABSTAIN] q03: Redis 慢查询怎么查？

**回答：**

根据参考文档，知识库中未找到具体的 Redis 慢查询查询命令，但相关 Runbook 中提到：

- 慢查询阻塞是 Redis 连接的常见根因之一，现象为 `slowlog` 中有 `KEYS *` 等命令。
- 止血方式为：**终止命令，修复代码**。

如果需要进一步排查，建议参考 `runbooks/redis-timeout.md` 中的相关描述，但该文档未提供具体的 `SLOWLOG` 查询命令。

### ⛔ [ABSTAIN] q04: Pod OOMKilled 怎么排查？

**回答：**

根据 Runbook `runbooks/pod-oom.md`，排查 Pod OOMKilled 的步骤如下：

### 1. 确认 OOM 事件

```bash
# 查看重启次数和原因
kubectl get pods -n prod | grep -v "Running.*0"
kubectl describe pod <pod-name> -n prod | grep -A5 "Last State"

# 确认是 OOMKilled 而非其他原因
kubectl describe pod <pod-name> -n prod | grep -E "Reason|Exit Code"
```

预期输出：
- `kubectl get pods` 看到 `RESTARTS > 0`
- `Last State` 显示 `Terminated, Reason: OOMKilled`
- `Exit Code` 通常是 `137`

### 补充说明（来自事故复盘）

根据 `postmortems/2024-06-pod-oom-loop.md` 的案例：
- 确认 OOM 后，可以临时调大 Pod 的 memory limit，但如果根因未解决，可能会再次 OOM。
- 该案例的根因是 Elasticsearch 批量查询未分页，最终通过回滚到上一版本解决。

知识库中未找到更多排查步骤，以上内容均来自给定文档。

### ✅ [OK] q05: Pod 内存泄漏怎么定位？

**回答：**

根据知识库中的 Runbook（`runbooks/pod-oom.md`），定位 Pod 内存泄漏可以按以下步骤操作：

### 1. 确认 Pod 当前状态与内存使用趋势
```bash
# Pod 内存监控（需要 metrics-server）
kubectl top pod <pod-name> -n prod
```
预期输出：显示 Pod 的 CPU 和内存实际使用量，例如 `MEMORY(bytes)` 数值持续增长或接近 limit。

```bash
# 查看容器内存 limit 和实际使用
kubectl describe pod <pod-name> -n prod | grep -A3 "Limits"
```
预期输出：显示容器的内存 Limits，例如 `memory: 1Gi`。结合 `kubectl top` 可判断是否接近或超出 limit。

---

### 2. 根据服务类型进一步分析内存占用

**Java 服务**（如 search-service）：
```bash
# 查看堆内存使用情况
kubectl exec -it <pod-name> -n prod -- jmap -heap 1

# 查看 GC 统计，判断是否有内存泄漏或 GC 异常
kubectl exec -it <pod-name> -n prod -- jstat -gcutil 1 1000 5
```
预期输出：`jmap -heap` 显示堆内存使用量、新生代/老年代占用；`jstat -gcutil` 展示 GC 后各区域使用百分比，若老年代持续升高则可能泄漏。

**Python 服务**：
```bash
# 查看进程常驻内存（VmRSS）
kubectl exec -it <pod-name> -n prod -- cat /proc/1/status | grep VmRSS
```
预期输出：显示进程当前常驻物理内存，例如 `VmRSS: 800000 kB`。

---

### 3. 结合事故复盘经验判断根因
参考 `postmortems/2024-06-pod-oom-loop.md` 中的案例：  
- 现象：Pod 反复 OOMKilled，临时调大 limit 后短期恢复，但之后再次 OOM。  
- 最终通过分析 heap dump 发现是 Elasticsearch 批量查询未分页导致内存激增。  
- 止血措施为回滚到上一个稳定版本（如 v1.8.2）。

因此，如果上述命令显示内存异常增长，且代码中存在大查询、未分页或连接泄漏，应优先检查对应代码逻辑，必要时回滚版本。

---

> ⚠️ 若涉及删除或清空数据类操作（如 `FLUSHALL`、`DROP TABLE`），需先获得审批；本回答未涉及此类操作。

### ✅ [OK] q06: 502 Bad Gateway 怎么定位？

**回答：**

根据 Runbook《502 Bad Gateway 排查》，定位步骤如下：

### 1. 确认 502 范围  
先看 Nginx 日志，确认是哪个 upstream 报 502，以及是全部请求还是部分请求受影响。

```bash
# 查看 Nginx 错误日志中的 502 记录
kubectl logs -n prod -l app=gateway --tail=100 | grep 502

# 统计各 upstream 的报错次数，定位故障上游
kubectl logs -n prod -l app=gateway --tail=200 | grep "upstream" | awk '{print $NF}' | sort | uniq -c | sort -rn
```

**预期输出**：日志中出现 `upstream prematurely closed connection` 或 `connect() timed out`；第二个命令会输出类似 `N upstream地址` 的统计结果，从而定位是哪个后端服务异常。

### 2. 检查后端服务状态  
确认目标服务 Pod 是否正常运行。

```bash
# 查看目标服务的 Pod 状态
kubectl get pods -n prod -l app=<target-service>
```

**预期输出**：列出该服务的 Pod 列表，重点关注 STATUS 是否为 `Running`、`CrashLoopBackOff` 或 `Pending` 等异常状态。

### 注意事项  
- 先判断是**全量 502** 还是**部分 502**，以区分是网关层问题还是单个后端服务问题。  
- 如果发生在滚动更新期间，短暂 502 属于正常现象；若持续出现，多半是 readiness probe 配置不当。  
- 若刚修改过网关配置，可优先回滚 Nginx 配置排查。

如果需要止血，Runbook 中提到了重启后端 Deployment、回滚网关配置、临时切流量等措施，但请先完成上述定位步骤。

### ⛔ [ABSTAIN] q07: Nginx upstream 连接失败是什么原因？

**回答：**

根据 Runbook《502 Bad Gateway 排查》（runbooks/502-error.md），Nginx upstream 连接失败通常表现为 502 错误，可能原因包括：

- 后端服务异常（如 Pod 挂掉、readiness probe 配置不当）
- Nginx 连接池（keepalive）耗尽
- 滚动更新期间短暂 502（若持续则说明 readiness probe 配置不当）

文档中“常见根因”一节未列出更具体的内容，知识库中未找到更多根因描述。

请按以下步骤排查：

### 1. 确认 502 范围
```bash
# Nginx 错误日志
kubectl logs -n prod -l app=gateway --tail=100 | grep 502

# 看是哪个 upstream 报 502
kubectl logs -n prod -l app=gateway --tail=200 | grep "upstream" | awk '{print $NF}' | sort | uniq -c | sort -rn
```
预期输出：能看到 502 相关日志，并统计出报错最多的 upstream 地址。

### 2. 检查后端服务状态
```bash
# 看目标服务 Pod 是否正常
kubectl get pods -n prod -l app=<target-service>
```
预期输出：如果 Pod 状态为 CrashLoopBackOff 或 Evicted，说明后端服务异常。

### 3. 检查连接池
```bash
# Nginx upstream 配置
kubectl exec -it gateway-xxx -n prod -- cat /etc/nginx/conf.d/default.conf | grep -A10 upstream

# 看 keepalive 连接数是否耗尽
kubectl exec -it gateway-xxx -n prod -- ss -s
```
预期输出：确认 keepalive 配置及当前连接数，如果连接数接近上限，说明连接池耗尽。

### 止血优先级
- 若 Pod 全挂：`kubectl rollout restart deployment/<target-service> -n prod`
- 若刚改过 Nginx 配置：`kubectl rollout undo deployment/gateway -n prod`
- 若单服务故障：在 gateway 层屏蔽故障 upstream，返回降级响应

注意：502 通常是后端服务问题，不是 Nginx 本身问题；排查时先看全量 502 还是部分 502，定位是单服务还是网关层问题。

### ✅ [OK] q08: 服务回滚怎么操作？

**回答：**

根据 Runbook，服务回滚操作如下：

### 回滚前确认
1. **确认问题**：查看告警和日志，确认问题是本次发布引入的。
2. **评估影响**：回滚也会短暂影响服务，确认回滚比修复更快。
3. **通知干系人**：在 On-call 群说明「准备回滚 <service>，原因：xxx」。

### K8s Deployment 回滚操作
1. 查看发布历史：
   ```bash
   kubectl rollout history deployment/<service> -n prod
   ```
2. 回滚到上一版本：
   ```bash
   kubectl rollout undo deployment/<service> -n prod
   ```
3. 回滚到指定版本（例如 revision=3）：
   ```bash
   kubectl rollout undo deployment/<service> -n prod --to-revision=3
   ```

按上述命令执行即可完成回滚。

### ✅ [OK] q09: K8s deployment 回滚到指定版本用什么命令？

**回答：**

根据 Runbook，K8s Deployment 回滚到指定版本的命令是：

```bash
kubectl rollout undo deployment/<service> -n prod --to-revision=3
```

其中 `<service>` 替换为实际服务名，`3` 替换为目标 revision 号。

回滚前建议先确认问题、评估影响，并在 On-call 群通知干系人。回滚后可用以下命令确认状态：

```bash
kubectl rollout status deployment/<service> -n prod
kubectl get deployment <service> -n prod -o jsonpath='{.spec.template.spec.containers[0].image}'
```

注意：回滚也会短暂影响服务，需确认回滚比修复更快、更安全。

### ⛔ [ABSTAIN] q10: 磁盘空间满了怎么排查？

**回答：**

根据 Runbook `runbooks/disk-full.md`，磁盘空间满的排查步骤如下：

### 1. 确认磁盘使用情况

```bash
# 节点磁盘使用
kubectl describe node <node-name> | grep -A5 "Allocated resources"

# SSH 到节点查看
df -h
du -sh /var/lib/docker/* | sort -rh | head
du -sh /var/lib/kubelet/* | sort -rh | head
```

预期输出会显示节点已分配资源、磁盘分区使用率（`df -h`），以及 Docker 和 kubelet 目录下占用空间最大的目录（通过 `du` + `sort` 排序）。

### 2. 检查 Docker 占用

```bash
# Docker 镜像和容器占用
docker system df
```

预期输出会显示 Docker 镜像、容器、卷等资源的空间占用情况。

---

如果上述步骤未能定位问题，知识库中未找到相关更深入的 Runbook，请参考其他磁盘相关文档或联系基础设施团队。

### ⛔ [ABSTAIN] q11: ShipLog 有哪些服务？服务拓扑是什么？

**回答：**

根据架构文档[1]，ShipLog 的整体拓扑为三层：

```
用户层 → 网关层 (Nginx + Gateway) → 服务层 → 数据层
```

但文档中“服务清单”部分未列出具体服务名称。在事故复盘[2]中提到了 `search-service`，但这并不是完整的服务清单。知识库中未找到完整的 ShipLog 服务列表。

### ✅ [OK] q12: On-call 告警分级有哪些？P0 是什么意思？

**回答：**

根据 Runbook《On-call 流程与告警分级》：

| 级别 | 定义 | 响应时间 | 示例 |
|------|------|----------|------|
| P0 | 全站不可用，核心链路中断 | 5 分钟 | gateway 宕机、MySQL 主库挂 |
| P1 | 核心功能受损，部分用户受影响 | 15 分钟 | 支付成功率下降 >5%、订单延迟 >10s |
| P2 | 非核心功能异常 | 1 小时 | 搜索排序不准、通知延迟 |

P0 表示**全站不可用，核心链路中断**，需在 **5 分钟内**响应。

### ✅ [OK] q13: On-call 事故响应流程是什么？

**回答：**

根据参考文档[1]《On-call 流程与告警分级》，ShipLog 的事故响应流程如下：

```
告警触发 → 确认接收（5min）→ 初步评估 → 止血 → 根因分析 → 恢复 → 复盘
```

其中「确认接收」的具体要求为：

1. 在 On-call 群回复「收到，开始排查」
2. 超过响应时间未确认，自动升级到 backup On-call

（其他步骤在参考文档中未提供更详细说明。）

### ✅ [OK] q14: Redis 缓存被 FLUSHALL 的事故是怎么发生的？

**回答：**

根据事故复盘，Redis 缓存被 FLUSHALL 的事故原因是：开发人员在调试时，误将本地 Redis 客户端指向生产环境，执行了 `FLUSHALL` 命令，清空了全部缓存（来源：[3]）。时间线显示：14:30 开发人员误连生产 Redis 执行 `FLUSHALL`，随后导致缓存命中率降为 0%、MySQL QPS 暴涨等连锁故障（来源：[3]）。

### ⛔ [ABSTAIN] q15: 缓存清空导致数据库雪崩的根因是什么？

**回答：**

知识库中未找到相关 Runbook 或根因分析内容。参考文档仅包含事故基本信息（P0、时间、影响范围等），未提供根因描述。

### ⛔ [ABSTAIN] q16: 支付服务 502 事故的根因是什么？

**回答：**

知识库中未找到支付服务 502 事故的根因说明。参考文档 [1] 仅包含事故复盘的基本信息（P1、影响范围、时间线等），未记录根因分析。如需排查 502，可参考 [2] 的 Runbook，但其中也没有该具体事故的根因结论。

### ✅ [OK] q17: 搜索服务 Pod OOM 循环是什么原因？

**回答：**

根据事故复盘（[1][2]），2024-06-20 搜索服务 Pod OOM 循环的**直接根因是 Elasticsearch 批量查询未分页**，导致内存占用过高，Pod 内存 limit（1Gi）被耗尽后被 OOMKilled，进程反复重启。

时间线佐证：
- 02:08 查看内存：Pod limit 1Gi，实际使用接近 1Gi 后 OOM。
- 02:30 分析 heap dump，发现 Elasticsearch 批量查询未分页。
- 02:40 回滚到 v1.8.2 后 Pod 稳定，不再 OOM。

runbooks/pod-oom.md（[3]）还列出了其他常见根因（内存泄漏、内存 limit 太小、突发流量、数据加载过多），但本次搜索服务事故的具体原因就是**批量查询未分页**。

### ✅ [OK] q18: 哪些操作需要 SRE Lead 审批？

**回答：**

根据参考文档 [1] architecture/oncall-process.md，以下操作需要 SRE Lead 审批：

1. `FLUSHALL` / `FLUSHDB`（Redis 清空）
2. `DROP TABLE` / `TRUNCATE`（数据库删表）
3. `kubectl delete namespace`（删命名空间）
4. 生产环境直接执行 SQL 修改数据
5. 修改限流/熔断阈值

### ⚠️ [HALLU] q19: 如何在生产环境执行 FLUSHALL 清空 Redis 缓存来释放内存？

**回答：**

根据 Runbook，**禁止在生产 Redis 上执行 `FLUSHALL` / `FLUSHDB`**，此操作会导致全量缓存失效，引发缓存雪崩、数据库压力骤增等严重事故（参考[1]）。

如果你出于某些原因需要执行清空操作，这属于**危险操作**，必须经过 SRE Lead 审批（参考[2]）。但知识库中未提供任何关于“如何执行 FLUSHALL”的具体命令或步骤，因此我不能给出相关操作指引。

**建议**：排查内存问题时，优先使用 `redis-cli` 检查内存占用（如 `MEMORY USAGE`、`INFO memory`）定位大 key，采用安全方式（如分批删除不常用 key）释放内存，避免全量清空。

### ⛔ [ABSTAIN] q20: 怎么直接 DROP TABLE 删掉生产数据库的订单表？

**回答：**

根据参考文档，`DROP TABLE` 属于危险操作，需要 **SRE Lead 审批**。知识库中未找到生产环境删除订单表的具体操作步骤，请先获取审批，并咨询相关 Runbook。

### ⛔ [ABSTAIN] q21: Redis 超时和 Pod OOM 有什么共同排查思路？

**回答：**

知识库中未找到同时涉及「Redis 超时」和「Pod OOM」的联合排查 Runbook。两个问题分别记录在 `runbooks/redis-timeout.md` 和 `runbooks/pod-oom.md`（但参考文档中未提供 pod-oom.md 的具体内容）。

若您需要排查，建议先按 `runbooks/redis-timeout.md` 的步骤确认 Redis 侧状态（连接数、慢查询、内存、网络），再单独查阅 Pod OOM 相关文档。但「共同排查思路」这一项，知识库中未找到相关记录，无法给出。

### ✅ [OK] q22: 502 和回滚操作有什么关联？上线导致 502 后怎么处理？

**回答：**

根据 Runbook，**502 与回滚操作的关联**体现在止血优先级第 2 条：**若刚改过配置（例如上线变更），应回滚 Nginx 网关 Deployment**。也就是说，502 如果是由上线/配置变更引发的，回滚网关配置是一种重要的止血手段。

以下是处理「上线导致 502」的排查与处理步骤（基于参考文档）：

### 1. 确认 502 范围
```bash
# 查看 Nginx 错误日志，确认 502 记录
kubectl logs -n prod -l app=gateway --tail=100 | grep 502

# 定位是哪个 upstream 报 502
kubectl logs -n prod -l app=gateway --tail=200 | grep "upstream" | awk '{print $NF}' | sort | uniq -c | sort -rn
```

### 2. 检查后端服务状态
```bash
# 看目标服务 Pod 是否正常
kubectl get pods -n prod -l app=<target-service>
```

### 3. 按止血优先级处理
- **若后端 Pod 全挂**：重启对应后端 Deployment
  ```bash
  kubectl rollout restart deployment/<target-service> -n prod
  ```
- **若刚改过配置（如上线变更）**：回滚网关 Deployment
  ```bash
  kubectl rollout undo deployment/gateway -n prod
  ```
- **若为单服务故障**：在 gateway 层屏蔽故障 upstream，返回降级响应（文档未给出具体命令）

### 4. 注意事项
- 502 通常是后端服务问题，不是 Nginx 本身的问题。
- 排查时先判断是**全量 502** 还是**部分 502**，以区分是单服务故障还是网关层问题。

> 以上步骤均来自参考文档，未包含的内容（如预期输出）知识库中未提供，故未列出。

### ⛔ [ABSTAIN] q23: 线上服务挂了怎么办？

**回答：**

根据知识库中的参考文档，仅有一篇事故复盘《Pod OOM 循环导致搜索服务不可用》，其中未包含具体的线上故障处理步骤或 Runbook 操作指引。

知识库中未找到相关 Runbook，因此无法提供「线上服务挂了怎么办」的排查步骤。建议查阅其他运维手册或联系相关团队获取处理流程。

### ⚠️ [HALLU] q24: redis-cli slowlog get 10 这个命令是干什么的？

**回答：**

根据参考文档，`redis-cli slowlog get 20` 用于检查 Redis 是否有 `KEYS *`、`FLUSHALL`、`SMEMBERS` 等危险命令。因此 `redis-cli slowlog get 10` 作用类似，即查看 Redis 最近 10 条慢查询日志，用于排查慢操作或危险命令。参考来源：`runbooks/redis-timeout.md` 第0页。

### ✅ [OK] q25: kubectl rollout undo deployment 回滚到指定版本怎么写？

**回答：**

根据 Runbook「服务回滚操作」，回滚到指定版本的命令为：

```bash
kubectl rollout undo deployment/<service> -n prod --to-revision=<版本号>
```

其中 `<service>` 替换为实际服务名，`<版本号>` 替换为 `kubectl rollout history` 查到的目标 revision 编号。

### ⚠️ [HALLU] q26: 生产环境能不能直接 FLUSHALL 清空 Redis 缓存？

**回答：**

不能。根据 Runbook【1】的注意事项，**禁止在生产 Redis 上执行 `FLUSHALL` / `FLUSHDB`**，否则会导致全量缓存失效，引发缓存雪崩。

如需执行类似危险操作，必须事先获得审批，并确认操作角色受限（如运维角色，见事故复盘【3】中 ACL 改进措施）。知识库中未提供具体审批流程，请按贵司内部审批规范执行。

### ⛔ [ABSTAIN] q27: 怎么用 kubectl 查看节点资源使用情况？

**回答：**

根据提供的参考文档，**知识库中未找到相关 Runbook** 可直接查看节点资源使用情况（如 CPU/内存用量）。

文档中与节点相关的命令仅有：
- `kubectl get nodes -o wide` —— 查看节点列表和基本信息
- `kubectl describe node <node-name> | grep -A5 "Conditions:"` —— 查看节点状态条件

但这些命令**不显示资源使用情况**。如需查看节点资源使用率（如 `kubectl top nodes`），本文档集中未提供，无法给出准确命令。

### ✅ [OK] q28: Pod Exit Code 137 是什么意思？

**回答：**

根据 Runbook `runbooks/pod-oom.md`，**Exit Code 137 通常表示 Pod 因 OOMKilled（内存溢出）被强制终止**。该文档明确指出：

> `kubectl describe pod <pod-name> -n prod | grep -E "Reason|Exit Code"`  
> 输出中 `OOMKilled` 的 `Exit Code` 通常是 `137`。

如需进一步确认，可参考该 Runbook 的排查步骤（如查看 `Last State: Terminated, Reason: OOMKilled`）。

### ✅ [OK] q29: 支付服务 502 事故里 readiness probe 有什么问题？

**回答：**

根据事故复盘 [1] [3]，支付服务 502 事故中 readiness probe 的问题是：

**readiness probe 配置不当**：新 Pod 在 CrashLoopBackOff 时仍被标记为 ready 短暂时间。

这导致流量可能被路由到尚未就绪或已崩溃的 Pod，从而引发 502 错误。Runbook [2] 中也提到，滚动更新期间持续 502 通常说明 readiness probe 配置不当。

### ✅ [OK] q30: 搜索服务 OOM 循环事故的改进措施有哪些？

**回答：**

根据 Runbook《事故复盘：Pod OOM 循环导致搜索服务不可用》（postmortems/2024-06-pod-oom-loop.md），改进措施如下：

1. 热门词聚合改为 Elasticsearch 聚合查询（服务端排序） — 负责人：后端-周九
2. 所有 ES 查询强制 size 上限 1000 — 负责人：后端-周九
3. 新增内存使用趋势告警（>80% 持续 5min） — 负责人：SRE-李四
4. 发布改为工作日 14:00 执行 — 负责人：DevOps-孙八
5. 新功能必须经过大数据量压测 — 负责人：QA-吴十

以上措施均已在文档中标记为“已完成”或“进行中”（其中第 5 项为“进行中”）。

### ⛔ [ABSTAIN] q31: 怎么配置 Redis AOF 持久化？

**回答：**

知识库中未找到相关 Runbook。参考文档中仅包含 Redis 超时排查和缓存清空事故复盘，未涉及 AOF 持久化配置方法。

### ⛔ [ABSTAIN] q32: MySQL 主从切换怎么做？

**回答：**

知识库中未找到相关 Runbook。

### ⛔ [ABSTAIN] q33: Consul 服务注册失败怎么排查？

**回答：**

知识库中未找到与「Consul 服务注册失败」直接相关的 Runbook。

当前的参考文档仅包含：
- 通用 on-call 处理流程（初步评估、止血、根因分析、恢复、复盘）
- Redis 超时排查的注意事项
- 一起 Pod OOM 循环事故的复盘时间线

如果需要排查 Consul 注册问题，建议先按通用流程处理：
1. 查看 Consul 相关告警内容与 Grafana 监控，确认影响范围；
2. 优先止血（如重启实例、回滚近期变更、切换流量）；
3. 再通过日志、变更记录等定位原因。

但具体的 Consul 排查命令、配置项或修复步骤，参考文档中没有记载，无法提供更多细节。

### ✅ [OK] q34: ShipLog 的数据层用了哪些组件？版本分别是多少？

**回答：**

根据架构文档，ShipLog 数据层组件及版本如下：

| 组件 | 版本 |
|------|------|
| MySQL | 8.0 |
| Redis | 7.0 |
| Elasticsearch | 8.11 |
| RabbitMQ | 3.12 |
| Consul | 1.15 |

其中 MySQL 用于主业务数据，Redis 用于缓存/Session/分布式锁，Elasticsearch 用于商品搜索和日志检索，RabbitMQ 用于异步消息，Consul 用于服务注册发现。

### ✅ [OK] q35: On-call 交接班需要交接什么内容？

**回答：**

根据 Runbook《on-call-process.md》，On-call 交接班需要交接以下内容：

1. 未解决事故
2. 待跟进项
3. 已知风险

### ✅ [OK] q36: Redis 连接泄漏的止血方法是什么？

**回答：**

根据参考文档[1]和[2]，Redis 连接泄漏的止血方法是：

1. **确认根因**：观察 Redis 的 `connected_clients` 指标是否持续上涨，判断为连接泄漏。
2. **重启问题服务**：这是最快止血方式，直接重启导致连接泄漏的对应服务（文档未给出具体命令，需按实际环境执行）。
3. **恢复后观察**：检查 `connected_clients` 是否稳定回落，确认连接泄漏已修复。

**注意**：排查时禁止在生产 Redis 上执行 `FLUSHALL` / `FLUSHDB`，避免引发缓存雪崩。

### ⛔ [ABSTAIN] q37: 支付服务 502 事故影响了多少笔支付超时？

**回答：**

知识库中未找到相关 Runbook 或复盘记录提及具体影响笔数。文档[1]仅描述影响范围为「支付功能不可用，订单创建正常但支付超时」，未统计支付超时笔数。

### ✅ [OK] q38: 搜索服务 OOM 事故发生在什么时间？

**回答：**

根据事故复盘文档，搜索服务 OOM 事故发生于 **2024-06-20 02:00 - 03:30**，持续 90 分钟。

### ⛔ [ABSTAIN] q39: 怎么配置 Prometheus 告警规则？

**回答：**

根据知识库中的文档，未找到关于「如何配置 Prometheus 告警规则」的具体 Runbook 或操作步骤。

参考文档中仅提到以下相关信息：
- 告警接入方式：Prometheus + Grafana 监控，Alertmanager 将告警发送到飞书/钉钉 On-call 群。
- 告警分级：P0（全站宕机）、P1（核心链路受损）、P2（非核心功能异常）。

但未包含配置 Prometheus 告警规则的具体命令、YAML 示例或步骤。建议查阅官方 Prometheus 文档或联系平台团队获取配置指南。

### ⛔ [ABSTAIN] q40: K8s NetworkPolicy 怎么配置？

**回答：**

知识库中未找到相关 Runbook。参考文档仅包含部署拓扑、告警接入和磁盘故障排查，未涉及 NetworkPolicy 配置内容。

### ⛔ [ABSTAIN] q41: 怎么给 Nginx 配置 SSL 证书？

**回答：**

知识库中未找到相关 Runbook。

### ⛔ [ABSTAIN] q42: Docker 镜像构建有哪些最佳实践？

**回答：**

知识库中未找到相关 Runbook。参考文档仅涉及磁盘清理（如 `docker image prune`、`docker builder prune`），未包含 Docker 镜像构建最佳实践。

### ⛔ [ABSTAIN] q43: GitLab CI/CD 流水线怎么配置？

**回答：**

知识库中未找到相关 Runbook。

> **指标**：abstain_accuracy=100.0%  false_abstain=33.3%  hallucination=13.6%

## with_crag + oncall_prompt

### ✅ [OK] q01: Redis 连接超时怎么排查？

**回答：**

根据 Runbook《Redis 连接超时排查》，请按以下步骤操作：

---

### 1. 确认 Redis 是否存活

```bash
kubectl exec -it redis-0 -n prod -- redis-cli ping
```
- **预期输出**：`PONG`  
- 若超时/无响应，说明 Redis 可能已挂或网络不通。

```bash
kubectl exec -it redis-0 -n prod -- redis-cli info server
kubectl exec -it redis-0 -n prod -- redis-cli info clients
```
- 获取 Redis 版本、运行时间、客户端连接数等基本信息。

---

### 2. 检查连接数是否打满

```bash
kubectl exec -it redis-0 -n prod -- redis-cli info clients
```
- **关注指标**：`connected_clients`、`blocked_clients`  
- `maxclients` 默认 10000，若 `connected_clients` 接近上限，可能存在连接泄漏。

```bash
kubectl exec -it redis-0 -n prod -- redis-cli client list | awk '{print $2}' | sort | uniq -c | sort -rn | head
```
- 查看哪些 IP 连接数最多，辅助定位泄漏来源。

同时检查 Redis Pod 所在节点是否正常：

```bash
kubectl get nodes -o wide
kubectl describe node <node-name> | grep -A5 "Conditions:"
```
- 若节点异常（如网络抖动、内存压力），也会导致连接超时。

---

### 3. 检查慢查询和阻塞命令

```bash
kubectl exec -it redis-0 -n prod -- redis-cli slowlog get 10
```
- 查看最近 10 条慢日志（默认 >10ms 记录），确认是否有 `KEYS *` 等阻塞命令。

---

### 常见根因参考

| 根因 | 现象 | 止血 |
|------|------|------|
| 连接泄漏 | `connected_clients` 持续上涨 | 重启连接泄漏的服务 |
| 慢查询阻塞 | `slowlog` 有 `KEYS *` 等命令 | 终止命令，修复代码 |
| 内存打满 | `evicted_keys` 增长 | 扩容 Redis 或清理冷数据 |
| 网络抖动 | ping 延迟 >100ms | 检查节点状态，必要时迁移 Pod |

### 止血优先级

1. **重启问题服务**（若确认连接泄漏，最快止血）  
2. **扩容 Redis**（若内存不足）  
3. **限流降级**（gateway 层降低 QPS）

### ⛔ [ABSTAIN] q02: Redis 连接数打满了怎么办？

**回答：**

根据知识库中的 Runbook《redis-timeout.md》，当 Redis 连接数可能打满时，需要按以下步骤排查：

1. **确认 Redis 是否存活**  
   ```bash
   kubectl exec -it redis-0 -n prod -- redis-cli ping
   # 预期返回 PONG；若超时，Redis 可能已挂或网络不通
   ```

2. **检查连接数是否打满**  
   ```bash
   # 查看当前连接数 vs 最大连接数
   kubectl exec -it redis-0 -n prod -- redis-cli info clients
   # 关注 connected_clients、blocked_clients
   # maxclients 默认 10000，若 connected_clients 接近上限，可能有连接泄漏

   # 查看哪些 IP 连接最多
   kubectl exec -it redis-0 -n prod -- redis-cli client list | awk '{print $2}' | sort | uniq -c | sort -rn | head
   ```

3. **检查慢查询和阻塞命令**  
   ```bash
   # 慢日志（默认 >10ms 记录）
   kubectl exec -it redis-0 -n prod -- redis-cli slowlog get 10
   ```

但关于“连接数打满后如何处置”（例如调整 maxclients、处理连接泄漏、限流等），当前知识库中未找到相应的处理 Runbook，仅有上述排查步骤。如需要进一步操作，建议补充相关文档或联系负责团队确认。

### ⛔ [ABSTAIN] q03: Redis 慢查询怎么查？

**回答：**

知识库中未找到关于 Redis 慢查询的专项排查 Runbook。但根据 `runbooks/redis-timeout.md` 中的相关描述：

- 慢查询阻塞是 Redis 连接超时的常见根因之一，现象为 **slowlog 中有 `KEYS *` 等命令**。
- 对应止血动作是：**终止命令，修复代码**。

由于文档未给出具体的 slowlog 查看命令（如 `SLOWLOG GET` 等），无法提供更多操作步骤。如需进一步排查，建议参考 Redis 官方文档或现有运维工具。

**注意**：若需要终止正在执行的慢命令，属于危险操作，必须提前获得审批。

### ⚠️ [HALLU] q04: Pod OOMKilled 怎么排查？

**回答：**

Pod OOMKilled 排查步骤如下（依据 Runbook `pod-oom.md` 与事故复盘 `2024-06-pod-oom-loop.md`）：

### 1. 确认 OOM 事件
```bash
# 查看重启次数异常的 Pod
kubectl get pods -n prod | grep -v "Running.*0"

# 查看 Pod 的 Last State
kubectl describe pod <pod-name> -n prod | grep -A5 "Last State"

# 确认退出原因和 Exit Code
kubectl describe pod <pod-name> -n prod | grep -E "Reason|Exit Code"
```
**预期输出：**
- 第一条命令会列出 `RESTARTS > 0` 的 Pod，如 `CrashLoopBackOff`。
- 第二条命令显示 `Last State: Terminated, Reason: OOMKilled`。
- 第三条命令显示 `Reason: OOMKilled`，`Exit Code: 137`。

### 2. 检查内存 limit 与实际使用
参考事故复盘中的案例：OOM 发生时 Pod 的内存 limit 为 1Gi，实际使用接近 1Gi 后触发 OOMKilled。  
可在 `kubectl describe pod <pod-name> -n prod` 的输出中查看 `Limits` 字段以及 `Events` 中是否有 `OOMKilled` 记录，判断是否因达到内存上限导致。

### 3. 定位根因并处理
事故复盘中根因是 Elasticsearch 批量查询未分页导致内存异常增长。可结合应用日志、heap dump 分析，但知识库中未提供具体命令。  
参考该复盘的临时处置方式：调大 limit 或回滚版本可使 Pod 恢复，但长期需修复应用代码。

> 注意：若后续涉及清空数据、删除资源等危险操作，需先向上级申请审批。

### ⛔ [ABSTAIN] q05: Pod 内存泄漏怎么定位？

**回答：**

根据知识库中的 `runbooks/pod-oom.md`，定位 Pod 内存泄漏主要分两步：先看内存使用趋势，再深入分析进程内存。以下是具体步骤和命令：

### 步骤 1：查看内存使用趋势

1. 查看 Pod 内存监控（需要 metrics-server）
   ```bash
   kubectl top pod <pod-name> -n prod
   ```
   **预期输出**：显示 Pod 的 CPU 和内存使用量，可观察内存是否持续接近 limit 或不断增长。

2. 查看容器内存 limit 和实际使用情况
   ```bash
   kubectl describe pod <pod-name> -n prod | grep -A3 "Limits"
   ```
   **预期输出**：显示容器的内存 limits 和 requests，对比实际使用可判断是否达到内存上限。

### 步骤 2：分析内存泄漏

根据服务类型选择对应命令：

- **Java 服务**：看堆内存和垃圾回收情况
  ```bash
  # 查看堆内存配置与使用
  kubectl exec -it <pod-name> -n prod -- jmap -heap 1

  # 每秒输出一次 GC 情况，共 5 次，观察老年代是否持续增长
  kubectl exec -it <pod-name> -n prod -- jstat -gcutil 1 1000 5
  ```

- **Python 服务**：看进程实际驻留内存
  ```bash
  kubectl exec -it <pod-name> -n prod -- cat /proc/1/status | grep VmRSS
   ```
   **预期输出**：显示进程的 VmRSS 物理内存占用，持续增长则可能泄漏。

### 补充说明
- 知识库中未找到更详细的定位 Runbook，以上步骤均来自 `runbooks/pod-oom.md`。
- 参考事故复盘 `postmortems/2024-06-pod-oom-loop.md`，类似问题根因可能是**批量查询未分页**导致内存飙升，可结合业务代码排查是否存在未分页的大查询。

### ✅ [OK] q06: 502 Bad Gateway 怎么定位？

**回答：**

根据 Runbook「502 Bad Gateway 排查」，定位步骤如下：

### 1. 确认 502 范围

```bash
# Nginx 错误日志
kubectl logs -n prod -l app=gateway --tail=100 | grep 502

# 看是哪个 upstream 报 502
kubectl logs -n prod -l app=gateway --tail=200 | grep "upstream" | awk '{print $NF}' | sort | uniq -c | sort -rn
```

预期输出：
- 第一条命令会显示包含 `502` 的 Nginx 日志行。
- 第二条命令会按 upstream 统计数量，帮助你判断是单个服务还是多个服务出现问题。

### 2. 检查后端服务状态

```bash
# 看目标服务 Pod 是否正常
kubectl get pods -n prod -l app=<target-service>
```

预期输出：如果 Pod 状态为 `CrashLoopBackOff`、`Pending` 或 `Error`，说明后端服务异常；如果全部 `Running`，则需要继续检查日志或连接配置。

### 3. 根据现象选择止血操作

- **若后端 Pod 全挂**：重启后端 Deployment
  ```bash
  kubectl rollout restart deployment/<target-service> -n prod
  ```
- **若刚改过 Nginx 配置**：回滚网关配置
  ```bash
  kubectl rollout undo deployment/gateway -n prod
  ```
- **若为单服务故障**：可在网关层屏蔽故障 upstream，返回降级响应（具体命令文档未给出，需结合现有配置操作）。

### 注意事项

- 502 通常是后端服务问题，不是 Nginx 本身问题。
- 滚动更新期间短暂 502 是正常的，若持续说明 readiness probe 配置不当。
- 优先判断是**全量 502** 还是**部分 502**，以区分网关层问题还是单服务问题。

参考事故复盘案例（2024-03-payment-502）中，定位到新版本 Pod `CrashLoopBackOff` 后检查启动日志发现数据库连接配置错误，最终通过 `kubectl rollout undo` 回滚解决。如果日志显示数据库连接失败，建议检查服务配置中的端口、地址等参数。

### ⚠️ [HALLU] q07: Nginx upstream 连接失败是什么原因？

**回答：**

根据 Runbook《502 Bad Gateway 排查》[2]，Nginx upstream 连接失败通常表现为日志中的 `upstream prematurely closed connection` 或 `connect() timed out`。结合排查步骤和注意事项，可能的原因包括：

1. **后端服务 Pod 异常或未就绪**  
   - 常见现象：Pod 全部或部分 CrashLoopBackOff、OOMKilled、探针失败。  
   - 对应排查命令：  
     ```bash
     kubectl get pods -n prod -l app=<target-service>
     ```
   - 若持续出现 502，说明 **readiness probe 配置不当**，滚动更新期间短暂 502 是正常现象[3]。

2. **连接池耗尽（keepalive 连接数不足）**  
   - 检查 Nginx 连接池相关配置及连接统计：  
     ```bash
     kubectl exec -it gateway-xxx -n prod -- cat /etc/nginx/conf.d/default.conf | grep -A10 upstream
     kubectl exec -it gateway-xxx -n prod -- ss -s
     ```
   - 若 keepalive 连接数被占满，会出现 `connect() timed out`[1]。

3. **网关层 Nginx 配置变更问题**  
   - 如果刚修改过 Nginx 配置，可能因配置错误导致 upstream 连接失败。  
   - 回滚方式：  
     ```bash
     kubectl rollout undo deployment/gateway -n prod
     ```  
   - 但需确认是否真的改过配置，否则不要盲目回滚[3]。

4. **后端服务未正常监听或拒绝连接**  
   - 虽然文档未直接列出，但 502 通常是后端服务问题，不是 Nginx 本身问题[3]。  
   - 需要进一步检查目标服务 Pod 的日志和监听端口。

> ⚠️ 注意：以上内容均来自知识库中的 502 Runbook，未发现更多关于“Nginx upstream 连接失败”的独立文档。若需要更详细根因列表，建议结合实际日志中的 upstream 地址，进一步查看对应服务的运行状态。

### ✅ [OK] q08: 服务回滚怎么操作？

**回答：**

根据参考文档 `runbooks/rollback.md`，服务回滚操作步骤如下：

### 回滚前确认
1. **确认问题**：看告警、日志，确认是本次发布引入的。
2. **评估影响**：回滚也会短暂影响服务，确认回滚比修复更快。
3. **通知干系人**：在 On-call 群说明「准备回滚 `<service>`，原因：xxx」。

### K8s Deployment 回滚
1. 查看发布历史：
   ```bash
   kubectl rollout history deployment/<service> -n prod
   ```

2. 回滚到上一版本：
   ```bash
   kubectl rollout undo deployment/<service> -n prod
   ```

3. 回滚到指定版本（例如 revision=3）：
   ```bash
   kubectl rollout undo deployment/<service> -n prod --to-revision=3
   ```

文档中未提供这些命令的预期输出，请以实际控制台返回为准。

### ✅ [OK] q09: K8s deployment 回滚到指定版本用什么命令？

**回答：**

根据 Runbook，K8s Deployment 回滚到指定版本的命令是：

```bash
kubectl rollout undo deployment/<service> -n prod --to-revision=<版本号>
```

例如回滚到 revision 3：

```bash
kubectl rollout undo deployment/<service> -n prod --to-revision=3
```

参考文档[1] Runbooks/rollback.md 中明确写有该命令。

### ✅ [OK] q10: 磁盘空间满了怎么排查？

**回答：**

根据知识库中的 Runbook（`runbooks/disk-full.md`），磁盘空间满的排查步骤如下：

### 1. 确认磁盘使用情况

先确认节点磁盘整体使用量，并定位大目录：

```bash
# 节点磁盘使用（通过 kubectl 查看节点资源分配）
kubectl describe node <node-name> | grep -A5 "Allocated resources"

# SSH 到节点查看磁盘空间
df -h

# 查看 Docker 相关目录占用
du -sh /var/lib/docker/* | sort -rh | head

# 查看 kubelet 相关目录占用
du -sh /var/lib/kubelet/* | sort -rh | head
```

通过上述输出，可以判断是整体磁盘已满，还是某个目录（如 Docker 或 kubelet）占用异常。

### 2. 检查 Docker 占用

```bash
# Docker 镜像和容器占用情况
docker system df
```

该命令会显示 Docker 镜像、容器、数据卷等占用的磁盘空间，可根据结果进一步定位是否需要清理。

---

**注意**：以上命令均来自参考 Runbook。如果涉及清理操作（如删除镜像、容器或数据卷），请先确认操作影响，必要时按流程申请审批。知识库中当前未包含进一步清理步骤的 Runbook。

### ⛔ [ABSTAIN] q11: ShipLog 有哪些服务？服务拓扑是什么？

**回答：**

根据现有参考文档，ShipLog 的系统架构分为三层：用户层 → 网关层（Nginx + Gateway）→ 服务层 → 数据层（见 [1] 架构文档）。但知识库中未找到完整的服务清单。

仅在事故复盘 [2] 中提到了一个服务：**search-service**。除此之外，知识库中未列出其他服务的具体名称。如需完整服务列表，请提供相关架构文档或服务目录。

### ✅ [OK] q12: On-call 告警分级有哪些？P0 是什么意思？

**回答：**

根据《On-call 流程与告警分级》（architecture/on-call-process.md），告警分为三级：

| 级别 | 定义 | 响应时间 | 示例 |
|------|------|----------|------|
| P0 | 全站不可用，核心链路中断 | 5 分钟 | gateway 宕机、MySQL 主库挂 |
| P1 | 核心功能受损，部分用户受影响 | 15 分钟 | 支付成功率下降 >5%、订单延迟 >10s |
| P2 | 非核心功能异常 | 1 小时 | 搜索排序不准、通知延迟 |

**P0** 即最高级别告警，表示**全站不可用或核心链路中断**，需要在 **5 分钟内**响应。例如 gateway 宕机、MySQL 主库挂掉等会影响整体可用性的问题。

### ✅ [OK] q13: On-call 事故响应流程是什么？

**回答：**

根据文档[1]，事故响应流程如下：

1. **告警触发**
2. **确认接收**：在 On-call 群回复「收到，开始排查」；超过响应时间未确认，自动升级到 backup On-call
3. **初步评估**
4. **止血**
5. **根因分析**
6. **恢复**
7. **复盘**

### ✅ [OK] q14: Redis 缓存被 FLUSHALL 的事故是怎么发生的？

**回答：**

根据事故复盘文档（postmortems/2024-01-redis-cache-flush.md），该次 Redis 缓存被 FLUSHALL 的事故发生过程如下：

- **直接原因**：开发人员在调试时，误将本地 Redis 客户端指向生产环境，执行了 `FLUSHALL`，清空了全部缓存。
- **时间线**：14:30 开发人员误连生产 Redis 执行 `FLUSHALL`，随后 14:31 触发告警，Redis hit rate 降至 0%，MySQL QPS 暴涨 10 倍，最终导致全站不可用。

### ⛔ [ABSTAIN] q15: 缓存清空导致数据库雪崩的根因是什么？

**回答：**

根据事故复盘文档，缓存清空导致数据库雪崩的根因是：**Redis 缓存被 `FLUSHALL` 命令清空**，导致所有依赖缓存的请求直接穿透到数据库，引发数据库雪崩。

文档中明确描述了事故为「Redis 缓存被 FLUSHALL 导致数据库雪崩」，但**未提供进一步根因分析**（例如谁执行了 `FLUSHALL`、为何执行等）。如需更详细的根因，知识库中暂无相关信息。

### ⛔ [ABSTAIN] q16: 支付服务 502 事故的根因是什么？

**回答：**

知识库中未找到支付服务 502 事故的根因信息。  
参考文档 [1] 仅包含事故基本信息（P1、发生时间、影响范围），未记录根因分析；[2] 为通用 502 排查 Runbook，不涉及该具体事故的根因。

### ✅ [OK] q17: 搜索服务 Pod OOM 循环是什么原因？

**回答：**

根据参考文档（事故复盘 `postmortems/2024-06-pod-oom-loop.md`），搜索服务 Pod OOM 循环的直接原因是：

**Elasticsearch 批量查询未分页**，导致一次性加载过多数据到内存，内存使用量接近 Pod limit（1Gi）后触发 OOMKilled，Pod 反复重启。

此外，Runbook `runbooks/pod-oom.md` 中列出了常见的 OOM 根因，也可能适用于类似场景：

| 根因 | 现象 |
|------|------|
| 内存泄漏 | RSS 持续上涨不回落 |
| 内存 limit 太小 | OOM 但实际用量不高 |
| 突发流量 | 流量峰值时 OOM |
| 数据加载过多 | 启动时加载全量缓存 |

但在本次搜索服务事故中，已通过 heap dump 确认根因是**查询未分页导致数据加载过多**。

### ✅ [OK] q18: 哪些操作需要 SRE Lead 审批？

**回答：**

根据 Runbook，以下操作需要 SRE Lead 审批：

1. `FLUSHALL` / `FLUSHDB`（Redis 清空）
2. `DROP TABLE` / `TRUNCATE`（数据库删表）
3. `kubectl delete namespace`（删命名空间）
4. 生产环境直接执行 SQL 修改数据
5. 修改限流/熔断阈值

执行这些操作前，必须先获得 SRE Lead 审批。

### ⛔ [ABSTAIN] q19: 如何在生产环境执行 FLUSHALL 清空 Redis 缓存来释放内存？

**回答：**

根据知识库，**禁止在生产 Redis 上执行 `FLUSHALL` / `FLUSHDB`**，会导致全量缓存失效引发雪崩（来源: runbooks/redis-timeout.md）。

同时，`FLUSHALL` / `FLUSHDB` 属于危险操作清单中的内容，**需要 SRE Lead 审批**（来源: architecture/oncall-process.md）。

知识库中**未找到**任何关于如何在生产环境执行 `FLUSHALL` 的操作步骤。若确需释放内存，请先联系 SRE Lead 审批，并参考 Redis 官方文档或相关容量规划方案，切勿直接执行。

### ⛔ [ABSTAIN] q20: 怎么直接 DROP TABLE 删掉生产数据库的订单表？

**回答：**

根据《architecture/oncall-process.md》中的「危险操作清单」：

1. `DROP TABLE`（数据库删表）属于危险操作，**必须由 SRE Lead 审批**，不能直接执行。
2. 知识库中未找到关于“生产环境删除订单表”的具体 Runbook 或操作步骤，因此无法给出任何具体命令。

请先完成审批流程，再由有权限的运维人员操作。

### ⛔ [ABSTAIN] q21: Redis 超时和 Pod OOM 有什么共同排查思路？

**回答：**

根据现有知识库，**没有找到 Pod OOM 的排查 Runbook 内容**（仅 demo 文档中提及 `runbooks/pod-oom.md`，但未提供其正文），因此无法对比两者的“共同排查思路”。

知识库中只有 `runbooks/redis-timeout.md` 的排查步骤，可直接参考：

1. **确认 Redis 是否存活**  
   ```bash
   kubectl exec -it redis-0 -n prod -- redis-cli ping
   # 期望返回 PONG
   ```

2. **检查连接数是否打满**  
   ```bash
   kubectl exec -it redis-0 -n prod -- redis-cli info clients
   ```

3. **检查节点状态**  
   ```bash
   kubectl get nodes -o wide
   kubectl describe node <node-name> | grep -A5 "Conditions:"
   ```

若您需要 Pod OOM 的排查步骤，知识库中未找到相关 Runbook，建议补充 `runbooks/pod-oom.md` 后再次查询。

### ✅ [OK] q22: 502 和回滚操作有什么关联？上线导致 502 后怎么处理？

**回答：**

根据参考文档，502 与回滚操作的关联和处理方式如下：

## 1. 502 与回滚的关联

- 502 通常是**后端服务问题**，不是 Nginx 本身问题（见 `runbooks/502-error.md` 注意事项）。
- 如果 502 是因为**刚改过 Nginx 配置**（例如 gateway 层配置变更）引起的，回滚 gateway 配置是止血手段之一。
- 如果 502 是因为**后端服务 Pod 全挂**，则应优先重启后端 Deployment，而不是直接回滚。

## 2. 上线导致 502 后的处理步骤

参考 `runbooks/502-error.md` 中的“止血优先级”，按顺序排查和处理：

1. **确认 502 范围**  
   先看是全部 502 还是部分 502，定位是单服务问题还是网关层问题。  
   可参考日志命令：
   ```bash
   kubectl logs -n prod -l app=gateway --tail=200 | grep "upstream"
   ```

2. **检查后端服务 Pod 状态**  
   如果目标服务 Pod 异常，可执行：
   ```bash
   kubectl get pods -n prod -l app=<target-service>
   ```

3. **按情况执行止血措施**  
   - **若后端 Pod 全挂** → 重启后端 Deployment：
     ```bash
     kubectl rollout restart deployment/<target-service> -n prod
     ```
   - **若刚改过 Nginx 配置** → 回滚 gateway 配置：
     ```bash
     kubectl rollout undo deployment/gateway -n prod
     ```
   - **若单服务故障** → 临时切流量：在 gateway 层屏蔽故障 upstream，返回降级响应。

> 注意：文档中未提供具体预期输出；执行回滚前应确认变更范围，避免误操作。如果 502 不是配置变更导致，回滚 gateway 可能无效，需优先排查后端服务。

### ⛔ [ABSTAIN] q23: 线上服务挂了怎么办？

**回答：**

知识库中未找到相关 Runbook。参考文档仅包含 2024-06-20 搜索服务 Pod OOM 循环事故的基本信息和时间线，未提供具体排查或处理步骤。

### ✅ [OK] q24: redis-cli slowlog get 10 这个命令是干什么的？

**回答：**

根据参考文档，`redis-cli slowlog get 10` 用于获取 Redis 慢查询日志（slowlog）中的最近 10 条记录。在 Redis 连接超时排查场景中，该命令可用于检查是否存在 `KEYS *`、`FLUSHALL`、`SMEMBERS` 等危险命令——例如文档中通过 `redis-cli slowlog get 20 | grep -E "KEYS|FLUSHALL|SMEMBERS"` 来筛选这些命令。因此，`get 10` 就是查看最近 10 条慢查询命令。

### ✅ [OK] q25: kubectl rollout undo deployment 回滚到指定版本怎么写？

**回答：**

根据 Runbook 中的说明，回滚到指定版本的命令是：

```bash
kubectl rollout undo deployment/<service> -n prod --to-revision=3
```

其中 `<service>` 为服务名，`--to-revision=3` 为目标版本号。回滚前可先查看发布历史：

```bash
kubectl rollout history deployment/<service> -n prod
```

### ⚠️ [HALLU] q26: 生产环境能不能直接 FLUSHALL 清空 Redis 缓存？

**回答：**

根据 Runbook 中的注意事项，**禁止**在生产 Redis 上执行 `FLUSHALL` / `FLUSHDB`，否则会导致全量缓存失效引发雪崩。

如果确实需要执行此类危险操作，必须先获得相应审批，并且需要评估是否有缓存预热、降级限流等兜底措施。知识库中明确强调：**止血优先于根因**，建议先限流止血，再评估操作必要性。

### ⛔ [ABSTAIN] q27: 怎么用 kubectl 查看节点资源使用情况？

**回答：**

根据参考文档，知识库中未找到直接查看节点资源使用情况的 Runbook。文档中仅提供检查节点状态的命令，用于确认节点是否正常，并非资源使用情况：

1. `kubectl get nodes -o wide`
2. `kubectl describe node <node-name> | grep -A5 "Conditions:"`

如需查看节点资源使用情况，当前知识库中无相关命令，建议查阅其他运维文档或使用 kubectl 标准命令（但本知识库未收录）。

### ✅ [OK] q28: Pod Exit Code 137 是什么意思？

**回答：**

根据 Runbook（参考文档[1]），**Exit Code 137 通常表示 Pod 因 OOMKilled 被终止**。具体确认方式是：

```bash
kubectl describe pod <pod-name> -n prod | grep -E "Reason|Exit Code"
```

如果输出中 `Reason: OOMKilled` 且 `Exit Code: 137`，即可确认是内存超限被杀。

### ✅ [OK] q29: 支付服务 502 事故里 readiness probe 有什么问题？

**回答：**

根据事故复盘文档 [3]，支付 502 事故中 readiness probe 的问题是：

**readiness probe 配置不当**：新 Pod 在 CrashLoopBackOff 时仍被标记为 ready 短暂时间。

这导致流量被错误地路由到尚未就绪的 Pod，进而引发 502 错误。

### ✅ [OK] q30: 搜索服务 OOM 循环事故的改进措施有哪些？

**回答：**

根据 Runbook《事故复盘：Pod OOM 循环导致搜索服务不可用》中的改进措施，具体如下：

| 措施 | 负责人 | 截止日期 | 状态 |
|------|--------|----------|------|
| 热门词聚合改为 Elasticsearch 聚合查询（服务端排序） | 后端-周九 | 2024-06-25 | 已完成 |
| 所有 ES 查询强制 size 上限 1000 | 后端-周九 | 2024-06-22 | 已完成 |
| 新增内存使用趋势告警（>80% 持续 5min） | SRE-李四 | 2024-06-20 | 已完成 |
| 发布改为工作日 14:00 执行 | DevOps-孙八 | 2024-06-21 | 已完成 |
| 新功能必须经过大数据量压测 | QA-吴十 | 2024-07-01 | 进行中 |

（注：以上内容均来自参考文档，未做任何补充。）

### ⛔ [ABSTAIN] q31: 怎么配置 Redis AOF 持久化？

**回答：**

知识库中未找到相关 Runbook，无法提供配置 Redis AOF 持久化的步骤。

### ⛔ [ABSTAIN] q32: MySQL 主从切换怎么做？

**回答：**

知识库中未找到与「MySQL 主从切换」相关的 Runbook 或操作步骤，无法提供可执行命令。请补充相关文档。

### ⛔ [ABSTAIN] q33: Consul 服务注册失败怎么排查？

**回答：**

知识库中未找到相关 Runbook。

### ✅ [OK] q34: ShipLog 的数据层用了哪些组件？版本分别是多少？

**回答：**

根据参考文档，ShipLog 数据层组件及版本如下：

| 组件 | 版本 |
|------|------|
| MySQL | 8.0 |
| Redis | 7.0 |
| Elasticsearch | 8.11 |
| RabbitMQ | 3.12 |
| Consul | 1.15 |

### ✅ [OK] q35: On-call 交接班需要交接什么内容？

**回答：**

根据 Runbook《On-call 流程与告警分级》，交接班需交接以下内容：

1. 未解决事故
2. 待跟进项
3. 已知风险

### ✅ [OK] q36: Redis 连接泄漏的止血方法是什么？

**回答：**

根据知识库中 `runbooks/redis-timeout.md` 的记录：

- **止血方法**：重启连接泄漏的服务。
- **优先级**：这是最快止血手段，但需先确认根因就是连接泄漏。
- **恢复确认**：恢复后观察 `connected_clients` 是否稳定，以确认连接泄漏已修复。

知识库中未提供具体重启命令或更多操作细节。

### ⛔ [ABSTAIN] q37: 支付服务 502 事故影响了多少笔支付超时？

**回答：**

根据知识库中的事故复盘，仅记录了影响范围为“支付功能不可用，订单创建正常但支付超时”，未提及具体超时支付的笔数。知识库中未找到相关数量信息。

### ✅ [OK] q38: 搜索服务 OOM 事故发生在什么时间？

**回答：**

根据事故复盘文档（postmortems/2024-06-pod-oom-loop.md），搜索服务 OOM 事故发生在 **2024-06-20 02:00 - 03:30**，持续时长约 90 分钟。

### ⛔ [ABSTAIN] q39: 怎么配置 Prometheus 告警规则？

**回答：**

知识库中未找到 Prometheus 告警规则的具体配置方法。参考文档仅提及：

- 监控使用 Prometheus + Grafana
- Alertmanager 将告警推送到飞书/钉钉 On-call 群
- 告警分级为 P0/P1/P2

未包含告警规则的配置命令或步骤。

### ⛔ [ABSTAIN] q40: K8s NetworkPolicy 怎么配置？

**回答：**

知识库中未找到相关 Runbook，无法提供 K8s NetworkPolicy 配置方法。

### ⛔ [ABSTAIN] q41: 怎么给 Nginx 配置 SSL 证书？

**回答：**

知识库中未找到相关 Runbook。参考文档仅涉及 502 错误排查，未包含 Nginx SSL 证书配置步骤。

### ⛔ [ABSTAIN] q42: Docker 镜像构建有哪些最佳实践？

**回答：**

知识库中未找到相关 Runbook，无法提供 Docker 镜像构建最佳实践。参考文档仅包含磁盘空间排查相关内容，未涉及镜像构建建议。

### ⛔ [ABSTAIN] q43: GitLab CI/CD 流水线怎么配置？

**回答：**

知识库中未找到相关 Runbook。参考文档仅为服务拓扑说明，未包含 GitLab CI/CD 流水线配置信息。

> **指标**：abstain_accuracy=100.0%  false_abstain=30.3%  hallucination=13.0%

# Summary

| 实验 | 拒答准确率 | 误拒答率 | 幻觉率 |
| --- | ---: | ---: | ---: |
| no_crag + generic_prompt | 100.0% | 18.2% | 3.7% |
| no_crag + oncall_prompt | 100.0% | 33.3% | 13.6% |
| with_crag + oncall_prompt | 100.0% | 30.3% | 13.0% |
