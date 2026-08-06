from pathlib import Path
import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse

from app.config import get_embedding_model, get_settings
from app.llm import chat, chat_stream
from app.rag.checkpointer import close_async_checkpointer, get_async_checkpointer
from app.rag.rag import prepare_rag_stream_async, rag_chat
from app.rag.session import load_thread_history, record_thread_turn, resolve_thread_id
from app.rag.loader import (
    DEFAULT_CHUNK_OVERLAP,
    DEFAULT_CHUNK_SIZE,
    SUPPORTED_SUFFIXES,
    load_and_split_document,
)
from app.rag.store import get_index_stats, index_chunks
from app.rag.trace import load_trace
from app.schemas import (
    ChatRequest,
    ChatResponse,
    ChunkPreview,
    IndexStatsResponse,
    SourceChunk,
    UploadResponse,
)

UPLOAD_DIR = Path("data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
PREVIEW_CHARS = 200


def _sse_event(payload: dict) -> str:
    """SSE 单行事件：data: {...}\\n\\n"""
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


@asynccontextmanager
async def lifespan(app: FastAPI):
    await get_async_checkpointer()
    yield
    await close_async_checkpointer()


app = FastAPI(title="RAG Agent", version="0.1.0", lifespan=lifespan)

# Docker 经 frontend nginx 同源反代时可不依赖 CORS；保留供直连 8032 / 本地调试
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_class=HTMLResponse)
async def home():
    """测试导航页：从根路径快速跳到 Swagger 和各接口。"""
    return """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>RAG Agent 测试台</title>
  <style>
    * { box-sizing: border-box; }
    body {
      font-family: system-ui, -apple-system, sans-serif;
      max-width: 720px;
      margin: 48px auto;
      padding: 0 20px;
      color: #1a1a1a;
      background: #f8fafc;
    }
    h1 { font-size: 1.5rem; margin-bottom: 0.25rem; }
    p.sub { color: #64748b; margin-top: 0; }
    .card {
      background: #fff;
      border: 1px solid #e2e8f0;
      border-radius: 12px;
      padding: 20px;
      margin: 16px 0;
    }
    .card h2 { font-size: 1rem; margin: 0 0 12px; }
    a.btn {
      display: inline-block;
      margin: 6px 8px 6px 0;
      padding: 10px 16px;
      background: #2563eb;
      color: #fff !important;
      text-decoration: none;
      border-radius: 8px;
      font-size: 14px;
    }
    a.btn:hover { background: #1d4ed8; }
    a.btn.secondary { background: #475569; }
    a.btn.secondary:hover { background: #334155; }
    code { background: #f1f5f9; padding: 2px 6px; border-radius: 4px; font-size: 13px; }
    ol { padding-left: 1.25rem; line-height: 1.8; color: #334155; }
    .tip { color: #b45309; font-size: 14px; }
  </style>
</head>
<body>
  <h1>RAG Agent 测试台</h1>
  <p class="sub">企业知识库 RAG · M2 基础链路</p>

  <div class="card">
    <h2>快速跳转</h2>
    <a class="btn" href="/docs">打开 Swagger 测试页</a>
    <a class="btn secondary" href="/health">健康检查 /health</a>
    <a class="btn secondary" href="/documents/stats">向量库统计 /documents/stats</a>
  </div>

  <div class="card">
    <h2>推荐测试顺序</h2>
    <ol>
      <li><code>POST /documents/upload</code> 上传 PDF</li>
      <li><code>GET /documents/stats</code> 确认 vector_count &gt; 0</li>
      <li><code>POST /chat</code> 设 <code>use_rag: true</code> 提问</li>
    </ol>
  </div>

  <div class="card">
    <h2>/chat 示例请求体</h2>
    <pre style="background:#f1f5f9;padding:12px;border-radius:8px;overflow:auto;font-size:13px;">{
  "message": "骆健渤做过什么项目？",
  "use_rag": true,
  "top_k": 3
}</pre>
  </div>

  <p class="tip">注意：服务跑在 <strong>http://127.0.0.1:8000</strong>，不是 8080。</p>
</body>
</html>
"""


@app.get("/health")
async def health():
    return {"status": "ok", "message": "服务运行中"}


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(body: ChatRequest):
    try:
        settings = get_settings()
        if body.use_rag:
            reply, raw_sources, trace_id, extracted, plan_steps, thread_id = await rag_chat(
                body.message,
                top_k=body.top_k,
                system_prompt=body.system_prompt,
                image_base64=body.image_base64,
                image_media_type=body.image_media_type,
                thread_id=body.thread_id,
            )
            sources = [SourceChunk(**item) for item in raw_sources] or None
            return ChatResponse(
                reply=reply,
                model=settings["model"],
                sources=sources,
                trace_id=trace_id,
                extracted_query=extracted,
                thread_id=thread_id,
                plan_steps=plan_steps or None,
            )

        if body.image_base64:
            raise HTTPException(status_code=400, detail="截图提问需开启 use_rag")
        tid = resolve_thread_id(body.thread_id)
        history = await load_thread_history(tid)
        reply = await chat(body.message, body.system_prompt, history=history)
        if reply.strip():
            try:
                await record_thread_turn(tid, user=body.message, assistant=reply)
            except Exception as exc:
                raise HTTPException(
                    status_code=500,
                    detail=f"回复已生成，但会话保存失败: {exc}",
                ) from exc
        return ChatResponse(reply=reply, model=settings["model"], thread_id=tid)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        detail = str(exc)
        if "aliyun" in detail.lower() or "dashscope" in detail.lower():
            raise HTTPException(
                status_code=502,
                detail=f"调用通义读图失败: {exc}",
            ) from exc
        raise HTTPException(
            status_code=502,
            detail=f"调用 DeepSeek 失败: {exc}",
        ) from exc


