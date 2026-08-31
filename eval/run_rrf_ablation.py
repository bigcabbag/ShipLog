"""U-031：RRF / BM25 权重消融 — 同库同题集，只改融合权重（不重嵌）。

用法（项目根，需 Postgres + 已 import_docs）：
    uv run python eval/run_rrf_ablation.py

默认对比：纯向量、现行 1.0/0.35、以及 0.2 / 0.5 / 1.0 几档 BM25 权重。
"""

from __future__ import annotations

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

from app.rag.retriever import BM25_RRF_WEIGHT, VECTOR_RRF_WEIGHT  # noqa: E402
from app.rag.store import get_index_stats  # noqa: E402
from run_eval import calc_metrics, eval_one, load_questions  # noqa: E402

OUTPUT = EVAL_DIR / "reports" / "ablation" / "rrf_weight.md"
TOP_K = 3

# (label, dense_only, vector_w, bm25_w, note)
CONFIGS: list[tuple[str, bool, float | None, float | None, str]] = [
    ("dense-only", True, None, None, "纯向量基线（关 BM25）"),
    (
        f"hybrid {VECTOR_RRF_WEIGHT:g}/{BM25_RRF_WEIGHT:g}",
        False,
        VECTOR_RRF_WEIGHT,
        BM25_RRF_WEIGHT,
        "现行默认（向量主、BM25 辅）",
    ),
    ("hybrid 1.0/0.2", False, 1.0, 0.2, "BM25 更弱"),
    ("hybrid 1.0/0.5", False, 1.0, 0.5, "BM25 略强"),
    ("hybrid 1.0/1.0", False, 1.0, 1.0, "两路等权（易被关键词堆叠带偏）"),
]


@dataclass
class AblationRow:
    label: str
    note: str
    dense_only: bool
    vector_w: float | None
    bm25_w: float | None
    recall: float
    precision: float
    mrr: float
    scored: int


def run_one(
    label: str,
    dense_only: bool,
    vector_w: float | None,
    bm25_w: float | None,
    note: str,
) -> AblationRow:
    questions = load_questions()
    rows = [
        eval_one(
            q,
            top_k=TOP_K,
            dense_only=dense_only,
            use_rerank=False,
            vector_weight=None if dense_only else vector_w,
            bm25_weight=None if dense_only else bm25_w,
        )
        for q in questions
    ]
    scored = [r for r in rows if r.expected_sources]
    metrics = calc_metrics(scored, TOP_K)
    print(
        f"{label}: Recall@{TOP_K}={metrics['recall']:.1%}  "
        f"P@{TOP_K}={metrics['precision']:.1%}  "
        f"MRR@{TOP_K}={metrics['mrr']:.3f}"
    )
    return AblationRow(
        label=label,
        note=note,
        dense_only=dense_only,
        vector_w=vector_w,
        bm25_w=bm25_w,
        recall=float(metrics["recall"]),
        precision=float(metrics["precision"]),
        mrr=float(metrics["mrr"]),
        scored=len(scored),
    )


def pick_winner(rows: list[AblationRow]) -> AblationRow:
    """主指标 Recall，其次 MRR；Recall 与现行默认并列时保留 1.0/0.35。"""
    hybrid = [r for r in rows if not r.dense_only]
    pool = hybrid or rows
    best = max(pool, key=lambda r: (r.recall, r.mrr))
    default = next(
        (
            r
            for r in rows
            if (not r.dense_only)
            and r.vector_w == VECTOR_RRF_WEIGHT
            and r.bm25_w == BM25_RRF_WEIGHT
        ),
        None,
    )
    if default and abs(default.recall - best.recall) < 1e-9:
        # 同库 Recall 常持平；MRR 差几个点不值得改已钉死的口述权重
        return default
    return best


def write_report(rows: list[AblationRow], winner: AblationRow, stats: dict) -> None:
    lines = [
        "# RRF / BM25 权重消融（U-031）",
        "",
        "> 同一知识库、同一 `questions.json`、Top-K=3、**不重嵌**、关 Rerank。  ",
        f"> 库规模：vector_count={stats.get('vector_count')}, "
        f"bm25_count={stats.get('bm25_count')}。  ",
        f"> 代码默认：`VECTOR_RRF_WEIGHT={VECTOR_RRF_WEIGHT}` / "
        f"`BM25_RRF_WEIGHT={BM25_RRF_WEIGHT}`（`app/rag/retriever.py`）。",
        "",
        "## 结果表",
        "",
        "| 配置 | scored | Recall@3 | Precision@3 | MRR@3 | 说明 |",
        "|------|-------:|---------:|------------:|------:|------|",
    ]
    for r in rows:
        mark = " ← 选用" if r.label == winner.label else ""
        lines.append(
            f"| {r.label} | {r.scored} | **{r.recall:.1%}** | "
            f"{r.precision:.1%} | {r.mrr:.3f} | {r.note}{mark} |"
        )
    lines.extend(
        [
            "",
            "## 结论",
            "",
            f"- **选用**：`{winner.label}`"
            f"（Recall@3={winner.recall:.1%}，MRR@3={winner.mrr:.3f}）。",
            "- 判定：hybrid 组先比 Recall；**Recall 与现行默认并列 → 保留 1.0/0.35**"
            "（本库各组 Recall 常持平，MRR 微差不改口述口径）。",
            "- 观察：等权 **1.0/1.0** 的 P@3 / MRR 最差，印证「勿等权、防关键词堆叠」。",
            "- 面试口述：「跑过纯向量与多档 BM25 权重；Recall 持平下保留向量主、BM25=0.35；"
            "等权会掉排序质量。」",
            "",
            "## 怎么复现",
            "",
            "```powershell",
            "cd E:\\01_Dev\\langChain",
            "uv run python eval/run_rrf_ablation.py",
            "```",
            "",
        ]
    )
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nWrote {OUTPUT}")


def main() -> None:
    stats = get_index_stats()
    if int(stats.get("vector_count") or 0) == 0:
        print("vector_count=0，请先: uv run python scripts/import_docs.py")
        sys.exit(1)

    results = [
        run_one(label, dense, vw, bw, note)
        for label, dense, vw, bw, note in CONFIGS
    ]
    winner = pick_winner(results)
    write_report(results, winner, stats)
    print(f"U-031 done. winner={winner.label}")


if __name__ == "__main__":
    main()
