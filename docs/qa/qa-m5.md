# M5 面试问答卡

> 场景题规范见 [qa-scenario-guide.md](./qa-scenario-guide.md)。

---

## 场景题 · M5.0 Docker Compose

**Q1：** 同事 clone 项目后说「我 Docker 起来了但 vector_count 是 0」，你怎么排查？

**A：**
1. **现象**：UI 能开、/health 正常，RAG 无引用或拒答。
2. **根因**：Compose 只起服务，**未跑 import_docs**；或 `data/chroma` 卷为空/未挂载。
3. **排查**：`docker compose exec backend uv run python scripts/import_docs.py`；`GET /documents/stats`；看 compose 里 `./data/chroma:/app/data/chroma` 是否生效。
4. **方案**：文档写清「首次必须 import」；CI/compose 可选 init 容器（M5.1 前保持手动）。
5. **本项目**：Chroma 持久化在宿主机 `data/chroma`，重建容器不丢向量。

---

**Q2：** 本地 `npm run dev` 正常，Docker 里前端能开但聊天 502/CORS，为什么？

**A：**
1. **现象**：浏览器 localhost:5173 打开，请求 API 失败。
2. **根因**：前端 `VITE_API_BASE_URL` 构建时写死；若写成 `http://backend:8000`，浏览器解析不了 docker 内网名；或 CORS 未含前端 origin。
3. **排查**：Network 看请求 URL 是 localhost:8032 还是 backend；后端 CORS 是否含 `http://localhost:5173`。
4. **方案**：Docker 前端 ARG 用 `http://localhost:8032`（宿主机端口映射）；CORS 与 dev 一致。
5. **本项目**：`frontend/Dockerfile` build-arg + `main.py` CORSMiddleware 已配 5173。后端映射 8032→8000（Windows Hyper-V 保留 8000 端口范围）。

---

**Q3：** Docker 部署和本地 uv 开发差在哪？数据卷为什么要挂？

**A：**
1. **现象**：容器删了向量库没了；或 Embedding 每次重新下载很慢。
2. **根因**：容器文件系统 ephemeral；未挂 `data/chroma` / HuggingFace cache。
3. **排查**：`docker volume ls`、compose volumes 配置。
4. **方案**：挂 `./data/chroma`、`data/bm25`、`data/traces`、`data/uploads`；`hf_cache` 命名卷缓存模型。
5. **本项目**：M5.0 仍 Chroma；M5.1 再加 postgres 卷。

---

## 场景题 · M5.1 pgvector + trace 迁 PostgreSQL

**Q5：** 为什么从 Chroma 迁到 pgvector？trace 为什么也进 PG？BM25 为什么还放 JSON？

**A：**
1. **现象**：Chroma 嵌入式 SQLite+duckDB，单机够用但多实例/备份/事务不好做；trace 是 JSONL 文件，按 trace_id 查要全表扫描。
2. **根因**：Chroma 不是真正的数据库——没有 ACID、没有并发写安全、没有 SQL 查询能力；JSONL trace 量大后线性扫描慢，且和向量数据割裂。
3. **排查**：`docker compose exec postgres psql -U rag -d rag -c "SELECT COUNT(*) FROM langchain_pg_embedding;"`；`EXPLAIN ANALYZE SELECT ... FROM rag_traces WHERE trace_id=...`。
4. **方案**：向量进 pgvector（`langchain_pg_embedding` 表，HNSW 索引）；trace 进 `rag_traces` 表（`trace_id` 主键索引，O(1) 查询）；BM25 仍放 `corpus.json`——它是内存索引，重建快、和 PG 无事务关联，进 PG 反而增复杂度。
5. **本项目**：`store.py` 用 `PGVectorAdapter` 包装 `langchain_postgres.PGVector`，兼容 retriever 的 `_collection.count()`；`trace.py` 的 `save_trace`/`load_trace` 签名不变，内部从 JSONL 改 PG `INSERT`/`SELECT`。

---

