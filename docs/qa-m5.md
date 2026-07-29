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
