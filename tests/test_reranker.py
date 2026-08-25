"""M6.25：Reranker 单测（mock CrossEncoder，不下载模型）。"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from langchain_core.documents import Document

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.rag.reranker import rerank_documents  # noqa: E402


class TestRerankDocuments(unittest.TestCase):
    def test_orders_by_score_desc(self) -> None:
        docs = [
            Document(page_content="无关内容", metadata={"source": "a.md"}),
            Document(page_content="Redis 超时排查步骤", metadata={"source": "redis.md"}),
            Document(page_content="Pod OOM", metadata={"source": "oom.md"}),
        ]
        mock = MagicMock()
        mock.predict.return_value = [0.1, 0.9, 0.3]

        out = rerank_documents("Redis 超时怎么办", docs, top_k=2, model=mock)

        self.assertEqual(len(out), 2)
        self.assertEqual(out[0].metadata["source"], "redis.md")
        self.assertEqual(out[1].metadata["source"], "oom.md")
        mock.predict.assert_called_once()
        pairs = mock.predict.call_args[0][0]
        self.assertEqual(pairs[0], ["Redis 超时怎么办", "无关内容"])

    def test_rerank_fail_open_on_predict_error(self) -> None:
        docs = [
            Document(page_content="a", metadata={"source": "a.md"}),
            Document(page_content="b", metadata={"source": "b.md"}),
        ]
        mock = MagicMock()
        mock.predict.side_effect = RuntimeError("cuda oom")

        out = rerank_documents("q", docs, top_k=1, model=mock)

        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].metadata["source"], "a.md")

    def test_empty_docs(self) -> None:
        self.assertEqual(rerank_documents("q", [], top_k=3), [])


if __name__ == "__main__":
    unittest.main()