**Q6：** 迁到 pgvector 后，`retriever.py` 里 `store._collection.count()` 报错怎么办？

**A：**
1. **现象**：PGVector 没有 `_collection` 属性，直接调 `store._collection.count()` 会 `AttributeError`。
2. **根因**：Chroma 的 `_collection` 是私有 API，PGVector 接口完全不同；retriever 依赖了这个私有属性。
3. **排查**：`docker compose logs backend | grep AttributeError`。
4. **方案**：写 `PGVectorAdapter` 包装类，`_collection` 返回一个 `_CountProxy`，其 `count()` 执行 `SELECT COUNT(*) FROM langchain_pg_embedding JOIN langchain_pg_collection`；其余方法 `__getattr__` 代理给 PGVector。retriever.py **零改动**。
5. **本项目**：`store.py` 的 `PGVectorAdapter` + `_count_vectors()` 兼容空库（表不存在时 catch `ProgrammingError` 返回 0）。

---

**Q7：** pgvector 的向量检索和 Chroma 性能差多少？什么场景该上 HNSW 索引？

**A：**
1. **现象**：小库（几百条）两者都毫秒级；库到百万条后 pgvector 不加索引会全表扫描变慢。
2. **根因**：pgvector 默认精确扫描（`<->` 距离逐行算）；HNSW 是近似最近邻索引，用图结构跳过大部分计算。
3. **排查**：`EXPLAIN ANALYSE SELECT ... ORDER BY embedding <-> '[...]' LIMIT 10`；看是 `Seq Scan` 还是 `Index Scan`。
4. **方案**：`CREATE INDEX ON langchain_pg_embedding USING hnsw (embedding vector_cosine_ops)`；百万级以上才值得，几百条精确扫描更快且无召回损失。
5. **本项目**：188 条，不加索引精确扫描足够；M6 如果知识库扩到 10w+ 再加 HNSW。

---

**Q8：** trace 表设计成什么样？为什么 trace_id 用 VARCHAR(16) 而不是 UUID？

**A：**
1. **现象**：trace_id 是 `uuid4().hex[:16]`，16 位 hex；表用 `VARCHAR(16) PRIMARY KEY`。
2. **根因**：16 位 hex = 64 bit 熵，单系统日 10w 条 trace 冲突概率极低（生日悖论 ~0.001%）；UUID 36 字符太长，URL/日志不方便。
3. **排查**：`SELECT COUNT(*) FROM rag_traces` vs `SELECT trace_id, LENGTH(trace_id) FROM rag_traces LIMIT 5`。
4. **方案**：`VARCHAR(16) PRIMARY KEY` + `ON CONFLICT (trace_id) DO NOTHING`；如果未来量极大可换 `BIGSERIAL` 或完整 UUID。
5. **本项目**：`trace.py` 的 `new_trace_id()` 返回 `uuid4().hex[:16]`，`save_trace` 用 `ON CONFLICT` 防重复；`steps` 字段用 `JSONB` 存检索过程数组，支持 PG JSON 查询。

---

**Q4：** 面试 30 秒怎么讲 Docker 这一步？

**A：**
> M5.0 用 Compose 起 backend（uvicorn + Chroma 卷，:8032→8000）和 frontend（nginx 静态页）。浏览器通过 localhost:8032 调 API，首次 `docker compose exec` 跑 import_docs。为 M5.1 pgvector 打基础，别人 clone 后只需 Docker + `.env` 能演示 RAG。

---

## 场景题 · M5.2 ShipLog 场景定稿

**Q9：** 混合检索为什么适合 Runbook（告警码、Pod 名、命令）？答错了怎么四层排查？

