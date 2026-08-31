# M6 分步指南：Agent 演进 + 交付收尾

> **前置**：M5 全部完成（M5.0～M5.3，含 PDF/截图）。  
> **目标**：ShipLog On-call **Agent** 能力 + README/PITCH/面试自测。  
> M4/M5 的 CRAG 仍负责**检索质量**；M6.0～M6.2 负责 **Agent**；M6.3～M6.4 负责 **简历交付**。

**当前进度：M6.0～M6.2 / M6.25～M6.27 / M6.4 ✅；M6.3 PITCH ✅、README 仍延后（U-019）。分支 `feature/m6-agent`。**

---

## 总览

```mermaid
flowchart LR
  M53[M5.3 PDF+截图] --> M60[M6.0 Tool Calling]
  M60 --> M61[M6.1 Multi-Agent]
  M61 --> M62[M6.2 记忆与规划]
  M62 --> M625[M6.25 Reranker U-001]
  M625 --> M626[M6.26 Faithfulness U-002]
  M626 --> M627[M6.27 误拒答 U-018]
  M627 --> M63[M6.3 README+PITCH]
  M63 --> M64[M6.4 面试 20 题]
```

| 子步 | 做什么 | 改动范围 | 场景题重点 | 状态 |
|------|--------|----------|-----------|------|
| M6.0 | Tool Calling | `tools.py`、`agent_graph.py`、SSE | 「Runbook vs 事故库 vs 拓扑」 | ✅ |
| M6.1 | Multi-Agent 分工 | LangGraph 多 Agent + 安全分支 | 「多路结果冲突怎么汇总」 | ✅ |
| M6.2 | 会话记忆 + 多步规划 | checkpointer、planning node | 「会话记忆 vs 知识库」 | ✅ |
| M6.25 | Reranker 二阶段重排（U-001） | `reranker.py`、`retriever.py`、eval | 「RRF 之后为什么还要 Rerank」 | ✅ |
| M6.26 | Faithfulness 口径（U-002 轻量） | `BASELINE.md`、qa、backlog | 「Retrieve 命中为何仍幻觉」 | ✅ |
| M6.27 | 压低误拒答（U-018） | `graph.py` grade + soft-fallback、`config` | 「CRAG 误拒答怎么降」 | ✅ |
| M6.3 | README 简历化 + `PITCH.md` | `README.md`、`docs/PITCH.md` | 「3 分钟介绍 ShipLog」 | PITCH ✅ / README **实习结束后** |
| **M6.4** | **场景面试 20 题自测** | `qa-m6.md` | 场景题 ≥15/20 | ✅ |

> **编号说明**：  
> - 原 M5 后半并入 M6：原 M5.4→M5.3，原 M5.3→M6.3，原 M5.5→M6.4  
> - **M6.25** 检索精排；**M6.26** 生成层 faithfulness 口径；**M6.27** 误拒答 soft-fallback（U-018）  
> - 面经 backlog：见 [upgrades/backlog.md](../interview/upgrades/backlog.md)

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

**目标**：复杂故障由协调 Agent 拆分——查 Runbook、查历史、查拓扑；危险操作走**安全策略回答**（非空白拒答）。

### Agent 分工

| Agent | 职责 |
|-------|------|
| **协调 Agent** | 解析问题 → JSON 派单 → 指定专家与参数 |
| **Runbook 专家** | `search_runbook`（RRF + CRAG） |
| **Incident 专家** | `query_incident` + 复盘摘要 |
| **Topology 专家** | `get_service_topology` 上下游依赖 |

### LangGraph 流程

```mermaid
flowchart TB
  START --> safe_check
  safe_check -->|危险操作/策略题| safe_response
  safe_check -->|正常| coordinator
  coordinator --> specialists
  specialists --> merge
  safe_response --> END
  merge --> END
```

### 安全分支（safe_response）

- 检测 FLUSHALL、删库等 → **safe_response 节点**
- **明确答「不能/禁止」** + Runbook 依据 + 审批提醒 + 替代方案
- **不**输出危险命令步骤；**不**空白拒答
- 历史复盘题（含「事故/复盘/怎么发生」）**不走**安全分支，正常派 incident 专家

### 验收

