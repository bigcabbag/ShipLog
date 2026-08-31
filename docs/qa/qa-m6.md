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

---

## M6.25 Reranker（U-001）

### 概念

**Q：RRF 之后为什么还要 CrossEncoder Rerank？**

**A：**

- **RRF**：多路召回（向量语义 + BM25 关键词）按排名融合，**不看 query-doc 文本对**，便宜、可扩池。
- **CrossEncoder**：把 `(query, chunk)` 拼在一起过 Transformer，打相关性分，**精排更准**、更贵。
- 常见流水线：**粗排多取（pool=20）→ 精排截断 Top-3** → 再进 CRAG/LLM。
- **本项目**：`retriever.retrieve` → `reranker.rerank_documents`；模型默认 `BAAI/bge-reranker-base`。

### 场景题（M6.25）

**Q1：** 混合检索已经 RRF 了，为什么还要 Reranker？

**A：**

1. **现象**：Top-3 里有关键词撞上的无关块，或语义相关但排序靠后。
2. **根因**：RRF 只融合「名次」，不直接建模 query 与段落是否匹配。
3. **排查**：对比 `eval/run_eval.py` 与 `--rerank` 的 MRR / 单题 rank。
4. **更好方案**：库更大时收益更明显；可再上专领域微调 reranker。
5. **本项目**：M6.25；`RERANK_ENABLED` / `RERANK_POOL`；单测 mock CrossEncoder。

**Q2：** 换 Rerank 模型要不要重跑 embedding 索引？

**A：**

1. **不用重跑向量库**：Rerank 在检索后打分，不写入 pgvector。
2. **要重跑的是**：换 **embedding** 模型时必须全量 re-index + Recall（见 §4.6 A10）。
3. **口述**：Rerank 换模型只影响在线打分延迟与排序；eval 用 `--rerank` 对比即可。

**Q3：** CPU 上 Rerank 太慢怎么办？

**A：**

1. 减小 `RERANK_POOL`（20→10）；或 `RERANK_ENABLED=0` 仅 RRF。
2. 换更小 cross-encoder；或异步预热模型（启动时 load）。
3. 生产可 GPU / 独立 rerank 服务。
4. **本项目**：懒加载 `get_cross_encoder()`；首次请求会下载模型。

### M6.25 自检

- [ ] `python -m unittest tests.test_reranker -v` 通过
- [ ] `uv run python eval/run_eval.py --rerank --no-file` 能出 Recall/MRR
- [ ] 能口述：粗排 RRF → 精排 CrossEncoder → Top-K
- [ ] 知道换 embed 要 re-index，换 rerank 不用

---

## M6.26 Faithfulness 口径（U-002 轻量）

### 概念

**Q：你们测 faithfulness 了吗？用的 RAGAS 吗？**

**A：**

- **目标同构**：答案必须能在检索 context 里找到依据（groundedness）。  
- **实现**：`run_gen_eval.py` 用 temperature=0 的 LLM 做答案级幻觉判定；**答案级 faithfulness ≈ 1 − 幻觉率**。  
- **未安装**官方 `ragas` 包；不说「跑了 RAGAS」，说「LLM-as-judge，口径对齐 faithfulness」。  
- 数字（v5）：On-call+CRAG 幻觉 **11.5%** → 答案级 faithfulness ≈ **88.5%**。

### 场景题（M6.26）

**Q1：** 检索 Recall@3 已经 86.8%，为什么还会幻觉？

**A：**

1. **分层**：Recall 只保证「期望文件进 Top-K」；生成仍可能补文档没有的命令。  
2. **Case**：q02「连接数打满」On-call 无 CRAG → `[HALLU]`（见 `eval/reports/generation/gen_eval_result_v5.md`）。  
3. **CRAG**：把幻觉 17.2%→11.5%，仍非零——grade 管相关，不管逐步溯源。  
4. **本项目**：检索 `run_eval` + 生成 `run_gen_eval` 分开报。

**Q2：** 答案级 faithfulness 和 RAGAS claim 级差在哪？

