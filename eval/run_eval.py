"""M5.2：检索评估，输出 Recall@K / Precision@K / MRR。

用法（项目根目录，需先 import_docs）：
    uv run python eval/run_eval.py
    uv run python eval/run_eval.py --top-k 5
    uv run python eval/run_eval.py --dense-only   # 纯向量对比
    uv run python eval/run_eval.py --rerank       # M6.25：RRF + CrossEncoder
    uv run python eval/run_eval.py --output eval/retrieval_eval_result.md
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVAL_DIR = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(EVAL_DIR) not in sys.path:
    sys.path.insert(0, str(EVAL_DIR))

import app.hf_bootstrap  # noqa: E402, F401

from app.rag.retriever import retrieve
from app.rag.store import get_index_stats
from report_md import format_retrieval_report

QUESTIONS_PATH = Path(__file__).with_name("questions.json")
DEFAULT_OUTPUT = Path(__file__).with_name("retrieval_eval_result.md")


@dataclass
class EvalRow:
    question_id: str
    question: str
    expected_sources: list[str]
    should_abstain: bool
    retrieved_sources: list[str]
    hit: bool
    first_relevant_rank: int | None  # 期望文件在 Top-K 里第一次出现的排名（1-based）


def load_questions() -> list[dict]:
    data = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("questions.json 必须是数组")
    return data


def eval_one(
    item: dict,
    top_k: int,
    *,
    dense_only: bool = False,
    use_rerank: bool = False,
) -> EvalRow:
    qid = str(item["id"])
    question = str(item["question"])
    expected = list(item.get("expected_sources") or [])
    should_abstain = bool(item.get("should_abstain", False))

    docs = retrieve(
        question,
        top_k=top_k,
        hybrid=not dense_only,
        use_rerank=use_rerank,
    )
    retrieved = [str(d.metadata.get("source", "")) for d in docs]

    first_rank: int | None = None
    for i, src in enumerate(retrieved, start=1):
        if src in expected:
            first_rank = i
            break

    if should_abstain:
        hit = len(docs) == 0
    else:
        hit = first_rank is not None

    return EvalRow(
        question_id=qid,
        question=question,
        expected_sources=expected,
        should_abstain=should_abstain,
        retrieved_sources=retrieved,
        hit=hit,
        first_relevant_rank=first_rank,
    )


def calc_metrics(scored: list[EvalRow], top_k: int) -> dict[str, float]:
    """计算 Recall@K / Precision@K / MRR。"""
    total = len(scored)
    if total == 0:
        return {"recall": 0.0, "precision": 0.0, "mrr": 0.0}

    hits = sum(1 for r in scored if r.hit)
    recall = hits / total

    precision_sum = 0.0
    for r in scored:
        if not r.expected_sources:
            continue
        relevant_in_topk = sum(
            1 for src in r.retrieved_sources if src in r.expected_sources
        )
        precision_sum += relevant_in_topk / top_k
    precision = precision_sum / total

    rrr_sum = 0.0
    for r in scored:
        if r.first_relevant_rank:
            rrr_sum += 1.0 / r.first_relevant_rank
    mrr = rrr_sum / total

    return {"recall": recall, "precision": precision, "mrr": mrr}


def main() -> None:
    parser = argparse.ArgumentParser(description="RAG retrieval eval (Recall/Precision/MRR)")
    parser.add_argument("--top-k", type=int, default=3, help="检索 Top-K，默认 3")
    parser.add_argument(
        "--dense-only",
        action="store_true",
        help="仅向量检索（对比纯向量基线）",
    )
    parser.add_argument(
        "--rerank",
        action="store_true",
        help="M6.25：RRF/向量粗排后 CrossEncoder 精排",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Markdown 报告路径（默认 {DEFAULT_OUTPUT.name}）",
    )
    parser.add_argument(
        "--no-file",
        action="store_true",
        help="不写 Markdown 文件，仅控制台输出",
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
        eval_one(
            q,
            top_k=args.top_k,
            dense_only=args.dense_only,
            use_rerank=args.rerank,
        )
        for q in questions
    ]

    if args.dense_only and args.rerank:
        mode = "dense + CrossEncoder rerank"
    elif args.dense_only:
        mode = "dense-only"
    elif args.rerank:
        mode = "hybrid RRF + CrossEncoder rerank"
    else:
        mode = "hybrid (BM25+vector RRF)"

    scored = [r for r in rows if r.expected_sources]
    abstain = [r for r in rows if not r.expected_sources]

    metrics = calc_metrics(scored, args.top_k)

    print(f"=== Retrieval Eval @K={args.top_k} ({mode}) ===")
    print(
        f"vector_count={vector_count}, bm25_count={bm25_count}, "
        f"questions={len(questions)}"
    )
    print(f"scored={len(scored)}, abstain={len(abstain)}")
    print(f"Recall@{args.top_k}    = {metrics['recall']:.1%}")
    print(f"Precision@{args.top_k} = {metrics['precision']:.1%}")
    print(f"MRR@{args.top_k}       = {metrics['mrr']:.3f}")
    print()

    for row in rows:
        mark = "HIT" if row.hit else "MISS"
        kind = "abstain" if row.should_abstain else "scored"
        rank_info = f" rank={row.first_relevant_rank}" if row.first_relevant_rank else ""
        print(f"[{mark}] {row.question_id} ({kind}){rank_info}")
        print(f"  Q: {row.question}")
        print(f"  expected: {row.expected_sources or '(none)'}")
        print(f"  retrieved: {row.retrieved_sources}")
        print()

    abstain_stats = None
    if abstain:
        abstain_empty = sum(1 for r in abstain if r.hit)
        abstain_stats = {
            "total": len(abstain),
            "empty_retrieve": abstain_empty,
        }
        print(
            f"abstain_set: {len(abstain)} questions, "
            f"empty_retrieve={abstain_empty} (检索层仅参考，生成拒答看 CRAG)"
        )

    if not args.no_file:
        suffix_parts: list[str] = []
        if args.dense_only:
            suffix_parts.append("dense")
        if args.rerank:
            suffix_parts.append("rerank")
        suffix = ("_" + "_".join(suffix_parts)) if suffix_parts else ""
        output = args.output
        if output == DEFAULT_OUTPUT and suffix:
            output = DEFAULT_OUTPUT.with_name(f"retrieval_eval_result{suffix}.md")
        output.parent.mkdir(parents=True, exist_ok=True)
        md = format_retrieval_report(
            top_k=args.top_k,
            mode=mode,
            vector_count=vector_count,
            bm25_count=bm25_count,
            question_count=len(questions),
            scored_count=len(scored),
            abstain_count=len(abstain),
            metrics=metrics,
            rows=rows,
            abstain_stats=abstain_stats,
        )
        output.write_text(md, encoding="utf-8")
        print(f"\nMarkdown 报告已写入: {output}")


if __name__ == "__main__":
    main()
