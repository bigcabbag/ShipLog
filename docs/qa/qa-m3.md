# M3 面试问答卡：React 前端 + SSE 流式

> 按子步（M3.0～M3.5）组织。每完成一步，复习对应章节再进下一步。
> 分步指南见 [M3-steps.md](../steps/M3-steps.md)
>
> **场景题（面经风格，优先复习）** 见各节「### 场景题」；规范见 [qa-scenario-guide.md](./qa-scenario-guide.md)  
> 下方「概念题」供打底，面试模拟以场景题为主。

---

## M3.0 脚手架 + CORS

### 1. 开发时为什么前后端分开两个端口？

- 前端 Vite 跑在 **5173**，后端 FastAPI 跑在 **8000**
- Vite 擅长热更新（改 React 代码秒级刷新），Python 后端不适合塞进 Vite
- 开发期分开，各自独立重启，互不干扰
- 生产环境再用 Nginx 反代，或后端托管前端 `dist/` 静态文件，对外只暴露一个域名

### 2. CORS 是什么？没有它会怎样？

- **CORS**（Cross-Origin Resource Sharing）：浏览器的跨域安全策略
- 前端 `http://127.0.0.1:5173` 调后端 `http://127.0.0.1:8000`，**协议相同但端口不同**，算跨域
- 后端必须在响应头里返回 `Access-Control-Allow-Origin`，浏览器才放行
- 没有 CORS：`fetch` 被浏览器拦截，Network 里能看到请求但 JS 读不到响应
- Postman/curl 不受 CORS 限制，所以 Swagger 能通、浏览器前端不通，多半是 CORS 问题

### 3. 为什么 API 地址放在 `config.ts` 而不是散落在组件里？

- **单一数据源**：改地址只改一处（或改 `.env` 的 `VITE_API_BASE_URL`）
- 组件只关心业务，不关心环境差异（开发 8000、生产可能是 `/api`）
- 对应后端「配置与业务分离」的思路，面试可类比 `.env` + `get_settings()`

### 4. `frontend/src/api/health.ts` 和 `App.tsx` 为什么要分层？

- `api/` 层：封装 HTTP 请求、错误处理、类型定义
- `App.tsx`：只管 UI 状态（loading / ok / error）和渲染
- 好处：M3.1 加 `chat.ts` 时复用同一模式；测试和改接口只动 api 层

### M3.0 自检

- [ ] 能口述：浏览器打开 5173 到显示 health JSON 的完整链路
- [ ] 能解释 CORS 中间件在 `main.py` 哪几行、允许了哪些 origin
- [ ] 能说出 `config.ts` → `health.ts` → `App.tsx` 各自职责

### 场景题（M3.0）

**Q1：** 同事跑起来后端了，但前端页面红字「无法连接后端」，Swagger 正常，你第一次查哪三处？

**A：**
1. 浏览器 F12 → Network：是 CORS 报错还是 `ERR_CONNECTION_REFUSED`
2. 前端 `config.ts` 的 `API_BASE_URL` 是否 `http://127.0.0.1:8000`（不是 8080）
3. 后端是否在跑：`uv run python main.py`，端口 8000

**更好方案：** M3.0 占位页自动调 `/health`，一眼看出连通性（已实现）。

---

**Q2：** 生产环境还要 CORS 吗？和开发环境有什么区别？

**A：**
- **开发**：前后端不同端口（5173/8000），必须 CORS。
- **生产**：Nginx 同域反代 `/api` → 8000，浏览器同源，**可去掉或收紧 CORS**。
- **更好方案**：生产静态文件 + API 一个域名，安全性更好。

**本项目关联：** `main.py` 的 `CORSMiddleware` 仅开发期需要，M5 Docker 文档里写清部署拓扑。

---

---

## M3.1 聊天页（非流式）

### 1. 前端 `fetch` 和后端 `ChatRequest` 怎么对应？

