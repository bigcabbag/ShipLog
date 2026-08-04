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

---

## M6.1 Multi-Agent

### 概念

**Q：M6.0 和 M6.1 架构差什么？**

**A：**
- M6.0：单 Agent bind 3 tools，LLM 自选工具
- M6.1：**协调 Agent 派单** → Runbook / Incident / Topology **专家各 1 工具** → **merge 汇总**；危险题走 **safe_response** 策略分支

| trace step | 含义 |
|------------|------|
| `safe_check` | 是否走安全分支 |
| `agent_dispatch` | 协调者派了哪些专家 |
| `agent_result` | 某专家 tool 结果摘要 |
| `agent_merge` / `safe_response` | 汇总或策略回答 |

---

### 场景题（M6.1）

**Q5：** Multi-Agent 里 Runbook 专家说先查日志，Incident 专家说上次是配置错误直接回滚，你怎么汇总？

**A：**
1. **现象**：两路专家结论冲突，用户收到矛盾建议。
2. **根因**：Runbook 给通用 SOP；Incident 给**单次**历史根因，不可直接等同本次。
3. **排查**：看 trace `agent_dispatch.tasks` 和各路 `agent_result`；确认 incident 的 service/keyword 是否匹配当前告警。
4. **更好方案**：merge prompt 约定优先级——**Runbook 步骤 + topology 结构化数据为准**，事故记录作背景；必要时协调者再派一轮补查。
5. **本项目**：`multi_agent_graph.py` `MERGE_PROMPT` 第 2 条；trace `agent_merge.agents_used`。

---

**Q6：** 用户问「生产 Redis 能 FLUSHALL 吗」，系统应该拒答还是回答？

**A：**
1. **现象**：若回「无法回答」，用户不知道是不能做还是系统坏了。
2. **根因**：这是**有标准答案的策略题**，Runbook 有禁止条款；不是 abstain 题。
3. **做法**：`safe_check` 命中 → `safe_response`：**明确答不能** + 风险 + Runbook 依据 + SRE Lead 审批 + 替代方案；**不给** FLUSHALL 执行步骤。
4. **例外**：「FLUSHALL 事故怎么发生的」含历史标记 → **不走** safe_response，派 incident 专家。
5. **本项目**：`needs_safe_branch()` + `HISTORICAL_MARKERS`；eval q26 `should_abstain: false`。

---

**Q7：** trace 里怎么区分 M6.0 单 Agent 和 M6.1 Multi-Agent？

**A：**
1. M6.0：`tool_start` / `tool_end` / `agent_synthesize`（LLM 直接选 tool）
2. M6.1：`agent_dispatch` → 多路 `agent_result` → `agent_merge`；或 `safe_check` → `safe_response`
3. 安全题看 `safe_response.policy: true`

---

**Q8：** 协调 Agent JSON 解析失败怎么办？

**A：**
1. **现象**：coordinator 输出非 JSON，专家未派单。
2. **根因**：模型格式漂移。
3. **手段**：`_extract_json_object` 抽 JSON；失败则 **fallback** 默认派 runbook 专家；trace 标 `coordinator_fallback: true`。
4. **更好方案**：Pydantic structured output / 重试 1 次。
5. **本项目**：`_coordinator_node` fallback + trace 字段。

---

### M6.1 自检

- [ ] 能口述 Multi-Agent 图：safe_check → coordinator → specialists → merge
- [ ] 能解释 safe_response vs abstain 区别
- [ ] 能用 trace 看 agent_dispatch / agent_merge
