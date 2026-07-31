# M6 面试问答卡 · Agent 演进 + 交付

> 场景题为主，见 [qa-scenario-guide.md](./qa-scenario-guide.md)。

---

## M6.0 Tool Calling

### 概念

**Q：M6.0 三个 tool 怎么分工？**

**A：**
- `search_runbook`：Runbook/复盘/架构文档检索（RRF + CRAG）
- `query_incident`：PG `incidents` 表查历史事故
- `get_service_topology`：PG `service_topology` 查上下游依赖

| 用户意图 | 工具 |
|----------|------|
| 怎么排查 / 第一步 | `search_runbook` |
| 以前出过吗 / 根因 | `query_incident` |
| 还影响谁 / 依赖 | `get_service_topology` |

---

### 场景题（M6.0）

**Q1：** On-call 问「Redis 超时第一步做什么？」Agent 却调了 `query_incident`，你怎么排查？

**A：**
1. **现象**：回答像历史故事，没有 Runbook 步骤。
2. **步骤**：`GET /traces/{trace_id}` 看 `tool_start.tool_name`；若为 `query_incident` 则选错工具。
3. **根因**：Agent system prompt 不够清晰；或问题歧义（「上次 Redis 超时」vs「现在超时怎么办」）。
4. **更好方案**：强化 `AGENT_SYSTEM` 路由规则；trace 里记录 `tool_name` + args；必要时 few-shot。
5. **本项目**：`app/rag/agent_graph.py` `AGENT_SYSTEM`；trace steps `tool_start` / `tool_end`。

---

**Q2：** 怎么保证 JSON tool 调用稳定？选错 tool 怎么办？

**A：**
1. **现象**：400 tool parse error，或 LLM 幻觉参数。
2. **根因**：模型输出不符合 schema；问题超出三工具能力。
3. **手段**：Pydantic `args_schema`；Agent 节点失败 **重试 1 次**；`MAX_TOOL_ROUNDS=3` 防死循环。
4. **选错 tool**：靠 trace 回放 + 优化 system prompt；M6.1 Multi-Agent 再分专职 Agent。
5. **本项目**：`app/tools.py` StructuredTool + `agent_graph._agent_node` 双次 invoke。

---

**Q3：** Runbook 检索和拓扑查询为什么拆成两个 tool，不一个 RAG 搞定？

**A：**
1. **数据形态不同**：Runbook 是非结构化 md chunk；拓扑是结构化依赖图。
2. **召回方式不同**：Runbook 用向量+BM25；拓扑用 SQL 精确查 `depends_on`/`depended_by`。
3. **面试点**：Tool 设计 = 按 **意图 + 数据源** 拆分，避免一个 tool 包打天下导致参数混乱。
4. **本项目**：`search_runbook` → CRAG；`get_service_topology` → `oncall_data.get_service_topology`。

---

**Q4：** `GET /traces/{id}` 里怎么确认 Agent 走了哪条工具链？

**A：**
1. 看 `steps` 数组顺序：`vision_extract`（有图）→ `tool_start` → `tool_end` → `agent_synthesize`。
2. `tool_start` 含 `tool_name`、`args`；`tool_end` 含结果摘要。
3. `agent_synthesize.tools_used` 列出本次用过的工具名列表。

---

### M6.0 自检

- [ ] 能口述 Agent 图：agent → tools → agent → synthesize
- [ ] 能解释三 tool 分工表
- [ ] 能用 trace_id 回放 tool 选择