- 前端 POST JSON：`{ "message": "...", "use_rag": true, "top_k": 3 }`
- 后端 `app/schemas.py` 的 `ChatRequest` 用 Pydantic 定义同名字段
- FastAPI 自动把 JSON body 解析成 `ChatRequest` 对象，字段类型/范围不对就 422
- 前端 TypeScript 类型应和后端 schema 保持一致（如 `ChatResponse`、`SourceChunk`）

### 2. `sources` 在前端展示有什么价值？

- 让用户看到 AI 回答**引用了哪些文档片段**（文件名、页码、内容摘要）
- 用户可以核对 AI 是否瞎编——这是 RAG 项目的 **citation（引用）** 能力
- 面试亮点：降低幻觉感知、提高可信度，是企业知识库产品的标配

### 3. 为什么 M3.1 先做非流式，M3.3/M3.4 再做流式？

- **先简后繁**：非流式就是一个 POST → 等完整 JSON，最容易验证前后端字段对齐
- 流式涉及 SSE、`ReadableStream`、增量 state 更新，调试难度高
- 如果非流式都调不通，流式更难定位是 API 问题还是 stream 解析问题

### M3.1 自检

- [ ] 能画出：输入框 → `chat.ts` → `POST /chat` → `rag.py` → 显示 reply + sources
- [ ] 能解释 `use_rag: true` 和 `false` 在前端传参上的区别
- [ ] 能说出加载中状态（disabled 按钮）为什么必要

### 场景题（M3.1）

**Q1：** 前端点了发送，一直转圈最后 502，Swagger 里 `/chat` 正常，你怎么查？

**A：**
1. **现象**：仅前端失败或超时，Swagger 同参数成功 → 多半不是 LLM 逻辑，是**请求体/字段/CORS**。
2. **步骤**：F12 Network 看 POST `/chat` 的 Request Payload 是否含 `message`；Response 里 `detail` 是什么；对比 Swagger 请求体字段名是否一致。
3. **常见根因**：`message` 空字符串（后端 422）；`DEEPSEEK_API_KEY` 未配（500）；CORS 只影响读响应，502 一般是后端异常。
4. **更好方案**：`chat.ts` 统一解析 `detail` 展示给用户（已实现）；加请求 timeout 提示。
5. **本项目**：`frontend/src/api/chat.ts` → `main.py` `chat_endpoint`。

---

**Q2：** 用户反馈「勾了 use_rag 但没有引用来源」，可能哪几种原因？

**A：**
1. **Chroma 为空**：`rag.py` 直接返回「请先上传 PDF」，无 sources。
2. **use_rag 实际为 false**：检查前端 checkbox 和 JSON 里 `use_rag` 字段。
3. **检索无结果**：retrieve 返回空列表，不会进 generate。
4. **后端 bug**：有 reply 但 `sources` 未映射——查 `main.py` 里 `SourceChunk` 转换。
5. **更好方案**：M3.2 上传后显示 `vector_count`；空库时前端禁用 RAG 并提示。
6. **本项目**：`ChatPanel.tsx` 的 sources 在 `<details>` 里展示。

---

**Q3：** 产品经理问「能不能先做流式，非流式以后再说？」你怎么回应？

**A：**
- **现象**：想跳过 M3.1 直接 SSE。
- **建议**：先非流式验证 JSON 字段、RAG 链路、sources 展示；流式是体验优化，不是功能前提。
- **风险**：流式 + RAG 同时调试，出错难分清是 retrieve、SSE 解析还是 UI 增量更新。
- **更好方案**：M3.1 非流式跑通 → M3.3 后端 stream → M3.4 前端接流，分步验收。
- **本项目**：按 `steps/M3-steps.md` 顺序即此策略。

---

## M3.2 上传 + 向量库统计

### 1. `multipart/form-data` 和 JSON POST 有什么区别？

