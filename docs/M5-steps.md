# M5 分步指南：简历交付 + 生产化收尾

> 前置：M4 全部完成（含 M4.4 trace_id）。  
> 场景面试题见 [qa-scenario-guide.md](./qa-scenario-guide.md)。

**当前进度：M5.0 已验收通过（后端 :8032 + 前端 :5173），待 commit**

---

## 总览

```mermaid
flowchart LR
  M50[M5.0 Docker Compose] --> M51[M5.1 PG 向量 + trace]
  M51 --> M52[M5.2 README 简历化]
  M52 --> M53[M5.3 场景面试 20 题]
```

| 子步 | 做什么 | 改动范围 | 场景题重点 |
|------|--------|----------|-----------|
| M5.0 | Docker 一键启动（后端+前端，**仍用 Chroma**） | `Dockerfile`、`docker-compose.yml` | 「怎么部署演示」 |
| M5.1 | **Chroma → pgvector** + **trace 迁 PG** | `store.py`、`trace.py`、Compose 加 Postgres | 「为什么上 pgvector / trace 表怎么查」 |
| M5.2 | README 简历化 + 3 分钟介绍稿 | `README.md`、`docs/PITCH.md` | 「项目亮点一句话」 |
| M5.3 | 模拟面试 20 题验收 | [qa-scenario-guide.md](./qa-scenario-guide.md) | 场景题 ≥15/20 |

> **约定**：**M5.0** 先 Docker 跑通（Chroma 卷）；**M5.1** 立刻上 Postgres（向量 + trace），README/面试放后面，文档里能写「生产栈：PG + pgvector」。

---

## M5.0 Docker Compose

**目标**：他人 `docker compose up` 能跑通上传 + 聊天 + eval（Chroma 数据卷挂载）。

### 要做的事

- 后端 `Dockerfile`（uv + `main.py`）
- `frontend/Dockerfile` + nginx 静态托管（`VITE_API_BASE_URL=http://localhost:8032`）
- `docker-compose.yml`：backend、frontend；挂载 `data/chroma`、`data/bm25`、`data/traces`
- `.env.example` 说明 `DEEPSEEK_API_KEY` 与 Docker 启动步骤

### 快速命令

```powershell
copy .env.example .env
# 编辑 .env 填入 DEEPSEEK_API_KEY
docker compose up --build
# 另开终端：首次入库
docker compose exec backend uv run python scripts/import_docs.py
```

浏览器：http://localhost:5173 · API：http://localhost:8032/health

### 验收

- 新机器仅依赖 **Docker Desktop** + `.env` 能打开 UI 并 RAG 问答
- `GET /documents/stats` 正常

### 场景题

「本地开发和 Docker 部署差在哪？数据卷怎么挂？」

---

## M5.1 PostgreSQL：pgvector + trace（原 M5.3，提前）

**目标**：向量与 trace 日志都进 **PostgreSQL**；**不大改**检索/CRAG/前端；BM25 仍用 `corpus.json`。

### 范围

| 要改 | 不改 |
|------|------|
| `app/rag/store.py`（`get_vector_store` → PGVector） | `retriever.py`（仍 `similarity_search`） |
| `app/rag/trace.py`（JSONL → PG 表，`trace_id` 索引） | `graph.py` / CRAG 流程 |
| `docker-compose.yml` 增加 **postgres** + pgvector 初始化 | 混合检索 RRF 逻辑 |
| `pyproject.toml` PG 依赖；`.env`：`DATABASE_URL` | 前端 |
| `GET /traces/{id}` 改为查 PG | 聊天历史 / users 表（**本步不做**） |

### PG 里存什么

```text
document_chunks（pgvector）：
  - page_content, embedding, metadata（source、chunk_id）

rag_traces：
  - trace_id（唯一索引）, question, steps（JSONB）, created_at, route, …
```

**不进 PG（本步）**：BM25 语料（仍 `data/bm25/corpus.json`）、chat 历史、users。