- 「order-service 502 影响谁？」→ trace 含 `agent_dispatch` + 多路 `agent_result` + `agent_merge`
- 「生产 Redis 能 FLUSHALL 吗？」→ trace 含 `safe_check.route=safe_response` + `safe_response.policy=true`；回答明确禁止
- 「Redis FLUSHALL 事故怎么发生的？」→ **不走** safe_response，走 coordinator + incident

### 场景题

「Multi-Agent 结果冲突怎么办？」

---

## M6.2 On-call 记忆与多步规划

**目标**：多轮 On-call 对话 + 复杂故障分步排查。

### 实现要点（M6.2 已编码）

| 模块 | 作用 |
|------|------|
| `app/rag/checkpointer.py` | `AsyncPostgresSaver` 连接 PG，启动时 `setup()` |
| `app/rag/session.py` | `record_thread_turn`；**补充** `load_thread_history` / `resolve_thread_id` |
| `app/llm.py` | **补充** `_build_chat_messages`（generate 多轮 history） |
| `multi_agent_graph.py` | `planning` 节点；`thread_id` checkpointer；每轮 `Overwrite` 重置 ephemeral 状态 |
| `schemas` / `main` | `thread_id`、`plan_steps`；SSE 先推 `plan_steps` 再推 token |
| `frontend` | `localStorage` thread_id；气泡内排查计划；「新会话」；**`chatStorage.ts` 刷新恢复 UI** |

### LangGraph 流程（正常路径）

```mermaid
flowchart TB
  START --> safe_check
  safe_check -->|策略题| safe_response --> END
  safe_check -->|正常| planning
  planning --> coordinator
  coordinator --> specialists --> merge --> END
```

### 要做的事

- [x] LangGraph **checkpointer**（PostgresSaver）
- [x] **Planning node**：拆 2～4 步排查计划
- [x] 前端：步骤列表 + SSE `plan_steps`
- [x] 前端：**localStorage 聊天气泡缓存**（刷新后 UI 恢复，方案 A）
- [x] **补充**：generate 层多轮（后端 `turn_history`，关 RAG 纯 LLM 也续聊）

### 验收

- 「刚才那个告警」能指代上一轮问题（同 `thread_id` 第二轮）
- 复杂题 trace/UI 可见 `planning.plan_steps`
- 点「新会话」换 thread_id 后指代失效（预期）
- **F5 刷新**后同 thread 聊天气泡仍在（plan_steps / sources / trace 保留；截图预览不保留）

### 场景题

「Agent 记忆和 RAG 知识库区别？」→ 见 [qa-m6.md](../qa/qa-m6.md) M6.2 章节。

---

## M6.2 补充 · generate 层多轮（后端存 history）

**目标**：**关 RAG = 纯 LLM**，但仍按 `thread_id` 从 checkpointer 读 `turn_history`，最终 generate 能看到最近几轮；**开 RAG** 时 generate 同样拼 history（Agent 推理记忆与生成记忆统一数据源）。

### 实现要点

| 模块 | 作用 |
|------|------|
| `session.py` | `load_thread_history` / `resolve_thread_id`；`record_thread_turn` 开/关 RAG 均调用 |
| `llm.py` | `_build_chat_messages`：System + 历史 Human/AI + 当前 Human |
| `main.py` | 关 RAG：`chat`/`chat_stream` 带 history；流式统一 `record_thread_turn` |
| `rag.py` | 最终 `chat(..., history=...)` 再 record |

### 记忆窗口

- `MAX_TURN_HISTORY = 6` 条（约 3 轮 Q&A），超出 **滑动丢弃最旧**（`trim_turn_history`）
- 前端仍只发 `thread_id` + `message`；localStorage 仅 UI 展示

### 验收

- **关知识库**：「北京天气」→「东城区」能接上上一轮语境（同 thread_id）
- **开知识库**：多轮 generate 不只有 Agent enrich，最终 LLM 也带 history
- 第 4 轮后最早一轮从 checkpointer 消失（预期）

### 场景题

「UI 有历史但模型接不上怎么办？」→ 见 [qa-m6.md](../qa/qa-m6.md) M6.2 补充。

---

## M6.25 Reranker 二阶段重排（U-001）