- **JSON POST**（`/chat`）：`Content-Type: application/json`，body 是 JSON 字符串
- **multipart/form-data**（`/documents/upload`）：传文件必须用这种格式，字段可以包含二进制
- 前端上传用 `FormData`，`append("file", pdfFile)`，不能 `JSON.stringify` 文件

### 2. 为什么上传后要调 `/documents/stats`？

- 确认向量**真的写进了 Chroma**（`vector_count > 0`）
- 上传响应虽然有 `indexed_chunks`，但 stats 是全局视角，多次上传后看总量
- 避免用户没上传成功就去聊天，得到「知识库为空」的困惑体验

### 3. M2 后端接口在 M3 需要改吗？

- **不需要**。M2 已经提供了 `/documents/upload`、`/documents/stats`、`/chat`
- M3 只是换了一个调用方：从 Swagger 变成 React 前端
- 这就是前后端分离的好处：后端 API 稳定，前端随便换 UI

### M3.2 自检

- [ ] 能在浏览器里完成：上传 PDF → 看 stats → 提问，全程不打开 Swagger
- [ ] 能解释 `UploadPanel` 和 `ChatPanel` 分别调哪个 API
- [ ] 能说出上传失败时（非 PDF、空文件）前端应该怎么提示

### 场景题（M3.2）

**Q1：** 用户上传 PDF 后界面一直转「上传并索引中…」超过 3 分钟，正常吗？你怎么判断？

**A：**
1. **现象**：首次上传会下载 Embedding 模型（bge-small-zh ~100MB），后端 CPU 切块+向量化，1～3 分钟可能正常。
2. **步骤**：看后端终端有无报错；F12 Network 看 `/documents/upload` 是 pending 还是 500。
3. **根因**：模型下载慢 / PDF 很大 / 内存不足。
4. **更好方案**：异步任务 + 进度条（task_id 轮询）；上传接口先返回 202。
5. **本项目**：M2 同步上传；`UploadPanel` 第 52 行 `setUploading(true)` 直到 fetch 结束。

---

**Q2：** 上传成功 vector_count 还是 0，可能什么原因？

**A：**
1. 看错字段：应看 `indexed_chunks` 和刷新后的 `vector_count`。
2. 后端 `index_chunks` 失败但前端未正确显示 error（查 Network Response）。
3. Chroma 路径权限问题（`data/chroma/`）。
4. **更好方案**：上传响应和 stats 不一致时前端 alert；M4.1 eval 验证检索。
5. **本项目**：`documents.ts` upload 后 `refreshStats()`；`main.py` 185～207 行返回 vector_count。

---

**Q3：** 为什么上传用 FormData，聊天用 JSON？混用会出什么问题？

**A：**
1. **FormData**：传二进制文件，浏览器自动设 `multipart/form-data` boundary。
2. **JSON**：只适合文本字段；把 PDF base64 塞进 JSON 体积大、易错。
3. **混用错误**：对 upload 设 `Content-Type: application/json` → 后端收不到 file → 422。
4. **更好方案**：大文件分片 upload 仍用 multipart。
5. **本项目**：`documents.ts` 第 49～54 行 FormData；`chat.ts` 第 25 行 JSON。

---

## M3.3 后端 SSE 流式接口

### 1. SSE 和 WebSocket 怎么选？

| | SSE | WebSocket |
|---|-----|-----------|
| 方向 | 单向（服务器 → 客户端） | 双向 |
| 协议 | 普通 HTTP，长连接 | 独立协议，需升级 |
| 适用 | AI 逐字输出、日志推送 | 聊天室、协作编辑、游戏 |
| 本项目 | ✅ 够用（用户发完等 AI 吐字） | 过度设计 |

### 2. 为什么 retrieve 不流式，只有 generate 流式？

- **Retrieve**（检索）：后台一步，用户看不到过程，几十毫秒～几百毫秒完成
- **Generate**（生成）：LLM 逐 token 输出，耗时长，用户等待焦虑
- 流式的价值是降低**首字延迟**（TTFT），让用户感觉「AI 在思考并回答」
- RAG 路径：先同步 retrieve 拿到文档 → 再流式 generate