**A：**

1. **答案级**：整段答里「有没有任意一条胡编」→ 我们的幻觉率。  
2. **Claim 级**：拆成多条陈述，每条算是否被 context 支持，再平均 → 官方 RAGAS 常见做法。  
3. **口述**：我们优先答案级，On-call「不能编造任何命令」更严；claim 级是扩展。

### M6.26 自检

- [ ] 能说出 ≈88.5% 怎么从 11.5% 换算来  
- [ ] 能举 q02 或 q08 说明 Retrieve≠Faithful  
- [ ] 追问「用了 RAGAS 吗」时诚实说轻量口径、未装包

---

## M6.27 压低误拒答（U-018）

### 概念

**Q：CRAG 为什么误拒答会到 21.2%？你们怎么降？**

**A：**

1. **根因**：grade 过严（「必须能完整回答」）→ 两次 NONE → 硬 abstain，库内题也被拒。  
2. **手段**：① grade 改成偏召回（同域线索即相关）；② 改写后仍 NONE 且检索非空 → **soft-fallback** 谨慎生成（trace `reason=soft_fallback`）。  
3. **开关**：默认 `CRAG_SOFT_FALLBACK=1`；对比实验可关。  
4. **边界**：soft-fallback **不是** `safe_response`（危险操作明确拒答仍走安全分支）。  
5. **数字**：优化前基线误拒答 21.2%；全量 gen_eval 刷新见 U-020。

### 场景题（M6.27）

**Q1：** soft-fallback 会不会把幻觉抬回去？

**A：** 可能略升——用检索 Top 但 grade 未认可的块生成。因此加「文档不足就说不确定、禁编命令」提示；需用 gen_eval 看 trade-off，不能只报误拒答。

**Q2：** 和 safe_response 是一回事吗？

**A：** 不是。误拒答 = 库内该答却 abstain；safe_response = 用户要 FLUSHALL 等危险操作时 **明确拒答并讲审批**。一个是可用性，一个是安全策略。

### M6.27 自检

- [ ] 能画：NONE → rewrite → 仍 NONE → soft_generate vs 硬 abstain  
- [ ] 知道 `CRAG_SOFT_FALLBACK` 默认开  
- [ ] 能区分 soft-fallback 与 safe_response

---

## M6.4 综合自测 20 题（场景 + 八股）

> **用法**：闭卷自答 → 对照参考答案 → 勾选自检。目标 **≥15/20**。  
> **八股**（Q15～Q20）来自美团/字节类 Agent 面经 + 火山引擎 RAG+Agent 题单；**场景题**覆盖 M4～M6 全链路。  
> 口述稿见 [PITCH.md](../PITCH.md)。

### 自测记录

| # | 题型 | 题目摘要 | 自评 |
|---|------|----------|------|
| 1 | 场景 | 召回率多少、怎么量的 | ☐ |
| 2 | 场景 | 答错了从哪层查 | ☐ |
| 3 | 场景 | Retrieve vs Generate | ☐ |
| 4 | 场景 | CRAG 幻觉 17.2%→11.5% trade-off | ☐ |
| 5 | 场景 | 混合检索为什么、何时无效 | ☐ |
| 6 | 场景 | PDF/截图进 RAG 链路 | ☐ |
| 7 | 场景 | 三 tool 怎么拆 | ☐ |
| 8 | 场景 | 专家结论冲突 | ☐ |
| 9 | 场景 | FLUSHALL 安全分支 | ☐ |
| 10 | 场景 | 会话记忆 vs 知识库 | ☐ |
| 11 | 场景 | planning vs coordinator | ☐ |
| 12 | 场景 | trace 回放排障 | ☐ |
| 13 | 场景 | Docker 前端 502 | ☐ |
| 14 | 场景 | 流式 + 会话保存失败 | ☐ |
| 15 | 八股 | 向量 vs 关键词检索 | ☐ |
| 16 | 八股 | Chunk overlap | ☐ |
| 17 | 八股 | RAG vs Agentic RAG | ☐ |
| 18 | 八股 | ReAct 原理 | ☐ |
| 19 | 八股 | LangGraph vs Chain | ☐ |
| 20 | 八股 | JSON tool 调用兜底 | ☐ |