**目标**：在 BM25+向量 **RRF 粗排**之后加 **CrossEncoder 精排**，对齐面经「二阶段检索」；服务 CRAG / `search_runbook`。

**对应 backlog**：[U-001](../interview/upgrades/backlog.md) · 面经 §4.1 Reranker

### 链路

```text
query
  → 向量 Top-N + BM25 Top-N
  → RRF 融合取 pool（默认 20）
  → bge-reranker-base 打分排序
  → 截断 Top-K（默认 3）→ CRAG grade / LLM
```

### 实现要点

| 模块 | 作用 |
|------|------|
| `app/rag/reranker.py` | `CrossEncoder` 懒加载；`rerank_documents(query, docs, top_k)` |
| `app/rag/retriever.py` | `retrieve(..., use_rerank=)`；开启时粗排池 → 精排 |
| `app/config.py` | `RERANK_ENABLED`（默认 `0`）、`RERANK_MODEL`、`RERANK_POOL` |
| `eval/run_eval.py` | `--rerank` 对比有无精排的 Recall@3 / MRR |
| `tests/test_reranker.py` | mock CrossEncoder 单测（不下载模型） |

### 环境变量

| 变量 | 默认 | 说明 |
|------|------|------|
| `RERANK_ENABLED` | `0` | 设 `1` 开启（首次会下载/加载 CrossEncoder） |
| `RERANK_MODEL` | `BAAI/bge-reranker-base` | CrossEncoder 模型 |
| `RERANK_POOL` | `20` | 粗排候选数 |

首次启用会经 HF 镜像下载模型；CPU 上全量 38 题 eval 可能较慢，可先冒烟。  
Rerank 失败时 **fail-open**（回退粗排 Top-K），不拖垮整条问答。

### 验收

```powershell
cd E:\01_Dev\langChain
.venv\Scripts\python.exe -m unittest tests.test_reranker -v
# 演示开启 Rerank 后再评：
$env:RERANK_ENABLED="1"
uv run python eval/run_eval.py --rerank --no-file
```

- 单测通过  
- `--rerank` 报告写入 `eval/reports/retrieval/retrieval_eval_result_rerank.md`（或 `--no-file` 只打控制台）  
- `BASELINE.md` 记录有/无 Rerank 一行（库小可能 Recall 持平，仍可讲二阶段架构）  
- 口述：「RRF 是多路粗排；CrossEncoder 看 query-doc 对，精排 Top-K」

### 场景题

1. 「混合检索已经 RRF 了，为什么还要 Reranker？」  
2. 「换 Rerank 模型要不要重跑 embedding 索引？」  
3. 「CPU 上 Rerank 太慢怎么办？」

→ 参考答案写入 [qa-m6.md](../qa/qa-m6.md) §M6.25。

---

## M6.26 Faithfulness 口径（U-002 轻量）

**目标**：把已有 `run_gen_eval` **幻觉率**对齐面试常说的 **faithfulness**，能讲清「Retrieve 命中 ≠ 不幻觉」；**不**引入官方 `ragas` 包。

**对应 backlog**：[U-002](../interview/upgrades/backlog.md)

### 做了什么

| 项 | 说明 |
|----|------|
| 口径 | 答案级 faithfulness ≈ `1 − 幻觉率`（同实验组） |
| 诚实边界 | ≠ RAGAS claim 级 faithfulness；未跑官方库 |
| Case | q02（On-call 无 CRAG）、q08（有 CRAG 仍 HALLU） |
| 文档 | [BASELINE.md](../eval/reports/BASELINE.md)「与 RAGAS / faithfulness 对照」 |

### 验收

- [x] BASELINE 有对照表 + 换算数字（≈89.7% / 82.8% / 88.5%）  
- [x] 能口述 Retrieve vs Generate 分层 + 1 个 HALLU case  
- [x] backlog U-002 标 done（轻量）  
- [ ] （可选）重跑 `run_gen_eval.py` 刷新 v6——非本步必做  

### 场景题

1. 「你们测了 RAGAS faithfulness 吗？」  
2. 「检索 Recall 很高为什么还会幻觉？」  
3. 「答案级 faithfulness 和 claim 级差在哪？」