### 要做的事

1. Compose：`postgres:16` + 初始化 `CREATE EXTENSION vector`
2. `get_vector_store()` → LangChain **PGVector**
3. `save_trace` / `load_trace` → INSERT + `WHERE trace_id = ?`
4. 迁移：重跑 `scripts/import_docs.py` + `rebuild_from_vector_store`
5. 环境变量：`VECTOR_BACKEND=chroma|pg`（本地可仍 Chroma，Docker 默认可 PG）

### 验收

- `eval/run_eval.py` Recall@3 与 M4.3 Chroma 版 **持平**（记入 `eval/BASELINE.md`）
- `GET /traces/{trace_id}` 从 PG 回放，中文 question 正常
- `vector_count` / stats 接口仍可用

### 场景题

「为什么从 Chroma 迁到 pgvector？trace 为什么也进 PG？BM25 为什么还放 JSON？」

### trade-off（面试）

- **得**：向量 + trace 统一存储、trace 按 id 索引、生产叙事  
- **舍**：部署变重；本步 **不** 做 Redis / 聊天表  

### 环境准备（见下节）

M5.1 需要 **Docker 已装好**（M5.0 验收过）；**不必单独安装 PostgreSQL 安装包**，PG 跑在 Compose 容器里。

---

## M5.2 README 简历化

**目标**：GitHub 首页能当简历项目链接，3 分钟能讲完（可写 PG + pgvector + trace 表）。

### 要做的事

- README：场景、架构图、技术栈、Docker/PG 启动命令、eval 数字（Recall@3）
- 链到 `docs/SCENARIO.md`、`eval/BASELINE.md`
- 写一版 **3 分钟口述稿**（`README` 末尾或 `docs/PITCH.md`）

### 验收

- 外人只看 README 知道怎么跑、解决什么问题
- 你能不看稿讲完：入库 → 混合检索 → CRAG → trace → 流式

### 场景题

「用 3 分钟介绍你的 RAG 项目。」

---

## M5.3 场景面试 20 题

**目标**：按 [qa-scenario-guide.md](./qa-scenario-guide.md) 自测，场景题能答 trade-off。

### 要做的事

- 过一遍 M1～M4 问答卡 + 场景题模板
- 模拟追问：Retrieve miss、混合检索、CRAG 拒答、Docker/PG 部署、trace 排查

### 验收

- 自测 **≥15/20** 题能答到「现象 → 根因 → 排查 → 更好方案」
- 能白板画 RAG 数据流 + 混合检索 RRF + trace 查 PG

### 场景题

「模拟腾讯 RAG 面」——从 qa-scenario-guide 抽题。

---

## 环境：要装什么？

| 软件 | M5.0 | M5.1 | 说明 |
|------|------|------|------|
| **Docker Desktop** | ✅ 必须 | ✅ 必须 | Windows 装这一个即可跑 Compose |
| **PostgreSQL 安装包** | ❌ 不需要 | ❌ 不需要 | PG 在 `docker-compose` 的 **postgres 容器**里 |
| **单独装 pgvector** | ❌ | ❌ | 容器初始化脚本 `CREATE EXTENSION vector` |

**推荐路径**：

1. 安装 [Docker Desktop for Windows](https://docs.docker.com/desktop/setup/install/windows-install/)（WSL2 后端）
2. M5.0：`docker compose up` → 后端 + 前端 + Chroma 卷
3. M5.1：Compose 加 `postgres` 服务 → `docker compose up` 自动拉起 PG，**不用本机再装数据库**

本地开发（不用 Docker 跑 app）时：可只 `docker compose up postgres`，本机 `uv run uvicorn` 连 `DATABASE_URL=postgresql://...@localhost:5432/...`。

---

## 下一步

说 **「继续 M5.0」** 写 Docker；M5.0 验收后再 **「继续 M5.1」** 上 PG + trace。