**A：**
1. **现象**：问「Redis 连接超时」检索到正确 runbook，但问「redis dial tcp i/o timeout」反而 miss。
2. **根因**：纯向量检索擅长语义（「连接超时」≈「connection timeout」），但精确词（告警码、Pod 名、shell 命令）语义距离远；BM25 擅长精确词匹配。混合检索 RRF 融合两者优势。
3. **排查**：四层——Retrieve（Top-3 有没有期望文件）→ Grade（CRAG 相关性评分）→ Rewrite（改写查询重检索）→ Generate（LLM 是否拒答）。哪层 miss 就调哪层。
4. **方案**：BM25+向量 RRF 融合，向量权重 1.0、BM25 权重 0.35（向量主、BM25 辅）；精确词题靠 BM25 补召回，语义题靠向量补召回。
5. **本项目**：M5.2 ShipLog eval Recall@3=100%（18/18），比 DevKit 阶段 94.4% 提升——知识库主题明确（Runbook/复盘），无跨主题混淆。

---

**Q10：** 为什么从 DevKit 换成 ShipLog 场景？换皮改了什么、没改什么？

**A：**
1. **现象**：面试官问「你这个 RAG 项目解决什么业务问题」，DevKit「查项目文档」太学生气，ShipLog「On-call 查 Runbook」有真实业务价值。
2. **根因**：DevKit 场景知识库是学习文档（PLAN/steps/qa），面试官不关心；ShipLog 场景知识库是 Runbook+事故复盘，能讲 SRE 痛点。
3. **排查**：看 `docs/kb/` 目录——10 篇文档分 architecture/runbooks/postmortems 三类，全是虚构 SRE 场景。
4. **方案**：换皮不换引擎——改了 `import_docs.py`（扫 kb/）、`context.py`（On-call 助手 prompt）、`graph.py`（REWRITE 改 Runbook 语境）、前端文案、eval 20 题；**没改** retriever/store/bm25/CRAG 主链路。
5. **本项目**：引擎复用体现工程能力——同一套混合检索+CRAG 架构，换知识库就能服务不同场景。

---

**Q11：** On-call 助手的 prompt 为什么要强调「禁止编造 shell 命令」？

**A：**
1. **现象**：用户问「怎么清理 Redis」，如果 LLM 编造一个不存在的命令，On-call 照着执行可能出事。
2. **根因**：通用 LLM 有「幻觉」倾向——即使知识库没有相关文档，也会编一个看起来合理的命令。On-call 场景下错误命令的代价是生产事故。
3. **排查**：看 `context.py` 的 `RAG_SYSTEM_PROMPT`——4 条规则：只根据文档、危险操作提醒审批、无信息时明确拒答、按步骤编号给命令。
4. **方案**：prompt 级约束 + CRAG 拒答兜底——检索不到相关文档时 CRAG 直接 abstain，不进 generate 环节。
5. **本项目**：eval q19（FLUSHALL 释放内存）和 q20（DROP TABLE）是危险操作题，检索层命中但生成层应拒答——靠 prompt + CRAG 双保险。

---

## 场景题 · M5.2 评估增强（量化对比）

**Q7：** 你怎么量化你的 RAG 系统比"裸 LLM + 检索"更好？有什么数据支撑？

**A：**
1. **现象**：面试官问"你说加了 CRAG、加了安全 prompt，到底好在哪里？有数据吗？"——光说"更安全"没有说服力。
2. **根因**：RAG 系统的改进需要量化指标支撑，否则就是"我觉得更好"的主观判断。
3. **排查**：自建 33 题 eval（28 scored + 5 abstain），分检索层和生成层两阶段评估。检索层跑 Recall@K / Precision@K / MRR；生成层跑拒答准确率 / 误拒答率 / 幻觉率，做 3 组对比实验。
4. **方案**：
   - 检索层：`run_eval.py` 对比纯向量 vs 混合检索（BM25+RRF）
   - 生成层：`run_gen_eval.py` 对比「无 CRAG + 通用 prompt」「无 CRAG + On-call prompt」「有 CRAG + On-call prompt」
   - 幻觉率用 temperature=0 的 LLM 评估器逐条检查回答中的命令是否在文档中有对应