→ [qa-m6.md](../qa/qa-m6.md) §M6.26。

---

## M6.27 压低误拒答（U-018）

**目标**：在尽量不抬升幻觉的前提下，降低 CRAG **误拒答率**（BASELINE 上有 CRAG 组曾到 **21.2%**）。

**对应 backlog**：[U-018](../interview/upgrades/backlog.md)

### 做了什么

| 项 | 说明 |
|----|------|
| Grade 口径 | `GRADE_PROMPT` 偏召回：同域线索即相关；仅完全无关才 `NONE` |
| Soft-fallback | 改写后仍 `NONE` 且检索非空 → 用 Top 文档 **谨慎生成**（`reason=soft_fallback`），默认开 |
| 开关 | `CRAG_SOFT_FALLBACK=1`（默认）；`=0` 回到硬 abstain 便于对比 |
| 纯函数 | `decide_route_when_no_relevant` + `tests/test_crag_soft_fallback.py` |

### 验收

- [x] 单测 soft / hard / empty 三路路由  
- [x] trace `grade.reason=soft_fallback` 可回放  
- [ ] （建议）`uv run python eval/run_gen_eval.py --output eval/reports/generation/gen_eval_result_v6.md` 刷新误拒答/幻觉数字（耗时长，见 U-020）

### 场景题

1. 「CRAG 误拒答为什么升高？你们怎么降？」  
2. 「soft-fallback 会不会把幻觉抬回去？」  
3. 「和 safe_response（危险操作拒答）是一回事吗？」

→ [qa-m6.md](../qa/qa-m6.md) §M6.27。

---

## M6.3 README 简历化 + PITCH

> 原规划 **M5.3**。M6.0～M6.2 完成后写，叙事覆盖 **RAG → CRAG → PDF/截图 → Agent** 全链路。

**目标**：GitHub 首页当简历项目；3 分钟 STAR 讲 ShipLog。

### 进度

- [x] `docs/PITCH.md`：背景 → 方案 → 指标 → 难点（3 分钟口述稿）
- [ ] `README.md` 简历化（**等实习结束再做**，约一周后；= backlog U-019）
- [ ] 更新 [SCENARIO.md](../scenario/SCENARIO.md) 与 README 链到 PITCH/eval

### 要做的事（README 延后项）

- README：场景、架构图、技术栈、Docker/PG 启动、eval 数字 + Agent 亮点
- 链到 `eval/reports/BASELINE.md`、`docs/PITCH.md`

### 验收

- [x] 能不看稿讲完全链路（PITCH）
- [ ] 外人只看 README 知道解决什么问题、怎么跑（待 README）

### 场景题

「用 3 分钟介绍你的 RAG/Agent 项目。」→ 见 [PITCH.md](../PITCH.md)

---

## M6.4 场景面试 20 题

> 原规划 **M5.5**。紧接 PITCH。

**目标**：按 [qa-scenario-guide.md](../qa/qa-scenario-guide.md) + 面经库自测；**14 场景 + 6 八股**。

### 进度

- [x] `docs/qa/qa-m6.md` §M6.4：20 题完整参考答案（含美团/火山引擎类八股）
- [x] 用户自测勾选 ≥15/20（2026-08-26 用户确认完成）

### 覆盖范围

- RAG/eval、CRAG、PDF/截图、Tool Calling、Multi-Agent、记忆、Docker 排障
- 八股：混合检索、overlap、Agentic RAG、ReAct、LangGraph、JSON tool 兜底

### 验收

- [x] 自测 **≥15/20** 题
- [x] 能白板画：用户问 → Agent 选 tool → 检索/CRAG → 生成 + trace

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
| 官方 RAGAS Python 包（U-002 正统版） | 轻量口径已够用；需要 brand 名再加 |
| 全量 gen_eval 刷新（U-020） | M6.27 代码已合；数字以下次跑分为准 |

---

## 下一步

**当前**：M6.4 自测 ✅；**U-012 Chunk 消融** ✅（选用 500/50，见 `eval/reports/ablation/chunk_ablation.md`）；README（U-019）**等实习结束**再开。  
期间：巩固口述 [PITCH.md](../PITCH.md)；可选 backlog（U-003 / U-014 等），不催 README。
