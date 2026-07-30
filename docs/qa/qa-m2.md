# M2 面试问答卡：RAG 基础链路

## 1. RAG 完整六步是什么？

Load → Split → Embed → Store → Retrieve → Generate

- **Load/Split**：`loader.py` 读 PDF 切块
- **Embed/Store**：`embeddings.py` + `store.py` 写入 Chroma
- **Retrieve/Generate**：`retriever.py` + `rag.py` 检索后调 DeepSeek

## 2. Retrieve 和 Generate 分别干什么？

- **Retrieve**：把用户问题变向量，从 Chroma 找 Top-K 最相似文档块
- **Generate**：把检索到的块拼进 system prompt，让 LLM 基于文档回答

## 3. 为什么要把文档块放进 system prompt？

LLM 本身不知道你上传了什么。RAG 把「相关证据」塞进 prompt，让模型**有据可依**，减少胡编。

## 4. `top_k` 是什么？设太大/太小会怎样？

检索返回的文档块数量。

- 太小：可能漏掉关键信息
- 太大：prompt 变长、成本上升、无关内容干扰回答

## 5. `sources` 字段有什么用？

告诉用户答案依据来自哪个文件、哪一页，方便核对，也是面试常问的 **citation（引用）** 能力。

## 6. Embedding 和 LLM 为什么分开？

DeepSeek 只有 Chat API，没有 Embedding。业界常见组合是：**专用/本地 Embedding 模型 + 通用 LLM**。

## 自检（能流利回答再进 M3）

- [ ] 上传 PDF 后，问「做过什么项目」，数据流经哪几个文件？
- [ ] `use_rag: false` 时 `/chat` 和 M1 有什么区别？
- [ ] 如果 Chroma 是空的，`/chat` 会返回什么？
