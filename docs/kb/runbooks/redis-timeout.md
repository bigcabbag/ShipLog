# Runbook: Redis 连接超时排查

## 症状

- 告警：`redis_connection_timeout` 触发
- 日志：`redis: connection timeout` / `redis: dial tcp: i/o timeout`
- 表现：依赖 Redis 的服务响应变慢或报错

## 排查步骤

### 1. 确认 Redis 是否存活

```bash
# 登录 Redis Pod
kubectl exec -it redis-0 -n prod -- redis-cli ping
# 期望返回 PONG；若超时，Redis 可能已挂或网络不通

# 查 Redis 基本信息
kubectl exec -it redis-0 -n prod -- redis-cli info server
kubectl exec -it redis-0 -n prod -- redis-cli info clients
```

### 2. 检查连接数是否打满

```bash
# 当前连接数 vs 最大连接数
kubectl exec -it redis-0 -n prod -- redis-cli info clients
# 关注：connected_clients、blocked_clients
# maxclients 默认 10000，若 connected_clients 接近上限，可能有连接泄漏

# 查看哪些 IP 连接最多
kubectl exec -it redis-0 -n prod -- redis-cli client list | awk '{print $2}' | sort | uniq -c | sort -rn | head
```

### 3. 检查慢查询和阻塞命令

```bash
# 慢日志（默认 >10ms 记录）
kubectl exec -it redis-0 -n prod -- redis-cli slowlog get 10

# 是否有 KEYS * / FLUSHALL 等危险命令
kubectl exec -it redis-0 -n prod -- redis-cli slowlog get 20 | grep -E "KEYS|FLUSHALL|SMEMBERS"
```

### 4. 检查内存是否打满

```bash
kubectl exec -it redis-0 -n prod -- redis-cli info memory
# 关注：used_memory_human、maxmemory、evicted_keys
# 若 evicted_keys 持续增长，说明内存不足在淘汰 key
```

### 5. 检查网络

```bash
# 从应用 Pod 测试到 Redis 的连通性和延迟
kubectl exec -it order-service-xxx -n prod -- bash -c "time redis-cli -h redis -p 6379 ping"

# 检查 Redis Pod 所在节点是否正常
kubectl get nodes -o wide
kubectl describe node <node-name> | grep -A5 "Conditions:"
```

## 常见根因

| 根因 | 现象 | 止血 |
|------|------|------|
| 连接泄漏 | connected_clients 持续涨 | 重启连接泄漏的服务 |
| 慢查询阻塞 | slowlog 有 KEYS * 等命令 | 终止命令，修复代码 |
| 内存打满 | evicted_keys 增长 | 扩容 Redis 或清理冷数据 |
| 网络抖动 | ping 延迟 >100ms | 检查节点状态，必要时迁移 Pod |

## 止血优先级

1. **重启问题服务**（最快止血，若确认连接泄漏）
2. **扩容 Redis**（若内存不足）
3. **限流降级**（gateway 层降低 QPS）

## 注意事项

- **禁止**在生产 Redis 上执行 `FLUSHALL` / `FLUSHDB`，会导致全量缓存失效引发雪崩
- 排查时优先用 `redis-cli`，避免在应用代码里加调试逻辑
- 恢复后观察 `connected_clients` 是否稳定，确认连接泄漏已修复
