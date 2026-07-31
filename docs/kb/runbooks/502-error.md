# Runbook: 502 Bad Gateway 排查

## 症状

- 告警：`http_502_rate` 触发
- Nginx 日志：`upstream prematurely closed connection` 或 `connect() timed out`
- 用户：页面/接口返回 502

## 排查步骤

### 1. 确认 502 范围

```bash
# Nginx 错误日志
kubectl logs -n prod -l app=gateway --tail=100 | grep 502

# 看是哪个 upstream 报 502
kubectl logs -n prod -l app=gateway --tail=200 | grep "upstream" | awk '{print $NF}' | sort | uniq -c | sort -rn
```

### 2. 检查后端服务状态

```bash
# 看目标服务 Pod 是否正常
kubectl get pods -n prod -l app=<target-service>

# 看 Pod 是否在重启或 CrashLoopBackOff
kubectl describe pod <pod-name> -n prod | grep -A10 "Conditions:"

# 看后端服务是否在监听端口
kubectl exec -it <pod-name> -n prod -- netstat -tlnp | grep 8080
```

### 3. 检查健康检查

```bash
# 手动调健康检查接口
kubectl exec -it gateway-xxx -n prod -- curl -s -o /dev/null -w "%{http_code}" http://<target-service>:8080/health

# 若返回非 200，后端服务可能假死（进程在但无法处理请求）
```

### 4. 检查连接池

```bash
# Nginx upstream 配置
kubectl exec -it gateway-xxx -n prod -- cat /etc/nginx/conf.d/default.conf | grep -A10 upstream

# 看 keepalive 连接数是否耗尽
kubectl exec -it gateway-xxx -n prod -- ss -s
```

## 常见根因

| 根因 | 现象 | 止血 |
|------|------|------|
| 后端 Pod 全挂 | get pods 显示 0 Running | 重启 Deployment |
| 后端假死 | Pod Running 但 /health 超时 | 重启 Pod |
| 连接池耗尽 | ss 显示大量 TIME_WAIT | 调整 keepalive 参数 |
| 后端启动慢 | 滚动更新时新 Pod 还没 ready | 调大 readiness probe 延迟 |
| Nginx 配置错误 | upstream 地址不对 | 修正配置回滚 |

## 止血优先级

1. **重启后端 Deployment**（若 Pod 全挂）
   ```bash
   kubectl rollout restart deployment/<target-service> -n prod
   ```
2. **回滚 Nginx 配置**（若刚改过配置）
   ```bash
   kubectl rollout undo deployment/gateway -n prod
   ```
3. **临时切流量**（若单服务故障）
   ```bash
   # 在 gateway 层屏蔽故障 upstream，返回降级响应
   ```

## 注意事项

- 502 通常是后端服务问题，不是 Nginx 本身问题
- 滚动更新期间短暂 502 是正常的，若持续说明 readiness probe 配置不当
- 排查时先看是全量 502 还是部分 502，定位是单服务还是网关层问题
