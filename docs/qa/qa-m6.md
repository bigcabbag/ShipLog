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


| 用户意图       | 工具                     |
| ---------- | ---------------------- |
| 怎么排查 / 第一步 | `search_runbook`       |
| 以前出过吗 / 根因 | `query_incident`       |
| 还影响谁 / 依赖  | `get_service_topology` |


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

- [x] 能口述 Agent 图：agent → tools → agent → synthesize
- [x] 能解释三 tool 分工表
- [x] 能用 trace_id 回放 tool 选择

---



## M6.1 Multi-Agent



### 概念

**Q：M6.0 和 M6.1 架构差什么？**

**A：**

- M6.0：单 Agent bind 3 tools，LLM 自选工具
- M6.1：**协调 Agent 派单** → Runbook / Incident / Topology **专家各 1 工具** → **merge 汇总**；危险题走 **safe_response** 策略分支


| trace step                      | 含义            |
| ------------------------------- | ------------- |
| `safe_check`                    | 是否走安全分支       |
| `agent_dispatch`                | 协调者派了哪些专家     |
| `agent_result`                  | 某专家 tool 结果摘要 |
| `planning`                      | M6.2 排查计划 2～4 步；`planning_skipped` = fast-path 未调 LLM |
| `session`                       | M6.2 thread_id 关联  |


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

### 场景题（M6.2）

**Q9：** Agent 会话记忆和 RAG 知识库有什么区别？「刚才那个还影响谁」怎么理解上下文？

**A：**

1. **现象**：用户问「刚才那个告警还影响谁」，需要理解上一轮上下文。
2. **根因**：知识库是**静态文档/结构化表**；会话记忆是**本轮 thread 内的对话轮次**（`turn_history`）。
3. **指代消解（enrich）**：第二轮 invoke 前，`run_multi_agent_prepare` 从 checkpointer `aget_state` 读历史；若问题含「刚才/那个/还影响」等标记，走 `enrich_question_with_history` 把上一轮用户问句拼进 `search_query`（轻量 query rewrite，不调额外 LLM）。
4. **排查**：trace `session.thread_id` 是否同一；checkpointer 是否有该 thread；第二轮 trace 里 coordinator 的检索 query 是否带「上下文：上一轮用户问的是…」。
5. **更好方案**：记忆只保留近 N 轮摘要（本项目 `trim_turn_history` 最多 6 轮）；事实仍从 Runbook/incident/topology 查，避免把旧回答当真相。
6. **本项目**：`session_context.py`（enrich / graph_config）；`session.py`（`record_thread_turn` 写回）；RAG 仍走 `search_runbook` / PG 表。

---

**Q10：** 排查计划（planning）和协调派单（coordinator）为什么要分两节点？首轮简单问会调 Planning LLM 吗？

**A：**

1. **现象**：复杂题需要先「拆步骤」再「派专家」，混在一起 JSON 易乱。
2. **根因**：planning 输出 **plan_steps**（给人看 + 给 coordinator 上下文）；coordinator 输出 **tasks**（可执行派单）。
3. **Planning fast-path**：首轮、短问（≤80 字、无「还影响/上下游/事故」等复杂标记）**跳过 Planning LLM**，直接用默认 1 步 plan；trace 标 `planning_skipped: true`。多轮或有复杂意图才调 LLM planning。
4. **排查**：trace 先看 `planning.plan_steps` 与 `planning_skipped` / `planning_fallback`；再看 `agent_dispatch.tasks` 是否对齐 plan。
5. **更好方案**：简单题省 1 次 LLM 延迟；策略题走 `safe_response` 整段跳过 planning；复杂题才 full planning。
6. **本项目**：`_should_skip_planning_llm()` + `planning → coordinator → specialists`；UI 展示 plan_steps（含 fast-path 默认步）。

---

**Q11：** 用户点「新会话」后指代不到上一轮，这是 bug 吗？enrich 为什么失效？

**A：**

