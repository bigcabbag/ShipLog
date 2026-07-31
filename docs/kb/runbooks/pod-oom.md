# Runbook: Pod OOMKilled 排查

## 症状

- 告警：`pod_oomkilled` 或 `container_restart_count` 触发
- `kubectl get pods` 显示 `RESTARTS > 0`
- `kubectl describe pod` 显示 `Last State: Terminated, Reason: OOMKilled`

## 排查步骤

### 1. 确认 OOM 事件

```bash
# 查看重启次数和原因
kubectl get pods -n prod | grep -v "Running.*0"
kubectl describe pod <pod-name> -n prod | grep -A5 "Last State"

# 确认是 OOMKilled 而非其他原因
kubectl describe pod <pod-name> -n prod | grep -E "Reason|Exit Code"
# OOMKilled 的 Exit Code 通常是 137
```

### 2. 查看内存使用趋势

```bash
# Pod 内存监控（需要 metrics-server）
kubectl top pod <pod-name> -n prod

# 查看容器内存 limit 和实际使用
kubectl describe pod <pod-name> -n prod | grep -A3 "Limits"
```

### 3. 分析内存泄漏

```bash
# Java 服务：看堆内存
kubectl exec -it <pod-name> -n prod -- jmap -heap 1
kubectl exec -it <pod-name> -n prod -- jstat -gcutil 1 1000 5

# Python 服务：看进程内存
kubectl exec -it <pod-name> -n prod -- cat /proc/1/status | grep VmRSS

# Go 服务：pprof
kubectl exec -it <pod-name> -n prod -- curl localhost:6060/debug/pprof/heap > heap.prof
go tool pprof heap.prof
```

### 4. 检查最近变更

```bash
# 看最近部署
kubectl rollout history deployment/<deployment> -n prod

# 看镜像版本是否变了
kubectl get deployment <deployment> -n prod -o jsonpath='{.spec.template.spec.containers[0].image}'
```

## 常见根因

| 根因 | 现象 | 止血 |
|------|------|------|
| 内存泄漏 | RSS 持续上涨不回落 | 重启 Pod，回滚到上个版本 |
| 内存 limit 太小 | OOM 但实际用量不高 | 调大 resources.limits.memory |
| 突发流量 | 流量峰值时 OOM | HPA 扩容 + 限流 |
| 数据加载过多 | 启动时加载全量缓存 | 改为分页加载或懒加载 |

## 止血优先级

1. **临时调大 memory limit**（最快止血）
   ```bash
   kubectl patch deployment <name> -n prod -p '{"spec":{"template":{"spec":{"containers":[{"name":"<container>","resources":{"limits":{"memory":"2Gi"}}}]}}}}'
   ```
2. **回滚到上个版本**（若确认是新版本引入的泄漏）
   ```bash
   kubectl rollout undo deployment/<name> -n prod
   ```
3. **HPA 扩容**（分流降低单 Pod 内存压力）

## 注意事项

- OOMKilled 后 Pod 会自动重启，但如果是内存泄漏会反复 OOM，形成 OOM 循环
- 调大 limit 是临时止血，长期要修代码或优化配置
- Java 服务注意 JVM 堆参数 `-Xmx` 不要超过 container memory limit
