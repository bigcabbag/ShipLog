"""M4.1：跑检索评估，输出 Recall@K。

用法（项目根目录，需先 import_docs）：
    uv run python eval/run_eval.py
    uv run python eval/run_eval.py --top-k 5
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.rag.retriever import retrieve
from app.rag.store import get_index_stats

QUESTIONS_PATH = Path(__file__).with_name("questions.json")


@dataclass
class EvalRow:
    question_id: str
    question: str
    expected_sources: list[str]
    should_abstain: bool
    retrieved_sources: list[str]
    hit: bool


def load_questions() -> list[dict]:
    data = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("questions.json 必须是数组")
    return data


def eval_one(item: dict, top_k: int, *, dense_only: bool = False) -> EvalRow:
    qid = str(item["id"])
    question = str(item["question"])
    expected = list(item.get("expected_sources") or [])
    should_abstain = bool(item.get("should_abstain", False))

    docs = retrieve(question, top_k=top_k, hybrid=not dense_only)
    retrieved = [str(d.metadata.get("source", "")) for d in docs]

    if should_abstain:
        # 拒答集：Top-K 不应命中「瞎编的业务文档」；此处仅报告检索到了什么
        hit = len(docs) == 0
    else:
        hit = any(src in retrieved for src in expected)

    return EvalRow(
        question_id=qid,
        question=question,
        expected_sources=expected,
        should_abstain=should_abstain,
        retrieved_sources=retrieved,
        hit=hit,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="RAG retrieval Recall@K eval")
    parser.add_argument("--top-k", type=int, default=3, help="检索 Top-K，默认 3")
    parser.add_argument(
        "--dense-only",
        action="store_true",
        help="仅向量检索（对比 M4.1 基线）",
    )
    args = parser.parse_args()

    stats = get_index_stats()
    vector_count = int(stats["vector_count"])
    if vector_count == 0:
        print("vector_count=0，请先运行: uv run python scripts/import_docs.py")
        sys.exit(1)

    bm25_count = int(stats.get("bm25_count", 0))
    if bm25_count == 0 and not args.dense_only:
        print("bm25_count=0，请先运行: uv run python scripts/import_docs.py")
        sys.exit(1)

    questions = load_questions()
    rows = [
        eval_one(q, top_k=args.top_k, dense_only=args.dense_only) for q in questions
    ]

    mode = "dense-only" if args.dense_only else "hybrid (BM25+vector RRF)"

    scored = [r for r in rows if not r.should_abstain]
    abstain = [r for r in rows if r.should_abstain]

    hits = sum(1 for r in scored if r.hit)
    total = len(scored)
    recall = hits / total if total else 0.0

    print(f"=== Recall@{args.top_k} ({mode}) ===")
    print(
        f"vector_count={vector_count}, bm25_count={bm25_count}, "
        f"questions={len(questions)}"
    )
    print(f"scored={total}, hits={hits}, recall={recall:.1%}")
    print()

    for row in rows:
        mark = "HIT" if row.hit else "MISS"
        kind = "abstain" if row.should_abstain else "scored"
        print(f"[{mark}] {row.question_id} ({kind})")
        print(f"  Q: {row.question}")
        print(f"  expected: {row.expected_sources or '(none)'}")
        print(f"  retrieved: {row.retrieved_sources}")
        print()

    if abstain:
        abstain_hits = sum(1 for r in abstain if r.hit)
        print(
            f"abstain_set: {len(abstain)} questions, "
            f"empty_retrieve={abstain_hits} (检索层仅参考，生成拒答看 M4.2+)"
        )


if __name__ == "__main__":
    main()
