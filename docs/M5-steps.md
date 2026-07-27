# M5 分步指南：简历交付 + 生产化收尾

> 前置：M4 全部完成（含 M4.4 trace_id）。  
> 场景面试题见 [qa-scenario-guide.md](./qa-scenario-guide.md)。

**当前进度：未开始（M4 完成后说「继续 M5.0」）**

---

## 总览

```mermaid
flowchart LR
  M50[M5.0 Docker Compose] --> M51[M5.1 README 简历化]
  M51 --> M52[M5.2 场景面试 20 题]
  M52 --> M53[M5.3 pgvector 最小迁移]
```

| 子步 | 做什么 | 改动范围 | 场景题重点 |
|------|--------|----------|-----------|
| M5.0 | Docker 一键启动（后端+前端，**仍用 Chroma**） | `Dockerfile`、`docker-compose.yml` | 「怎么部署演示」 |
| M5.1 | README 简历化 + 3 分钟介绍稿 | `README.md` | 「项目亮点一句话」 |
| M5.2 | 模拟面试 20 题验收 | [qa-scenario-guide.md](./qa-scenario-guide.md) | 场景题 ≥15/20 |
| M5.3 | **Chroma → pgvector**（仅换向量层） | 主改 `store.py` + Compose 加 Postgres | 「为什么上 pgvector」 |

> **约定**：pgvector **放在 M5 最后**（M5.3）。M5.0～M5.2 继续用 Chroma，避免 Docker/面试与 DB 迁移搅在一起。

---

## M5.0 Docker Compose

**目标**：他人 `docker compose up` 能跑通上传 + 聊天 + eval（Chroma 数据卷挂载）。

### 要做的事

- 后端 `Dockerfile`（uv + `main.py`）
- 前端构建 + 静态或 dev 代理（与现有 `API_BASE_URL` 一致）
- `docker-compose.yml`：backend、frontend；挂载 `data/chroma`、`data/bm25`
- `.env.example` 说明 `DEEPSEEK_API_KEY` 等

### 验收

- 新机器仅依赖 Docker + `.env` 能打开 UI 并 RAG 问答
- `GET /documents/stats` 正常

### 场景题

「本地开发和 Docker 部署差在哪？数据卷怎么挂？」

---

## M5.1 README 简历化

**目标**：GitHub 首页能当简历项目链接，3 分钟能讲完。

### 要做的事

- README：场景、架构图、技术栈、启动命令、eval 数字（Recall@3）
- 链到 `docs/SCENARIO.md`、`eval/BASELINE.md`
- 写一版 **3 分钟口述稿**（可放 README 末尾或 `docs/PITCH.md`）

### 验收

- 外人只看 README 知道怎么跑、解决什么问题
- 你能不看稿讲完：入库 → 混合检索 → CRAG → 流式

### 场景题

「用 3 分钟介绍你的 RAG 项目。」

---

## M5.2 场景面试 20 题

**目标**：按 [qa-scenario-guide.md](./qa-scenario-guide.md) 自测，场景题能答 trade-off。

### 要做的事

- 过一遍 M1～M4 问答卡 + 场景题模板
- 模拟追问：Retrieve miss、混合检索、CRAG 拒答、部署

### 验收

- 自测 **≥15/20** 题能答到「现象 → 根因 → 排查 → 更好方案」
- 能白板画 RAG 数据流 + 混合检索 RRF

### 场景题

「模拟腾讯 RAG 面」——从 qa-scenario-guide 抽题。

---

## M5.3 pgvector 最小迁移（M5 最后一步）

**目标**：向量存储从 **Chroma 换成 PostgreSQL + pgvector**；**不大改**检索/CRAG/前端；BM25 仍用 `corpus.json`。

### 范围（ deliberately 缩小）

| 要改 | 不改 |
|------|------|
| `app/rag/store.py`（`get_vector_store` → PGVector） | `retriever.py`（仍 `similarity_search`） |
| `docker-compose.yml` 增加 **postgres** 服务 + pgvector 扩展 | `graph.py` / CRAG 流程 |
| `pyproject.toml` 增加 PG 相关依赖 | 前端 |
| `.env`：`DATABASE_URL` | 混合检索 RRF 逻辑 |
| `rebuild_from_vector_store` 改为从 PG 读（或重跑 import） | 聊天历史 / 用户表（**本步不做**） |

### PG 里存什么（本步仅）

```text
document_chunks：
  - page_content
  - embedding（vector 类型，pgvector）
  - metadata：source、chunk_id
```

**不进 PG（本步）**：BM25 语料、chat 历史、users、trace 表（trace 仍可按 M4.4 方案，后续再迁 PG）。

### 要做的事

1. Compose：`postgres:16` + 初始化脚本 `CREATE EXTENSION vector`
2. 实现 `get_vector_store()` 返回 LangChain **PGVector**（或等价封装）
3. `index_chunks`：按 `source` 删旧 + `add_documents`（与现逻辑一致）
4. 迁移：重跑 `scripts/import_docs.py` + `rebuild_from_vector_store`（或一次性 import 脚本）
5. README 增加一节：**「开发用 Chroma / 生产演示用 pgvector」** 或环境变量切换 `VECTOR_BACKEND=chroma|pg`

### 验收

- `eval/run_eval.py` Recall@3 与 M4.3 Chroma 版 **持平**（记录进 `eval/BASELINE.md`）
- `vector_count` / stats 接口仍可用
- 能口述：**只改 store 层，为什么 pgvector**（SQL filter、生产一体化）

### 场景题

「为什么从 Chroma 迁到 pgvector？迁移要改哪些模块？BM25 为什么还放 JSON？」

### trade-off（面试）

- **得**：生产叙事、metadata SQL 过滤、与 Postgres 生态一致  
- **舍**：部署变重、本地开发需起 Postgres；本步 **不** 顺带做 Redis / 聊天表  

---

## 下一步

M4.4 完成后说 **「继续 M5.0」**；pgvector 说 **「继续 M5.3」**（需 M5.0 Docker 基础）。
