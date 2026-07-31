# M6 分步指南：Agent 演进 + 交付收尾

> **前置**：M5 全部完成（M5.0～M5.3，含 PDF/截图）。  
> **目标**：ShipLog On-call **Agent** 能力 + README/PITCH/面试自测。  
> M4/M5 的 CRAG 仍负责**检索质量**；M6.0～M6.2 负责 **Agent**；M6.3～M6.4 负责 **简历交付**。

**当前进度：未开始（需先完成 M5.3）。M5.3 后说「继续 M6.0」。**

---

## 总览

```mermaid
flowchart LR
  M53[M5.3 PDF+截图] --> M60[M6.0 Tool Calling]
  M60 --> M61[M6.1 Multi-Agent]
  M61 --> M62[M6.2 记忆与规划]
  M62 --> M63[M6.3 README+PITCH]
  M63 --> M64[M6.4 面试 20 题]
```

| 子步 | 做什么 | 改动范围 | 场景题重点 |
|------|--------|----------|-----------|
| M6.0 | Tool Calling | `tools.py`、`graph.py`、SSE | 「Runbook vs 事故库 vs 拓扑」 |
| M6.1 | Multi-Agent 分工 | LangGraph 多 Agent + 安全分支 | 「多路结果冲突怎么汇总」 |
| M6.2 | 会话记忆 + 多步规划 | checkpointer、planning node | 「会话记忆 vs 知识库」 |
| M6.3 | README 简历化 + `PITCH.md` | `README.md`、`docs/PITCH.md` | 「3 分钟介绍 ShipLog」 |
| M6.4 | 场景面试 20 题自测 | `qa-m5.md` / `qa-m6.md` | 场景题 ≥15/20 |

> **编号说明**（原 M5 后半并入 M6）：  
> - 原 **M5.4** → 现 **M5.3**（PDF + 截图，M5 最后一步）  
> - 原 **M5.3** → 现 **M6.3**（README + PITCH）  
> - 原 **M5.5** → 现 **M6.4**（面试自测）

---

## M6.0 Tool Calling：On-call 三工具

**目标**：LLM 根据问题自主选工具——查 Runbook、查历史事故、或查**服务依赖拓扑**（不做联网搜索）。

> **已定稿（2026-07）**：第三工具为 `get_service_topology`，数据来自 `docs/kb/architecture/service-topology.md`（可 seed PG 小表）。不做 `web_search`。

### 工具定义（`app/tools.py`）

| 工具 | 作用 | 对应能力 |
|------|------|----------|
| `search_runbook` | 混合检索 `docs/kb/` Runbook/复盘（语义+关键词） | M4.3 RRF + CRAG |
| `query_incident` | SQL 查 PG `incidents` 历史事故 | M5.1 PG |
| `get_service_topology` | 按服务名返回上下游依赖、端口、关键中间件 | `docs/kb/architecture/service-topology.md` |

**三工具分工（面试可背）**：

| 用户意图 | 选哪个 tool |
|----------|-------------|
| 「怎么排查 / 第一步做什么」 | `search_runbook` |
| 「以前出过吗 / 上次事故根因」 | `query_incident` |
| 「还影响了谁 / 依赖谁 / blast radius」 | `get_service_topology` |

### `incidents` 表（M6.0 新增 seed）

```text
incidents：
  - id, title, service, severity, root_cause, resolved_at, summary, …
```

- seed 3～5 条与 `docs/kb/postmortems/` 一致的虚构数据

### `service_topology`（M6.0 新增，与 kb 对齐）

- 来源：`docs/kb/architecture/service-topology.md` 中的服务清单与依赖关系
- 实现：PG 表 `service_topology` 或启动时解析 md/json seed（二选一，M6.0 子步内定）
- 返回示例字段：`service`, `depends_on[]`, `depended_by[]`, `ports`, `datastores[]`

### 要做的事

- `tools.py`：上述三工具 + Pydantic 参数校验 + JSON 解析兜底（重试 1 次）
- `graph.py`：LangGraph tool calling 节点（agent → tool → 汇总 → 生成）
- `trace`：steps 记录 `tool_name`、入参、摘要结果
- 前端（可选）：SSE `tool_start` / `tool_end`
- 复用 M5.3 `vision.py`：贴图后可先读图再 `search_runbook` 或 `get_service_topology`

