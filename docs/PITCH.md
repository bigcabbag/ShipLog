# ShipLog · 3 分钟项目 Pitch

> **用途**：面试自我介绍后的项目深挖、HR/技术面「讲讲你的项目」、不写稿也能讲完全链路。  
> **配套**：指标见 [eval/BASELINE.md](../eval/BASELINE.md) · 场景题见 [qa/qa-m6.md](./qa/qa-m6.md) §M6.4 · 业务背景见 [scenario/SCENARIO.md](./scenario/SCENARIO.md)

---

## 一句话（15 秒）

**ShipLog** 是我做的 **研发 On-call 故障排查助手**：把 Runbook、事故复盘和服务拓扑放进知识库，用 **混合检索 + CRAG** 控幻觉，再叠 **Multi-Agent 派单、安全分支和会话记忆**，让值班工程师能查步骤、查历史、看影响面，并且 **危险操作会明确拒答而不是胡编命令**。

---

## STAR 完整版（约 3 分钟）

### S — Situation（背景 · 30 秒）

On-call 值班时，工程师要在几分钟内判断：**先查什么、以前出过没有、还会影响哪些服务**。现实里 Runbook 散在 Wiki、复盘在另一处、依赖关系在架构图里，告警一来容易 **搜不到、搜到也信不过**——大模型还会 **编造 kubectl/redis 命令**，P0 场景风险很高。

所以我用 **模拟 SRE 知识库**（`docs/kb/`）做了一个可演示、可量化的项目，对标企业搜索 + Agent 面经里的 On-call 场景，而不是泛泛的「聊天知识库 Demo」。

### T — Task（目标 · 20 秒）

1. **答得准**：检索要能命中 Runbook，生成要能 **引用来源、该拒答就拒答**  
2. **答得全**：复杂故障要能 **查文档 + 查历史事故 + 查服务拓扑**  
3. **答得稳**：`FLUSHALL`、删库这类题 **策略明确拒答**，不能装死 abstain  
4. **能讲清**：有 **eval 数字**、有 **trace 回放**、能 **Docker 一键演示**

### A — Action（方案 · 90 秒）

我按里程碑把能力叠上去，每一层只解决一类问题：

| 阶段 | 做了什么 | 为什么 |
|------|----------|--------|
| **M2～M3** | PDF/Markdown 入库、切块、向量检索、React + SSE 流式 | 先跑通 RAG 全栈 |
| **M4** | BM25+向量 **RRF 混合检索**、**LangGraph CRAG**（评分→改写/拒答）、eval 20+ 题、trace_id | 解决「搜不准」和「瞎编」 |
| **M5** | 场景切 **ShipLog**、**pgvector**、Docker Compose、PDF 热更新 + **截图读图** | 工程化 + On-call 真实输入 |
| **M6** | **三 Tool** → **Multi-Agent 派单** → **Planning + Postgres checkpointer 会话记忆** | Agent 分工 + 多轮指代 |

**技术栈一句话**：Python 3.12、FastAPI、LangGraph、pgvector、React；LLM 用 DeepSeek；会话状态进 Postgres checkpointer，可观测性进 `rag_traces`。

**三条面试必讲的设计**：

1. **三工具分工**（不是一个大 RAG 包打天下）  
   - `search_runbook`：非结构化文档，RRF + CRAG  
   - `query_incident`：结构化 SQL 查历史事故  
   - `get_service_topology`：依赖图精确查上下游  

2. **Multi-Agent + 安全分支**  
   - 协调者 JSON 派单 → 三专家各干一件事 → merge 汇总  
   - 危险操作走 `safe_response`：**明确说不能做** + 风险 + 审批流程，而不是空泛拒答  

3. **记忆分层**（别和 RAG 混为一谈）  
   - **知识库**：静态 Runbook / PG 表  
   - **checkpointer `turn_history`**：同 thread 多轮指代（enrich + generate 层 history）  
   - **localStorage**：仅前端展示刷新用  

### R — Result（结果 · 40 秒）

**检索层**（ShipLog 38 题 scored）：**Recall@3 = 86.8%**，MRR ≈ 0.855（5 道 miss 是知识库故意不覆盖的场景，用于测拒答）。

**生成层**（33 题对比实验）：完整 **CRAG + On-call prompt** 把幻觉率从 **17.2% 降到 11.5%**；代价是误拒答率升到 21.2%——On-call 场景我接受 **宁可少说也不编造命令**。

**工程交付**：`docker compose up` 起 postgres + backend + frontend；`GET /traces/{id}` 可回放 planning、派单、tool、安全分支。

---

## 架构口述（白板 60 秒）

```text
用户 → FastAPI (/chat/stream)
         ├─ 有图 → vision 读图 → 文本 query
         ├─ use_rag=true → Multi-Agent Graph
         │     safe_check → planning → coordinator → specialists(3 tools) → merge → LLM 生成
         │     checkpointer: turn_history 跨轮
         └─ use_rag=false → 纯 LLM + 同 thread history

检索：Chroma/pgvector + BM25 → RRF → CRAG grade/rewrite
观测：rag_traces（每轮 trace_id）+ SSE plan_steps / sources
```

---

## 难点 & 我怎么讲（追问备用）

| 难点 | 现象 | 我的做法 |
|------|------|----------|
| On-call prompt 反而增幻觉 | 要求「给具体命令」→ LLM 补全文档没有的命令 | 用 CRAG 压回 11.5%；prompt 平衡详细 vs 保守 |
| 多专家结论冲突 | Runbook 步骤 vs 上次事故根因 | merge 优先级：SOP + 拓扑为准，事故作背景 |
| 会话指代 | 「刚才那个还影响谁」 | enrich 拼上轮 query；generate 层也读 checkpointer history |
| 关 RAG 多轮接不上 | UI 有历史但 LLM 只吃一句 | 后端 authoritative：`load_thread_history` → `chat(history=)` |
| LangGraph 外部写状态 | `Ambiguous update, specify as_node` | `aupdate_state(..., as_node="merge")` |

---

## 和岗位 JD 的对应（Agent / RAG 应用开发）

| JD 常见要求 | ShipLog 对应 |
|-------------|--------------|
| RAG 优化（混合检索、拒答） | RRF + CRAG + eval 数字 |
| Agent / Tool Calling | 三 tool + LangGraph |
| 多 Agent 协作 | coordinator → specialists → merge |
| 记忆 / 多轮 | Postgres checkpointer + enrich |
| 流式 / 可观测 | SSE + trace 回放 + plan_steps UI |
| 工程化部署 | Docker Compose + pgvector |

---

## 收尾金句（可选）

> 这个项目我不是堆概念，而是按 **检索质量 → 生成安全 → Agent 分工 → 会话状态** 一层层加能力，每一层都有 eval 或 trace 能证明。如果让我继续做，我会加 **Rerank**、把误拒答率压下来，以及生产级会话存储替代 localStorage。

---

## 自测清单（讲完对照）

- [ ] 30 秒内说清 **为谁、解决什么痛点**
- [ ] 能报 **Recall@3、幻觉率 17.2%→11.5%** 两个数字
- [ ] 能画 **safe_check → planning → coordinator → specialists → merge**
- [ ] 能区分 **三 tool、safe_response vs abstain、三种记忆**
- [ ] 被追问「你的贡献」：从 M4 eval/CRAG 到 M6 Agent/记忆，按里程碑讲

**下一步自测**：[qa-m6.md §M6.4](./qa/qa-m6.md) 20 题，目标 **≥15/20**。
