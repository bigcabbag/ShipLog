# Runbook: 服务回滚操作

## 适用场景

- 新版本上线后发现问题，需要快速回滚
- 灰度发布异常，需要切回稳定版本

## 回滚前确认

1. **确认问题**：看告警、日志，确认是本次发布引入的
2. **评估影响**：回滚也会短暂影响服务，确认回滚比修复更快
3. **通知干系人**：在 On-call 群说明「准备回滚 <service>，原因：xxx」

## 回滚操作

### K8s Deployment 回滚

```bash
# 1. 查看发布历史
kubectl rollout history deployment/<service> -n prod

# 2. 回滚到上一版本
kubectl rollout undo deployment/<service> -n prod

# 3. 回滚到指定版本
kubectl rollout undo deployment/<service> -n prod --to-revision=3

# 4. 确认回滚状态
kubectl rollout status deployment/<service> -n prod
kubectl get deployment <service> -n prod -o jsonpath='{.spec.template.spec.containers[0].image}'
```

### ArgoCD 回滚

```bash
# 1. 查看 ArgoCD 应用状态
argocd app get prod/<service>

# 2. 回滚（ArgoCD 会禁用 auto-sync）
argocd app rollback prod/<service> <revision>

# 3. 回滚后若需要恢复 auto-sync
argocd app set prod/<service> --sync-policy automated
```

### 数据库变更回滚

**注意**：数据库变更通常不可逆，需要提前准备回滚 SQL。

```bash
# 1. 确认有回滚 SQL（应在发布前准备）
# 2. 执行回滚 SQL
mysql -h <host> -u <user> -p <db> < rollback_xxx.sql

# 3. 确认数据状态
mysql -h <host> -u <user> -p <db> -e "SELECT COUNT(*) FROM <table>"
```

## 回滚后验证

```bash
# 1. 确认 Pod 正常启动
kubectl get pods -n prod -l app=<service>

# 2. 确认健康检查通过
kubectl exec -it gateway-xxx -n prod -- curl http://<service>:8080/health

# 3. 确认告警恢复
# 看 Grafana 对应 Dashboard 指标是否恢复正常

# 4. 观察稳定性 15-30 分钟
```

## 注意事项

- **回滚不是万能的**：如果数据库 schema 已变更，回滚代码可能不兼容旧 schema
- **数据库迁移要前向兼容**：新代码能读旧 schema，旧代码也能读新 schema
- **回滚后要禁用 auto-sync**（ArgoCD），否则 GitOps 会再次同步到新版本
- **回滚操作记录**：在复盘文档里记录回滚时间、版本号、原因