### 3. `StreamingResponse` 和普通 JSON 响应有什么区别？

- 普通 JSON：一次性返回完整 body，然后关闭连接
- `StreamingResponse`：连接保持打开，服务端分多次 `yield` 数据块
- 响应头 `Content-Type: text/event-stream`，格式 `data: {...}\n\n`
- 适合 LLM 长输出，不必等全部生成完才返回

### M3.3 自检

- [ ] 能用 curl 或 Swagger 看到 `/chat/stream` 逐字输出
- [ ] 能解释 SSE 事件格式 `data: {"token": "你"}\n\n`
- [ ] 能说出 RAG 流式时 `sources` 为什么在最后一个事件里返回

### 场景题（M3.3）

**Q1：** Swagger 调 `/chat/stream` 一直不结束、连接挂着，这正常吗？

**A：**
1. **现象**：SSE 连接保持 open，直到 LLM 生成完才发 `done`。
2. **正常**：流式就是长连接；中间多条 `data: {"token":"..."}`。
3. **结束标志**：最后一条 `data: {"done":true,"model":"...","sources":[...]}`。
4. **异常**：长时间无任何 token → 查 API Key、网络、后端日志。
5. **本项目**：`main.py` 195～201 行发 done 事件。

---

**Q2：** 为什么 `sources` 放在最后一个 SSE 事件，而不是每个 token 都带？

**A：**
1. Retrieve 在生成前已完成，sources 一开始就知道。
2. 每个 token 带 sources 浪费带宽、前端重复解析。
3. 前端 M3.4：流式阶段只追加 token，收到 `done` 再渲染引用。
4. **更好方案**：首条事件可先带 `sources` 预览（可选优化）。
5. **本项目**：`prepare_rag_stream` 先检索，`done` 里带 `sources`。

---

**Q3：** `ainvoke` 改 `astream` 后，错误怎么处理？还和 `/chat` 一样抛 HTTPException 吗？

**A：**
1. 流式中途出错时，HTTP 200 可能已发出，无法再改状态码。
2. **做法**：在 generator 里 `yield _sse_event({"error": "..."})` 然后结束。
3. 前端 M3.4 需监听 `error` 字段。
4. **更好方案**：先 retrieve，retrieve 失败仍可用普通 JSON 422/500。
5. **本项目**：`event_generator` 202～205 行 catch 后发 error 事件。

---

## M3.4 前端接 SSE + 打字机

### 1. `EventSource` 和 `fetch` + `ReadableStream` 有什么区别？

- **`EventSource`**：浏览器原生 SSE 客户端，但**只支持 GET**
- **`fetch` + `ReadableStream`**：POST 带 body（如 message、use_rag）时用这个
- 读法：`response.body.getReader()` 循环读 chunk，按 `\n\n` 拆 SSE 事件
- 本项目 `/chat/stream` 是 POST，所以用 fetch stream

### 2. React 里流式更新为什么用 state 追加字符串？

- 每收到一个 token，执行 `setReply(prev => prev + token)`
- 触发 re-render，UI 显示累积文本，用户看到「打字机效果」
- 如果用 `let text += token` 不 setState，React 不会重新渲染，UI 不更新

### 3. 流式对用户体验和 API 成本有什么影响？

- **体验**：首字延迟（TTFT）大幅降低，用户不用盯白屏等 5～10 秒
- **成本**：总 token 数不变，DeepSeek 计费一样
- **注意**：流式中途断连需要前端处理（显示已收到部分 + 重试按钮）

### M3.4 自检

- [ ] 能在聊天框看到打字机效果
- [ ] 能解释 `chatStream.ts` 怎么解析 SSE 事件
- [ ] 能说出流式过程中为什么要禁用发送按钮

### 场景题（M3.4）

**Q1：** 用户说「流式开了但字是一次性蹦出来的，没有打字机」，你怎么查？

