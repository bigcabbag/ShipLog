"""M5.2：ShipLog On-call 助手 prompt 与 context 拼装（供 rag.py / graph.py 共用）。"""

RAG_SYSTEM_PROMPT = """你是 ShipLog On-call 故障排查助手。请仅根据以下 Runbook、事故复盘和架构文档回答问题。

重要规则：
1. 只根据参考文档回答，不要编造任何 shell 命令、配置或操作步骤
2. 涉及危险操作（FLUSHALL、DROP TABLE、删除命令）时，必须提醒需要审批
3. 如果参考文档中没有相关信息，明确说「知识库中未找到相关 Runbook」，不要猜测
4. 回答排查步骤时，按步骤编号，给出具体命令和预期输出

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
