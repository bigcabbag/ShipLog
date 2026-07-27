# CodeGraph 速查（本仓库）

> 索引：`codegraph init` 已完成（25 files, 252 nodes）。改代码后：`codegraph sync`

## 改 X 时先看谁调谁

```powershell
codegraph callers <符号名>
codegraph callees <符号名>
codegraph query "<关键词>"
codegraph impact <符号名>    # 改这个会影响谁
```

## M4.2 CRAG / RAG 主链（codegraph 核实）

```
POST /chat/stream (main.py)
  └─ event_generator
       └─ prepare_rag_stream_async (rag.py)
            └─ run_crag_prepare (graph.py)
                 └─ get_crag_graph().ainvoke
                      ├─ _retrieve_node → retrieve → vector + BM25 → RRF
                      ├─ _grade_node → llm.chat + _format/_parse
                      ├─ _rewrite_node → llm.chat
                      ├─ _build_generate_node → context.build_context
                      └─ _abstain_node
            └─ save_trace (trace.py) → data/traces/traces.jsonl
            └─ (图外) llm.chat_stream 流式生成

POST /chat (main.py)
  └─ chat_endpoint → rag_chat
       ├─ run_crag_prepare (同上 + save_trace)
       └─ llm.chat

GET /traces/{trace_id} (main.py) → load_trace (trace.py)
```

## 入库 / 评估（不经 graph）

```
scripts/import_docs.py → load_and_split_markdown → index_chunks → store
eval/run_eval.py → retrieve (只评 Recall@3)
POST /documents/upload → load_and_split_document → index_chunks
```

## 文件 → 职责（改错地方时查）

| 改什么 | 文件 |
|--------|------|
| CRAG 节点/分支 | `app/rag/graph.py` |
| trace 日志 | `app/rag/trace.py` |
| RAG 对外 API | `app/rag/rag.py` |
| prompt/context | `app/rag/context.py` |
| 向量检索 | `app/rag/retriever.py` |
| BM25 索引 | `app/rag/bm25_index.py` |
| Chroma 入库 | `app/rag/store.py` |
| PDF/Md 切块 | `app/rag/loader.py` |
| HTTP 路由 | `main.py` |
| SSE 前端 | `frontend/src/api/chatStream.ts` |
| eval 题/脚本 | `eval/questions.json`, `eval/run_eval.py` |

## Cursor 里

MCP `codegraph_explore` 问：`run_crag_prepare rag_chat graph CragState`（需 `codegraph serve` 或 MCP 连上）