**A：**
1. **现象**：Network 里 `/chat/stream` 是 200，但 UI 等很久才整段出现。
2. **步骤**：F12 → Network → `/chat/stream` → 看 Response 是否**逐段**到达；若后端 chunk 正常、UI 仍整段 → 查 React 是否 batch 更新或 `onToken` 没调 `setState`。
3. **常见根因**：误走非流式 `POST /chat`（关掉了「流式输出」）；Nginx/代理缓冲 SSE（缺 `X-Accel-Buffering: no`）；`chatStream.ts` buffer 没按 `\n\n` 拆事件。
4. **更好方案**：开发期直连 8000；生产反代关 buffering；保留流式开关方便 A/B 对比。
5. **本项目**：`ChatPanel.tsx` 51～82 行流式分支；`chatStream.ts` 75～77 行拆 buffer。

---

**Q2：** 流式生成到一半，用户刷新页面，再发新问题，后端还在跑旧请求吗？前端该怎么设计？

**A：**
1. **现象**：长连接断开后，后端 generator 可能还在跑（直到客户端断开被感知），前端 state 已丢。
2. **根因**：SSE 无 session 绑定；刷新 = 新页面，旧流无法续上。
3. **步骤**：M3.4 用 `loading` 禁发，流完才解锁；断连时保留已收 token + 提示「流式中断」（`chatStream.ts` 111～113 行）。
4. **更好方案**：`AbortController` + 停止按钮；或 request_id 关联会话（M5 可加）。
5. **本项目**：M3.4 刻意不做 Abort，M3.5 可 polish。

---

**Q3：** 同事建议用浏览器原生 `EventSource` 接 SSE，说代码更短，你同不同意？

**A：**
1. **现象**：`EventSource` 只能 **GET**，不能 POST JSON body。
2. **根因**：本项目 `/chat/stream` 要传 `message`、`use_rag`，必须 POST。
3. **选项**：改后端 GET + query（URL 长度、日志泄露）| 用 `fetch` + `ReadableStream`（当前方案）| 引 `fetch-event-source` 库。
4. **更好方案**：POST SSE 用 fetch stream，无新依赖，面试能讲清解析逻辑。
5. **本项目**：`frontend/src/api/chatStream.ts`；后端 `main.py` 166 行 POST。

---

**Q4：** 流式过程中用户连点两次发送，会出现两个回答叠在一个气泡里吗？你怎么防？

**A：**
1. **现象**：重复 POST，消息列表乱序或重复 assistant 气泡。
2. **根因**：`loading` 未禁发送 / 示例按钮 / Enter 快捷键。
3. **做法**：`sendMessage` 开头 `if (loading) return`；textarea、发送、示例按钮、`streamOn`/`useRag` 开关均 `disabled={loading}`。
4. **更好方案**：in-flight 请求用 ref 记 assistantId；或 Abort 上一次（未做）。
5. **本项目**：`ChatPanel.tsx` 40、153～163、176、234、242 行。

---

## M3.5 总验收 + 工程化

### 1. 从用户点发送到看到第一个字，经过哪些层？

1. 用户在前端 `ChatPanel` 输入并点击发送
2. `chatStream.ts` 发 `POST /chat/stream`（JSON body）
3. FastAPI 路由 → `rag_chat_stream()` 或 `chat_stream()`
4. RAG 路径：`retriever.py` 检索文档 → 拼 prompt
5. `llm.py` 的 `astream` 逐 token 调 DeepSeek
6. `StreamingResponse` 把每个 token 作为 SSE 事件推给前端
7. 前端 `ReadableStream` 读 chunk → `setState` 追加 → UI 更新

### 2. 生产环境前后端怎么部署？

常见两种：

- **同域反代**：Nginx 把 `/api` 转发到 FastAPI，`/` 托管 React `dist/`，无 CORS 问题
- **Docker Compose**：一个容器跑 uvicorn，一个容器跑 Nginx 静态文件，或合并成一个镜像