### 验收

- 「Redis 超时第一步？」→ `search_runbook`
- 「上个月 OOM 出过吗？」→ `query_incident`
- 「order-service 502 还可能影响谁？」→ `get_service_topology`（含 payment-service 等）
- `GET /traces/{id}` 可回放选了哪个 tool

### 场景题

- 「怎么保证 JSON tool 调用稳定？选错 tool 怎么办？」
- 「Runbook 检索和拓扑查询为什么拆成两个 tool？」

---

## M6.1 Multi-Agent：On-call 分工

**目标**：复杂故障由协调 Agent 拆分——查 Runbook、查历史、（可选）查外部。

### Agent 分工

| Agent | 职责 |
|-------|------|
| **协调 Agent** | 解析告警 → 分配子任务 → 汇总 |
| **Runbook Agent** | RAG + BM25 混合检索 |
| **Incident Agent** | `query_incident` + 复盘摘要 |
| **External Agent**（可选） | M6.0 不做 web_search；M6.1 可扩展 metrics/日志 adapter |

### LangGraph 安全分支

- 检测到 FLUSHALL、删库等 → **safe_response 节点**，只引用 Runbook 禁止条款

### 验收

- 两路结果汇总；危险操作拒答

### 场景题

「Multi-Agent 结果冲突怎么办？」

---

## M6.2 On-call 记忆与多步规划

**目标**：多轮 On-call 对话 + 复杂故障分步排查。

### 要做的事

- LangGraph **checkpointer**
- **Planning node**：拆 2～4 步排查计划
- 前端：步骤列表（可与 M5.3 截图 SSE 共用事件类型）

### 验收

- 「刚才那个告警」能指代上一轮问题
- 复杂题输出分步计划并执行

### 场景题

「Agent 记忆和 RAG 知识库区别？」

---

## M6.3 README 简历化 + PITCH

> 原规划 **M5.3**。M6.0～M6.2 完成后写，叙事覆盖 **RAG → CRAG → PDF/截图 → Agent** 全链路。

**目标**：GitHub 首页当简历项目；3 分钟 STAR 讲 ShipLog。

### 要做的事

- 更新 [SCENARIO.md](../SCENARIO.md)
- README：场景、架构图、技术栈、Docker/PG 启动、eval 数字 + Agent 亮点
- `docs/PITCH.md`：背景 → 方案 → 指标 → 难点
- 链到 `eval/BASELINE.md`

### 验收

- 外人只看 README 知道解决什么问题、怎么跑
- 能不看稿讲完全链路

### 场景题

「用 3 分钟介绍你的 RAG/Agent 项目。」

---

## M6.4 场景面试 20 题

> 原规划 **M5.5**。紧接 M6.3。

**目标**：按 [qa-scenario-guide.md](../qa/qa-scenario-guide.md) + 面经库自测。

### 要做的事

- 更新 `docs/qa/qa-m5.md`；新建或补充 `docs/qa/qa-m6.md`
- 覆盖：RAG/eval、CRAG、PDF/截图、Tool Calling、Multi-Agent、记忆

### 验收

- 自测 **≥15/20** 题
- 能白板画：用户问 → Agent 选 tool → 检索/CRAG → 生成 + trace

---

## 与 M5.3 截图的衔接

| 能力 | M5.3 | M6 |
|------|------|-----|
| `vision.py` 读图 → query | ✅ | M6.0 复用 |
| 文本 RRF + CRAG | ✅ | `search_runbook` tool |
| SSE 读图/工具步骤 | 可选 | `vision_extract` / `tool_start` |

---

## 不做 / 延后

| 项 | 说明 |
|----|------|
| CLIP / 端到端多模态向量 | backlog U-009 |
| MCP 协议 | backlog U-005 |

---

## 下一步

先完成 **M5.3**（PDF + 截图）→ 说 **「继续 M6.0」**。  
M6.2 后 → **M6.3** README → **M6.4** 面试自测。
