# rag-agent

**DevKit — 研发团队文档助手**：帮新人查本仓库 PLAN、分步指南、qa 卡与 API 说明。  
业务场景详见 [docs/SCENARIO.md](./docs/SCENARIO.md)。

企业知识库 RAG 学习项目（Python 3.12 + uv + FastAPI + React）。

## 环境要求

- uv（`%USERPROFILE%\.local\bin`）
- Python 3.12（`.python-version`）
- Node.js 18+（M3 前端）

## 快速开始（全栈）

**1. 配置 API Key**

```powershell
copy .env.example .env
# 编辑 .env，填入 DEEPSEEK_API_KEY
```

**2. 启动后端（终端 1）**

```powershell
cd E:\01_Dev\langChain
.\scripts\dev.ps1
```

**3. 启动前端（终端 2）**

```powershell
cd E:\01_Dev\langChain
.\scripts\dev-frontend.ps1
```

**4. 导入本项目文档（M4.0 推荐）**

```powershell
uv run python scripts/import_docs.py
```

会把 `docs/*.md` 写入向量库。然后浏览器验收：

打开 http://127.0.0.1:5173

1. 确认 vector_count > 0（或左侧刷新统计）
2. 问「M3 分几步？」→ 应引用 `M3-steps.md` + 引用来源
3. 也可上传 PDF / Markdown 单文件补充知识库
4. 默认流式提问，可关「流式输出」对比非流式

后端健康检查：http://127.0.0.1:8000/health  
API 文档：http://127.0.0.1:8000/docs

## 仅后端（M0～M2）

```powershell
uv sync
uv run python main.py
```

## 前端环境变量

见 `frontend/.env.example`（默认 `VITE_API_BASE_URL=http://127.0.0.1:8000`）。

## 主要接口

| 接口 | 说明 |
|------|------|
| `POST /documents/upload` | 上传 PDF / Markdown 入库 |
| `GET /documents/stats` | 向量库统计 |
| `POST /chat` | 非流式对话（JSON 一次返回） |
| `POST /chat/stream` | SSE 流式对话（M3.3+） |

| 脚本 | `uv run python scripts/import_docs.py` 批量导入 `docs/*.md` |
| 评估 | `uv run python eval/run_eval.py` 输出 Recall@3（见 [eval/BASELINE.md](./eval/BASELINE.md)） |

## 学习进度

见 [docs/PLAN.md](./docs/PLAN.md) · [docs/M4-steps.md](./docs/M4-steps.md) · 面试题 [docs/qa-m4.md](./docs/qa-m4.md)

## Cursor / VS Code

解释器：`.venv\Scripts\python.exe`（`.vscode/settings.json` 已配置）
