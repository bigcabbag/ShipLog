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

**Q4：** 面试 30 秒怎么讲 Docker 这一步？

**A：**
> M5.0 用 Compose 起 backend（uvicorn + Chroma 卷，:8032→8000）和 frontend（nginx 静态页）。浏览器通过 localhost:8032 调 API，首次 `docker compose exec` 跑 import_docs。为 M5.1 pgvector 打基础，别人 clone 后只需 Docker + `.env` 能演示 RAG。

---