开发期的 CORS 配置生产环境可以收紧或去掉（同域不需要）。

### 3. 如果 SSE 连接断了，前端应该怎么处理？

- 显示已收到的部分内容，不要直接清空
- 提示「连接中断，请重试」
- 提供重发按钮（重新 POST `/chat/stream`）
- 可选：自动重试 1～2 次，带 exponential backoff
- 记录错误日志（后续 M5 可加 Sentry）

### M3.5 自检

- [ ] 能 30 秒口述 M3 项目是什么、解决什么问题
- [ ] 能 2 分钟讲清前后端架构 + 技术栈
- [ ] 能对比 M2（纯 API）和 M3（全栈）你多了什么能力

### 场景题（M3.5）

**Q1：** 新人 clone 仓库后，前端能开、后端 health 正常，但聊天一直 502，你怎么带他排查？

**A：**
1. **现象**：UI 能加载，`/health` OK，发消息失败。
2. **步骤**：看 Network 里 `/chat/stream` 或 `/chat` 的 Response `detail`；查 `.env` 是否有 `DEEPSEEK_API_KEY`；后端终端是否报 DeepSeek 异常。
3. **常见根因**：只启了前端没启后端；API Key 未配；向量库空但 use_rag 开（应返回提示而非 502，502 多半是 LLM 调用失败）。
4. **更好方案**：README 写双终端启动；前端 health 检测已做，可再加 Key 缺失友好提示。
5. **本项目**：`scripts/dev.ps1` + `dev-frontend.ps1`；`App.tsx` 后端状态条。

---

**Q2：** 上线时前端 `5173`、后端 `8000` 分两个端口，CORS 报错，生产怎么解？

**A：**
1. **现象**：浏览器 Console 报 CORS，Swagger 直连 8000 正常。
2. **根因**：跨域；开发期 `main.py` 允许 5173，生产不应长期靠宽松 CORS。
3. **步骤**：Nginx 同域反代 `/api` → 8000、静态 → `frontend/dist`；或 Docker Compose 统一入口。
4. **更好方案**：生产同域，去掉或收紧 CORS；开发保留 5173→8000。
5. **本项目**：`main.py` CORS 仅开发；M5 Docker 可一并解决。

---

**Q3：** 面试官问「M3 你比 M2 多做了什么，值不值得写简历」，你怎么答？

**A：**
1. **M2**：FastAPI + RAG 链路，Swagger 验收，证明 retrieve→generate 能跑。
2. **M3 增量**：React 全栈 UI、PDF 上传、SSE 流式打字机、feature 分支 PR 流程。
3. **价值**：贴近真实产品形态（用户不打开 Swagger）；能讲前后端数据流和 SSE trade-off。
4. **诚实边界**：评估指标、Agent、混合检索在 M4；M3 是全栈交付里程碑。
5. **本项目**：见 qa-m3「M3 综合对比」表。

---

**Q4：** M3 要合并 PR 了，Review 同事说「流式和非流式两套逻辑重复」，你怎么回应？

**A：**
1. **现象**：`ChatPanel` 里 `streamOn` 分支 + `postChat` 分支代码相似。
2. **短期理由**：M3.1 先非流式跑通，M3.4 加流式，保留开关便于对比和回退。
3. **重构方向**：抽 `sendChat({ stream })` 统一错误处理；或默认只留流式，非流式当 fallback。
4. **更好方案**：M3.5 不强行大 refactor；M4 前若稳定可合并路径。
5. **本项目**：`ChatPanel.tsx` 51～135 行；spec 明确 YAGNI。

---

## M3 综合对比（面试速记）

| 维度 | M2 | M3 |
|------|----|----|
| 调用方式 | Swagger / curl | React 浏览器 UI |
| 响应方式 | 一次性 JSON | SSE 流式 + 打字机 |
| 文件上传 | Swagger 表单 | 前端 UploadPanel |
| Git 流程 | 直接 master | feature 分支 + PR |
