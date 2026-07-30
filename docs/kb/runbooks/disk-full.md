# Runbook: 磁盘空间满排查

## 症状

- 告警：`disk_usage > 90%` 触发
- Pod 事件：`Evicted` (reason: NodeHasDiskPressure)
- 日志写入失败：`no space left on device`

## 排查步骤

### 1. 确认磁盘使用情况

```bash
# 节点磁盘使用
kubectl describe node <node-name> | grep -A5 "Allocated resources"

# SSH 到节点查看
df -h
du -sh /var/lib/docker/* | sort -rh | head
du -sh /var/lib/kubelet/* | sort -rh | head
```

### 2. 检查 Docker 占用

```bash
# Docker 镜像和容器占用
docker system df

# 清理无用镜像和停止的容器（谨慎，先确认）
docker image prune -a --filter "until=168h"
docker container prune

# 清理构建缓存
docker builder prune
```

### 3. 检查日志文件

```bash
# 查找大日志文件
find /var/log -type f -size +500M -exec ls -lh {} \;

# K8s Pod 日志（每个 Pod 的日志在 /var/log/pods/）
du -sh /var/log/pods/* | sort -rh | head

# 清理旧日志（保留最近 3 天）
find /var/log/pods -mtime +3 -delete
```

### 4. 检查 K8s 镜像和 Pod 残留

```bash
# 未使用的 ConfigMap 和 Secret
kubectl get cm -n prod | grep -v "kube-root"
kubectl get secrets -n prod | wc -l

# 已完成但未清理的 Pod
kubectl get pods -n prod --field-selector=status.phase=Succeeded
```

### 5. 检查应用自身产生的大文件

```bash
# 进入 Pod 检查
kubectl exec -it <pod-name> -n prod -- du -sh /tmp/* | sort -rh | head
kubectl exec -it <pod-name> -n prod -- du -sh /app/logs/* | sort -rh | head
```

## 常见根因

| 根因 | 现象 | 止血 |
|------|------|------|
| 日志文件未轮转 | /var/log 下大文件 | logrotate 或手动清理 |
| Docker 镜像堆积 | docker system df 占用大 | docker image prune |
| Pod 产生大临时文件 | /tmp 或 /app/logs 膨胀 | 清理临时文件，修代码 |
| 监控数据堆积 | Prometheus 数据目录大 | 调短 retention |
| CoreDNS 缓存 | /var/lib/coredns 膨胀 | 重启 CoreDNS |

## 止血优先级

1. **清理日志和 Docker 缓存**（最快释放空间）
2. **驱逐低优先级 Pod**（保护核心服务）
3. **扩容磁盘**（长期方案）

## 注意事项

- **不要**直接 `rm -rf /var/lib/docker`，会删除所有镜像导致节点不可用
- 清理前先 `du` 确认大小，避免删错文件
- 磁盘满会导致 K8s 驱逐 Pod，先确保核心服务 Pod 不被驱逐
- 定期设置 logrotate 和镜像清理 cron，预防而非临时处理