1. **现象**：新 thread 无 `turn_history`，「刚才那个还影响谁」无法 enrich。
2. **根因**：**预期行为**——新会话 = 新 `thread_id` = checkpointer 空历史；`enrich_question_with_history` 无上一轮可拼，原样返回问题。
3. **做法**：前端 `resetThreadId()` + 清空 messages；旧 thread 仍在 PG checkpointer 中，trace 仍可按旧 thread_id 回放。
4. **排查**：对比两轮 `session.thread_id`；新会话后应为新 UUID；不应期望跨 thread 指代。
5. **更好方案**：可选「会话列表」加载历史 thread（backlog）；或显式提示「新会话已开启，请完整描述问题」。
6. **本项目**：`frontend/src/utils/threadId.ts` + 「新会话」；`REFERENTIAL_MARKERS` 在 `session_context.py`。

---

**Q12：** Postgres checkpointer 和 rag_traces 表各存什么？enrich / fast-path 落在哪？

**A：**

1. **checkpointer**：LangGraph 图状态（含 `turn_history`），按 **thread_id** 跨轮持久化；`record_thread_turn` 每轮 append 后 `trim_turn_history` 裁剪。
2. **rag_traces**：每轮请求的 **trace 回放**（steps、route、plan_steps），按 **trace_id** 单次查询。
3. **关系**：一轮对话 = 1 trace_id + 同一 thread_id；trace steps 含 `session` / `planning`（含 `planning_skipped`）/ `agent_dispatch` 等。
4. **enrich 不落库单独字段**：发生在 `run_multi_agent_prepare` invoke **之前**，只改当轮 `search_query`；历史来源是 checkpointer 的 `turn_history`。
5. **fast-path 可观测**：首轮简单问 trace 里 `planning.planning_skipped: true`，无 `planning_fallback`。
6. **面试句**：「会话状态在 checkpointer，可观测性在 rag_traces；指代 enrich 是 invoke 前内存改写，planning fast-path 是 trace 可证的省 LLM 路径。」

---

**Q13：** 刷新页面后聊天记录还在，是 checkpointer 恢复的吗？

**A：**

1. **现象**：F5 后气泡、plan_steps、sources 仍在界面上。
2. **根因**：**前端 localStorage**（`shiplog_messages_{thread_id}`）缓存展示层；与后端 checkpointer 的 `turn_history` **职责分离**。
3. **不恢复什么**：截图 base64 预览（体积大）不持久化，文字「（附带告警截图）」仍保留。
4. **更好方案**：生产用 PG/Redis + 用户账号维度的 `chat_messages` 表；本项目 M6.2 用方案 A 够演示。
5. **本项目**：`frontend/src/utils/chatStorage.ts`；mount 时 `loadChatMessages`，debounce `saveChatMessages`；「新会话」`clearChatMessages`。

---

**Q14（M6.2 补充）：** 关知识库时多轮为什么以前接不上？现在怎么做的？

**A：**

1. **现象**：UI 能看到上一轮，但关 RAG 时「东城区」接不上「北京天气」。
2. **根因（旧）**：关 RAG 只发当前一句给 DeepSeek，且不 `record_thread_turn`。
3. **做法（补充）**：**后端 authoritative**——`load_thread_history(thread_id)` → `chat/history` 拼 messages → 答完 `record_thread_turn`；关 RAG **仍不走** Multi-Agent。
4. **窗口**：最近 6 条 message（约 3 轮），超出 `trim_turn_history` 丢最旧。
5. **本项目**：`session.load_thread_history` + `llm._build_chat_messages` + `main.py` 关 RAG 路径。

---

### M6.2 自检

- [ ] 两轮同 thread：「payment 502」→「刚才那个还影响谁」（topology 派单 + enrich 生效）
- [ ] 首轮简单问 trace 含 `planning.planning_skipped: true`
- [ ] UI 助手气泡上方见排查计划列表
- [ ] trace 含 `planning` + `session.thread_id`
- [ ] 「新会话」后指代 / enrich 重置（预期失效）
- [ ] **F5 刷新**后聊天气泡仍在（localStorage；截图预览除外）
- [ ] **关知识库**：「北京天气」→「东城区」同 thread 能续聊（generate 层 history）

### M6.1 自检

- [x] 能口述 Multi-Agent 图：safe_check → coordinator → specialists → merge
- [x] 能解释 safe_response vs abstain 区别
- [x] 能用 trace 看 agent_dispatch / agent_merge