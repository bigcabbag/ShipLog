# M5.3 截图提问 · 手测步骤

> 虚构告警截图，勿用真实公司内部监控图。可自己用画图工具做一张「Redis 连接超时」告警图。
>
> **本目录 sample 图**（与 curl 示例同路径）：
> - `alert-redis.png` — Redis connection timeout（用例 1）
> - `alert-pod-oom.png` — Kubernetes Pod OOMKilled（用例 2）
> - `alert-db-drop.png` — prod DB DROP / 无 Runbook 危险告警（用例 3）

## 用例 1：只发截图

1. 确保已 `import_docs`，知识库有 `runbooks/redis-timeout.md`
2. 前端开启 **use_rag** + **流式**
3. 粘贴告警截图（含 Redis / timeout / prod 等字样），**不输入文字**，点发送
4. **期望**：
   - 助手气泡显示「已从截图识别：…」
   - 回答引用 Runbook 排查步骤
   - `sources` 含 `runbooks/redis-timeout.md`
   - `GET /traces/{trace_id}` 的 `steps` 第一条为 `vision_extract`

## 用例 2：截图 + 问句

1. 贴 Pod OOM 相关截图 + 文字「第一步查什么？」
2. **期望**：检索 query 合并读图结果与用户文字；命中 `runbooks/pod-oom.md`

## 用例 3：无关 / 危险无覆盖截图

1. 贴 `alert-db-drop.png`（prod `DROP DATABASE`，知识库无对应 Runbook）
2. **期望**：CRAG 拒答或「未找到相关 Runbook」，不编造 `DROP`/`kubectl`/恢复命令；不假装能止血

## curl 调试（可选）

```powershell
# 将 alert.png 转为 base64 后填入
$b64 = [Convert]::ToBase64String([IO.File]::ReadAllBytes("docs/kb/demo/alert-redis.png"))
$body = @{
  message = "这个告警怎么处理？"
  use_rag = $true
  image_base64 = $b64
  image_media_type = "image/png"
} | ConvertTo-Json
Invoke-RestMethod -Uri http://127.0.0.1:8000/chat -Method Post -Body $body -ContentType "application/json; charset=utf-8"
```