---

### 场景题（Q1～Q14）

**Q1：** 你做了三个月 RAG，召回率多少？怎么量的？

**A：**

1. **指标**：ShipLog **38 题 scored**，**Recall@3 = 86.8%**，MRR ≈ 0.855（见 `eval/reports/BASELINE.md`）。
2. **方法**：`eval/questions.json` 标注期望来源文件；`eval/run_eval.py` 只评检索层，不调 LLM。
3. **Miss 解释**：5 道是知识库**故意不覆盖**的 On-call 场景（Prometheus、NetworkPolicy 等），用于测拒答，不算检索失败。
4. **更好方案**：上线后 RAGAS context_recall + bad case 回流 eval。
5. **本项目**：M4.1 建 eval；M5.2 换 ShipLog 题库。

---

**Q2：** 用户说「AI 答错了」，你从哪开始查？

**A：**

| 层 | 查什么 | 本项目 |
|----|--------|--------|
| Query | 太模糊？需改写？ | CRAG rewrite；M6 enrich 指代 |
| Retrieve | Top-K 片段相关吗？ | 看 `sources`；`run_eval.py` |
| Chunk | 语义被切断？ | `loader.py` chunk_size/overlap |
| Generate | 上下文对仍胡说？ | On-call prompt；CRAG grade |
| Agent | 选错 tool？ | `GET /traces/{id}` tool_name |

**步骤**：先分 Retrieve vs Generate（gold chunk 在不在 Top-K），再动刀；别一上来换模型。

---

**Q3：** 怎么判断是检索问题还是生成问题？

**A：**

1. **Retrieve 问题**：期望文档块**不在** Top-K → 查 embedding、切块、混合检索、索引是否过期。
2. **Generate 问题**：正确块**在** Top-K 但答案错/编造 → 查 prompt、temperature、CRAG、是否缺 citation。
3. **工具**：手工读 Top-3 最快；离线 RAGAS。
4. **本项目**：M4.1 eval 看 retrieve 命中；M4.2 CRAG 低分则 rewrite 重检。

---

**Q4：** CRAG 把幻觉率从 17.2% 降到 11.5%，为什么误拒答率反而升到 21.2%？

**A：**

1. **现象**：生成层 eval 三组对比，CRAG 降幻觉但 availability 下降。
2. **根因**：`grade` 节点偏严，相关文档被判不相关 → 该答的也拒了。
3. **trade-off**：On-call **宁可误拒也不编造 kubectl 命令**。
4. **更好方案**：调 grade 阈值；加 Rerank 提升 Retrieve 质量后再 grade；分「必须拒答」与「可尝试回答」两类题。
5. **本项目**：`eval/reports/BASELINE.md` 生成层表；`graph.py` CRAG 节点。

---

**Q5：** 向量检索和关键词检索各适合什么？你为什么做混合检索？

**A：**

1. **向量**：语义相似、换说法也能命中（「Redis 超时」≈「连接 timed out」）。
2. **关键词（BM25）**：专有名词、告警码、命令精确匹配（`OOMKilled`、`FLUSHALL`）。
3. **混合 RRF**：两路排名融合，互补；DevKit 库小曾 94.4% 持平，ShipLog 86.8% 也与纯向量持平但工程上为扩库做准备。
4. **本项目**：`app/rag/retrieval.py` RRF；M4.3。

---

**Q6：** 用户贴告警截图，系统怎么处理？

**A：**

1. **链路**：前端 base64 → `vision.py` DeepSeek 读图 → 提取文本 query → 走 RAG/Agent（与文本问同一套）。
2. **现象**：trace 可有 `vision_extract`；检索仍走 `search_runbook` 等 tool。
3. **注意**：截图预览不持久化 localStorage（体积）；文字标记「附带告警截图」保留。
4. **本项目**：M5.3；`resolve_rag_inputs`。

