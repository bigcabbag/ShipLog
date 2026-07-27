"""RAG  prompt 与 context 拼装（供 rag.py / graph.py 共用）。"""

RAG_SYSTEM_PROMPT = """你是一个企业知识库助手。请仅根据以下参考文档回答问题。
如果参考文档中没有相关信息，请明确说「文档中未找到相关信息」，不要编造。

参考文档：
{context}"""


def build_context(docs: list) -> tuple[str, list[dict]]:
    parts: list[str] = []
    sources: list[dict] = []

    for i, doc in enumerate(docs, start=1):
        source = str(doc.metadata.get("source", "未知"))
        page = doc.metadata.get("page", "?")
        parts.append(f"[{i}] 来源: {source} 第{page}页\n{doc.page_content}")
        sources.append(
            {
                "source": source,
                "page": page,
                "content": doc.page_content[:200],
            }
        )

    return "\n\n".join(parts), sources