@app.post("/chat/stream")
async def chat_stream_endpoint(body: ChatRequest):
    """M3.3：SSE 流式对话。事件：{"token":"..."} 逐条推送，最后 {"done":true,"model":"...","sources":[...]}。"""

    async def event_generator():
        try:
            settings = get_settings()
            model = settings["model"]
            sources: list[dict] | None = None
            stream_prompt: str | None = body.system_prompt
            trace_id: str | None = None
            extracted_query: str | None = None

            stream_user_message = body.message or "请根据截图排查。"
            plan_steps: list[str] = []
            thread_id = resolve_thread_id(body.thread_id)
            chat_history = await load_thread_history(thread_id)

            if body.use_rag:
                (
                    rag_prompt,
                    raw_sources,
                    early_reply,
                    trace_id,
                    extracted_query,
                    stream_user_message,
                    plan_steps,
                    thread_id,
                ) = await prepare_rag_stream_async(
                    body.message,
                    top_k=body.top_k,
                    system_prompt=body.system_prompt,
                    image_base64=body.image_base64,
                    image_media_type=body.image_media_type,
                    thread_id=thread_id,
                )
                if plan_steps:
                    yield _sse_event(
                        {
                            "plan_steps": plan_steps,
                            "thread_id": thread_id,
                        }
                    )
                if early_reply is not None:
                    if early_reply.strip():
                        try:
                            await record_thread_turn(
                                thread_id,
                                user=stream_user_message,
                                assistant=early_reply,
                            )
                        except Exception as exc:
                            yield _sse_event(
                                {"warning": f"回复已生成，但会话保存失败: {exc}"}
                            )
                    yield _sse_event({"token": early_reply})
                    yield _sse_event(
                        {
                            "done": True,
                            "model": model,
                            "sources": [],
                            "trace_id": trace_id,
                            "extracted_query": extracted_query,
                            "thread_id": thread_id,
                            "plan_steps": plan_steps,
                        },
                    )
                    return
                stream_prompt = rag_prompt
                sources = raw_sources

            full_reply: list[str] = []
            async for token in chat_stream(
                stream_user_message,
                system_prompt=stream_prompt,
                history=chat_history,
            ):
                full_reply.append(token)
                yield _sse_event({"token": token})

            reply_text = "".join(full_reply)
            if reply_text.strip():
                try:
                    await record_thread_turn(
                        thread_id,
                        user=stream_user_message,
                        assistant=reply_text,
                    )
                except Exception as exc:
                    yield _sse_event(
                        {"warning": f"回复已生成，但会话保存失败: {exc}"}
                    )

            yield _sse_event(
                {
                    "done": True,
                    "model": model,
                    "sources": sources,
                    "trace_id": trace_id,
                    "extracted_query": extracted_query,
                    "thread_id": thread_id,
                    "plan_steps": plan_steps,
                }
            )
        except ValueError as exc:
            yield _sse_event({"error": str(exc)})
        except RuntimeError as exc:
            yield _sse_event({"error": str(exc)})
        except Exception as exc:
            detail = str(exc)
            if "aliyun" in detail.lower() or "dashscope" in detail.lower():
                yield _sse_event({"error": f"调用通义读图失败: {exc}"})
            else:
                yield _sse_event({"error": f"调用 DeepSeek 失败: {exc}"})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/traces/{trace_id}")
async def get_trace(trace_id: str):
    """M4.4：按 trace_id 回放当次 CRAG 检索过程。"""
    record = load_trace(trace_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"trace_id 不存在: {trace_id}")
    return record


@app.post("/documents/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """上传 PDF / Markdown → 切块 → Embedding → 写入 Chroma。"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="缺少文件名")
    suffix = Path(file.filename).suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        allowed = ", ".join(sorted(SUPPORTED_SUFFIXES))
        raise HTTPException(status_code=400, detail=f"目前只支持 {allowed} 文件")

    save_path = UPLOAD_DIR / file.filename
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="文件为空")

    save_path.write_bytes(content)

    try:
        chunks = load_and_split_document(save_path)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"文档解析失败: {exc}",
        ) from exc

    if not chunks:
        raise HTTPException(status_code=400, detail="文件中未提取到可索引文本")

    try:
        indexed = index_chunks(chunks, source=file.filename)
        stats = get_index_stats()
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"向量入库失败: {exc}",
        ) from exc

    previews = [
        ChunkPreview(
            index=i,
            content=chunk.page_content[:PREVIEW_CHARS],
            metadata=chunk.metadata,
        )
        for i, chunk in enumerate(chunks[:3])
    ]

    return UploadResponse(
        filename=file.filename,
        chunk_count=len(chunks),
        chunk_size=DEFAULT_CHUNK_SIZE,
        chunk_overlap=DEFAULT_CHUNK_OVERLAP,
        indexed_chunks=indexed,
        vector_count=int(stats["vector_count"]),
        embedding_model=get_embedding_model(),
        previews=previews,
    )


@app.get("/documents/stats", response_model=IndexStatsResponse)
async def document_stats():
    """查看 Chroma 里当前有多少条向量。"""
    stats = get_index_stats()
    return IndexStatsResponse(
        collection=str(stats["collection"]),
        vector_count=int(stats["vector_count"]),
        embedding_model=get_embedding_model(),
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