---

**Q7：** 为什么拆三个 tool，不是一个 RAG 查全部？

**A：**（详见 M6.0 Q3）

1. **数据形态**：Runbook 非结构化；incident/topology 结构化 SQL。
2. **召回方式**：文档 RRF+CRAG；拓扑 `depends_on` 精确查。
3. **Agent 稳定性**：单 tool 参数易混，协调者 JSON 派单更清晰。
4. **本项目**：`app/tools.py` 三 StructuredTool。

---

**Q8：** Runbook 专家说查日志，Incident 专家说上次直接回滚，怎么汇总？

**A：**（详见 M6.1 Q5）

1. **优先级**：Runbook SOP + topology 结构化数据为准；事故记录是**历史背景**不是本次定论。
2. **排查**：trace `agent_dispatch` / `agent_result`。
3. **本项目**：`MERGE_PROMPT` 第 2 条。

---

**Q9：** 「生产 Redis 能 FLUSHALL 吗」怎么答？

**A：**（详见 M6.1 Q6）

1. **走 safe_response**：明确不能 + 风险 + 审批 + 替代方案；**不是** abstain。
2. **例外**：「FLUSHALL 事故怎么发生的」→ 历史题，派 incident。
3. **本项目**：`needs_safe_branch()` + `HISTORICAL_MARKERS`。

---

**Q10：** Agent 会话记忆和 RAG 知识库有什么区别？

**A：**（详见 M6.2 Q9）

1. **知识库**：静态文档 + PG 表，跨用户共享。
2. **turn_history**：同 thread 对话轮次，用于指代 enrich + generate 多轮。
3. **localStorage**：仅 UI 刷新，非权威。
4. **原则**：事实仍从 tool 查，别把旧回答当真相。

---

**Q11：** planning 和 coordinator 为什么要分两节点？

**A：**（详见 M6.2 Q10）

1. **planning**：`plan_steps` 给人看 + 给协调者上下文。
2. **coordinator**：可执行 `tasks` JSON 派单。
3. **fast-path**：首轮简单问跳过 Planning LLM，trace `planning_skipped: true`。

---

**Q12：** 线上用户说回答不对，你只有 trace_id，怎么排障？

**A：**

1. `GET /traces/{trace_id}` 看 `steps` 顺序。
2. 有 `safe_check` / `safe_response`？→ 策略题。
3. 有 `planning` / `agent_dispatch` / `agent_result`？→ 派单与专家结果。
4. 有 `tool_start`？→ M6.0 单 Agent 路径。
5. 看 `route`、`abstain_reply`、`plan_steps`、`thread_id`。
6. **本项目**：`app/rag/trace.py` + PG `rag_traces`。

---

**Q13：** Docker 部署后浏览器 502，Swagger 直连 8032 正常，怎么查？

**A：**

1. **现象**：仅经 frontend nginx 失败。
2. **根因**：`VITE_API_BASE_URL` 构建成 `http://backend:8000` 浏览器解析不了；或 nginx upstream 未就绪。
3. **排查**：`docker compose logs frontend`；Network 看请求 URL；`curl localhost:8032/health`。
4. **修复**：生产构建 `VITE_API_BASE_URL: ""` 同源反代。
5. **本项目**：`docker-compose.yml`；见 `qa-m5.md`。

---

**Q14：** SSE 流式已出完整回答，却报「调用 DeepSeek 失败」，可能是什么？

**A：**

1. **现象**：token 都推完了才报错。
2. **根因**：生成成功，**之后** `record_thread_turn` 写 checkpointer 失败（如 LangGraph `Ambiguous update, specify as_node`）。
3. **排查**：看 SSE 最后一帧是 `error` 还是 `warning`；后端日志 `record_thread_turn`。
4. **修复**：`aupdate_state(..., as_node="merge")`；保存失败单独 `warning` 不误报 LLM。
5. **本项目**：M6.2 补充；`session.py`。

