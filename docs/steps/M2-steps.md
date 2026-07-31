# M2 分步指南：基础 RAG

M2 拆成 3 小步，从简到难。**当前进度：M2.3 已完成代码，待你验收。**

---

## M2.1 上传 PDF → 切块 ✅

**目标**：把 PDF 变成很多小文本块（Document）。

```
Load → Split → Embed → Store → Retrieve → Generate
 ↑       ↑
M2.1   M2.1
```

### 新增文件

| 文件 | 作用 |
|------|------|
| `app/rag/loader.py` | PyPDFLoader 读 PDF + RecursiveCharacterTextSplitter 切块 |
| `POST /documents/upload` | 接收 PDF，保存到 `data/uploads/` |

---

## M2.2 Embedding + Chroma ✅

**目标**：把每块文本变成向量，存入本地 Chroma。

```
Load → Split → Embed → Store
                ↑       ↑
              M2.2    M2.2
```

### 新增文件

| 文件 | 作用 |
|------|------|
| `app/rag/embeddings.py` | 本地 Embedding 模型（默认 `BAAI/bge-small-zh-v1.5`） |
| `app/rag/store.py` | 切块 → 向量化 → 写入 `data/chroma/` |
| `GET /documents/stats` | 查看向量库总量 |

### 为什么不用 DeepSeek 做 Embedding？

DeepSeek API **只有 Chat**，没有 Embedding 接口。RAG 业界标准做法是：

- **生成（LLM）**：DeepSeek
- **向量化（Embedding）**：本地模型或专用 Embedding API

### 国内下载模型（已内置镜像）

项目启动时会自动设置 `HF_ENDPOINT=https://hf-mirror.com`，**无需手动挂 VPN**。

首次上传 PDF 仍会从镜像站下载约 **100MB** 的 `bge-small-zh` 模型，终端可能停 1～3 分钟，属正常现象。

### 怎么验收

1. 启动：`uv run python main.py`（**首次下载模型请耐心等待 1～3 分钟**）
2. 打开 http://127.0.0.1:8000/docs
3. `POST /documents/upload` 上传 PDF
4. 期望返回新增字段：
   - `indexed_chunks` = 写入向量数
   - `vector_count` = 库中向量总数
   - `embedding_model` = `BAAI/bge-small-zh-v1.5`
5. `GET /documents/stats` → `vector_count` > 0

### 面试 3 题（M2.2）

1. **Embedding 是什么？**  
   把文字变成一串数字（向量），语义相近的文本，向量距离更近。

2. **为什么用 Chroma？**  
   专门存向量、做相似度搜索；比 MySQL 直接搜文字适合「语义检索」。

3. **为什么选 bge-small-zh？**  
   中文文档友好、模型小、本地免费跑，学习阶段够用。

---

## M2.3 检索 + RAG 问答（当前）

**目标**：用户提问 → 检索相关块 → 拼进 prompt → DeepSeek 生成带引用的回答。

```
Load → Split → Embed → Store → Retrieve → Generate
                               ↑          ↑
                             M2.3       M2.3
```

### 新增文件

| 文件 | 作用 |
|------|------|
| `app/rag/retriever.py` | 从 Chroma 做语义检索（`similarity_search`） |
| `app/rag/rag.py` | 拼 prompt + 调 DeepSeek |
| `POST /chat` 增强 | 新增 `use_rag`、`top_k`，返回 `sources` |

### 怎么验收

1. 确认已上传 PDF（`GET /documents/stats` → `vector_count > 0`）
2. `POST /chat`，请求体示例：
   ```json
   {
     "message": "骆健渤做过什么项目？",
     "use_rag": true,
     "top_k": 3
   }
   ```
3. 期望返回：
   - `reply` 提到简历里的项目（如北果南茶、爱心超市）
   - `sources` 有来源文件名和片段
4. 对比：`use_rag: false` 时不会查文档，可能胡编

### 面试 3 题（M2.3）

1. **Retrieve 怎么找相关文档？**  
   把问题 Embedding 成向量，在 Chroma 里找距离最近的 Top-K 块。

2. **为什么要求「仅根据参考文档回答」？**  
   降低幻觉；文档没有的内容应明确说不知道。

3. **`use_rag` 和 M1 的 `/chat` 区别？**  
   M1 直接问 LLM；M2.3 先检索文档再生成，答案有依据。

验收通过后说 **「继续 M3」**，我们做 React 前端。