5. **本项目**：实测数据——CRAG 把幻觉率从 **17.2% → 11.5%**（-5.7pp），代价是误拒答率从 12.1% → 21.2%（grade 偏严格的 trade-off）。检索层 Recall@3=86.8%、MRR=0.855（43题，含 5 道知识库不覆盖的 On-call 场景）。

---

**Q8：** 你的 CRAG 误拒答率从 0% 升到 14.3%，这不是变差了吗？为什么还要用？

**A：**
1. **现象**：CRAG 模式下，一些本该回答的题被误拒答了。
2. **根因**：CRAG 的 grade 节点用 LLM 判断检索结果是否相关，有时太严格——文档明明有相关内容，但 grade 认为"不够直接"就 abstain 了。
3. **排查**：看 trace 日志，grade_raw 输出是 NONE，但实际文档里有相关内容。grade prompt 的判断标准偏保守。
4. **方案**：这是 safety vs availability 的 trade-off。On-call 场景下，**错误回答的代价 >> 拒答的代价**（编造命令可能导致生产事故，拒答只是用户体验差）。所以宁可误拒答也不编造。优化方向：调 grade prompt 让它更宽松，或增加 rewrite 次数。
5. **本项目**：MAX_REWRITES=1，只改写一次。误拒答率 21.2% 在可接受范围内，且拒答时会建议"查阅官方文档或联系 SRE"，不是硬中断。CRAG 同时把幻觉率从 17.2% 降到 11.5%，是安全性的净提升。

---

**Q9：** 你的幻觉率评估用 LLM 判断 LLM，这不是"既当裁判又当运动员"吗？可靠吗？

**A：**
1. **现象**：幻觉率由 LLM 评估器判定，但 LLM 本身也会犯错——可能把正确的回答判为幻觉，或把幻觉判为正确。
2. **根因**：LLM-as-judge 的已知问题：评估器有自己的偏差，且受 temperature 影响（temperature=0.7 有随机性，同题不同次结果不同）。
3. **排查**：调试时发现三个问题：①"只输出判断"的 prompt 倾向判 HALLUCINATED；②评估时传的 context 和生成时用的不一致（CRAG 改写查询后检索的文档不同）；③temperature=0.7 导致同题不同次结果不同。
4. **方案**：
   - 评估器用 temperature=0 消除随机性
   - 逐条检查回答中的每个命令是否在文档中有对应（而非整体判断）
   - 评估时传生成时实际用的 context（CRAG 模式下用改写后查询检索的文档）
   - 先分析再判断（chain-of-thought），取最后一行
5. **本项目**：修正后幻觉率从"全部 0%"（评估器太宽松）变为有区分度的 0%-25%。承认 LLM-as-judge 有局限，但作为快速量化手段已足够展示改进趋势。生产环境可引入人工标注的 golden set 做校准。

---

**Q10：** 你的 On-call prompt 幻觉率（25%）比通用 prompt（0%）还高，这不是越改越差吗？

**A：**
1. **现象**：无 CRAG 时，On-call prompt 幻觉率 17.2%，通用 prompt 幻觉率 10.3%。
2. **根因**：On-call prompt 要求"按步骤编号、给出具体命令和预期输出"，诱导 LLM 补全文档中没有的命令细节（如 `jmap -dump`、`SLOWLOG GET`）。通用 prompt 只说"根据文档回答"，不确定时直接拒答，反而更保守。
3. **排查**：逐条检查发现，幻觉回答里的编造命令多为"合理但文档没有的"——LLM 基于领域知识补全了文档缺失的细节。
4. **方案**：这是 prompt 设计的 trade-off——"详细"和"保守"不可兼得。CRAG 通过 grade 过滤不相关文档，把幻觉率从 17.2% 降到 11.5%，接近通用 prompt 水平。进一步优化：prompt 加"只引用文档中出现的命令，不要补充"约束。
5. **本项目**：这个发现本身是面试亮点——展示了量化评估如何揭示 prompt 设计的隐藏代价，以及 CRAG 如何部分缓解这个问题。

---