---

### 基础八股（Q15～Q20）

> 答法：**定义 → 为什么需要 → 本项目怎么落地（有则说）**

**Q15：** 向量检索和关键词检索各适合什么场景？为什么现在混合检索更多？

**A：**

1. **向量**：语义泛化、同义改写、自然语言问法；弱点是稀有词、ID、命令拼写。
2. **关键词**：精确 token、告警码、API 名；弱点是换一种说法就 miss。
3. **混合**：工业界默认 **召回互补**；融合常用 RRF，避免只信一路。
4. **本项目**：BM25 + pgvector/Chroma → RRF（M4.3）。

---

**Q16：** 文档切片为什么要 Chunk Overlap？解决什么问题？

**A：**

1. **问题**：固定窗口切块会在 **段落/步骤边界** 切断，答案跨两块时 Retrieve 只命中一半。
2. **Overlap**：相邻块共享尾部/头部，提高边界语义完整性。
3. **代价**：存储增多、索引冗余，需调 `chunk_size` / `overlap`。
4. **本项目**：`loader.py` 默认 chunk_size=500、overlap 可配；eval 可对比调参。

---

**Q17：** 传统 RAG 和 Agentic RAG 本质区别是什么？

**A：**

1. **传统 RAG**：固定链路 query → retrieve → generate，无自主决策。
2. **Agentic RAG**：LLM/图 **决定是否检索、检索几次、何时改写 query、何时拒答**；可接多数据源 tool。
3. **框架**：LangGraph 用 State + 条件边实现 CRAG 循环、Agent 派单。
4. **本项目**：M4.2 CRAG 图；M6 Multi-Agent + 三 tool = Agentic RAG 落地。

---

**Q18：** ReAct 原理是什么？和单轮问答最本质区别？

**A：**

1. **ReAct**：**Reasoning + Acting** 交替——模型输出思考 + 调 tool + 读 observation + 再思考，多步直到能答。
2. **单轮**：一次 prompt 一次 completion，无工具反馈环。
3. **区别**：有无 **环境反馈**（tool 结果）和 **多步循环**。
4. **本项目**：M6.0 `agent_graph` tool 节点循环；M6.1 改为协调者派单（仍是多步，但分工更结构化）。

---

**Q19：** 为什么用 LangGraph，而不是普通 LangChain Chain？

**A：**

1. **Chain**：线性 DAG，难表达 **循环**（CRAG 重写再检）、**条件分支**（safe_check）、**多 Agent 汇合**。
2. **LangGraph**：显式 **State**、节点、条件边；支持 checkpointer **持久化状态**；适合生产 Agent。
3. **面试句**：「Chain 适合一次性管道；Agent 要循环、分支、记忆就用图。」
4. **本项目**：`graph.py` CRAG；`multi_agent_graph.py` M6.1～M6.2。

---

**Q20：** 怎么保证 LLM 稳定输出 JSON 调工具？格式错了怎么兜底？

**A：**

1. **手段**：Pydantic `args_schema` + StructuredTool；system prompt 约束；**structured output** / function calling（模型支持时）。
2. **兜底**：正则/括号抽取 JSON（`_extract_json_object`）；解析失败 **重试 1 次**；仍失败 fallback（如默认派 runbook 专家）。
3. **限流**：`MAX_TOOL_ROUNDS` 防死循环。
4. **本项目**：`app/tools.py` + `agent_graph._agent_node`；`multi_agent_graph._coordinator_node` fallback。

---

### M6.4 自检

- [x] 20 题自测 **≥15/20**（场景题能讲排查步骤，八股能连本项目）— 2026-08-26 用户确认完成
- [ ] 能 **3 分钟** 讲完 [PITCH.md](../PITCH.md) 不看稿（建议定期复习）
- [x] 白板能画：用户 → Agent → 三 tool → CRAG → trace
- [x] 能报两个数字：**Recall@3 86.8%**、**幻觉率 17.2%→11.5%**
