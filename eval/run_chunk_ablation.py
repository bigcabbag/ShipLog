"""U-012：Chunk size/overlap 消融 — 多组入库 + 检索 eval，写出对照表。

用法（项目根，需 Postgres + .env；不调聊天 LLM，只耗 embedding）：
    uv run python eval/run_chunk_ablation.py

默认三组：300/30、500/50（现行）、800/80；跑完后按最优（并列取现行 500/50）恢复入库。
"""

from __future__ import annotations

import subprocess
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

from app.rag.loader import DEFAULT_CHUNK_OVERLAP, DEFAULT_CHUNK_SIZE  # noqa: E402
from app.rag.store import get_index_stats  # noqa: E402
from run_eval import calc_metrics, eval_one, load_questions  # noqa: E402

OUTPUT = EVAL_DIR / "chunk_ablation.md"
PY = sys.executable

CONFIGS: list[tuple[int, int, str]] = [
    (300, 30, "更碎：步骤不易被切断，噪声块可能增多"),
    (500, 50, "现行默认（loader.py）"),
    (800, 80, "更大块：上下文更完整，语义可能稀释"),
]


@dataclass
class AblationRow:
    chunk_size: int
    chunk_overlap: int
    note: str
    vector_count: int
    recall: float
    precision: float
    mrr: float
    scored: int


def _import_kb(size: int, overlap: int) -> None:
    cmd = [
        PY,
        str(ROOT / "scripts" / "import_docs.py"),
        "--chunk-size",
        str(size),
        "--chunk-overlap",
        str(overlap),
        "--clear",
    ]
    print(f"\n======== import {size}/{overlap} ========")
    subprocess.run(cmd, cwd=str(ROOT), check=True)


def run_one(size: int, overlap: int, note: str) -> AblationRow:
    _import_kb(size, overlap)
    stats = get_index_stats()
    questions = load_questions()
    rows = [eval_one(q, top_k=3, dense_only=False, use_rerank=False) for q in questions]
    scored = [r for r in rows if r.expected_sources]
    metrics = calc_metrics(scored, 3)
    print(
        f"Recall@3={metrics['recall']:.1%}  "
        f"Precision@3={metrics['precision']:.1%}  "
        f"MRR@3={metrics['mrr']:.3f}  "
        f"vector_count={stats['vector_count']}"
    )
    return AblationRow(
        chunk_size=size,
        chunk_overlap=overlap,
        note=note,
        vector_count=int(stats["vector_count"]),
        recall=float(metrics["recall"]),
        precision=float(metrics["precision"]),
        mrr=float(metrics["mrr"]),
        scored=len(scored),
    )


def pick_winner(rows: list[AblationRow]) -> AblationRow:
    """主指标 Recall，其次 MRR；并列优先现行 500/50。"""
    best = max(rows, key=lambda r: (r.recall, r.mrr))
    default = next(
        (r for r in rows if r.chunk_size == 500 and r.chunk_overlap == 50), None
    )
    if default and abs(default.recall - best.recall) < 1e-9:
        if default.mrr + 1e-9 >= best.mrr:
            return default
    return best


def write_report(rows: list[AblationRow], winner: AblationRow) -> None:
    lines = [
        "# Chunk 消融实验（U-012）",
        "",
        "> 同一知识库 `docs/kb/`、同一 `questions.json`、混合检索 RRF、Top-K=3。  ",
        "> **不调聊天 LLM**；每组 `--clear` 后全量重嵌。  ",
        f"> 现行默认：`{DEFAULT_CHUNK_SIZE}/{DEFAULT_CHUNK_OVERLAP}`（`app/rag/loader.py`）。",
        "",
        "## 结果表",
        "",
        "| chunk_size | overlap | vector_count | scored 题 | Recall@3 | Precision@3 | MRR@3 | 说明 |",
        "|-----------:|--------:|-------------:|----------:|---------:|------------:|------:|------|",
    ]
    for r in rows:
        mark = " ← 选用" if (
            r.chunk_size == winner.chunk_size and r.chunk_overlap == winner.chunk_overlap
        ) else ""
        lines.append(
            f"| {r.chunk_size} | {r.chunk_overlap} | {r.vector_count} | {r.scored} | "
            f"**{r.recall:.1%}** | {r.precision:.1%} | {r.mrr:.3f} | {r.note}{mark} |"
        )
    lines.extend(
        [
            "",
            "## 结论",
            "",
            f"- **选用**：`{winner.chunk_size}/{winner.chunk_overlap}`"
            f"（Recall@3={winner.recall:.1%}，MRR@3={winner.mrr:.3f}）。",
            "- 判定：先比 Recall，再比 MRR；Recall 并列时优先保留现行 **500/50**（少改生产默认）。",
            "- 面试口述：「做过 300/500/800 三组消融，按 Recall@3 / MRR 选最终切块。」",
            "",
            "## 怎么复现",
            "",
            "```powershell",
            "cd E:\\01_Dev\\langChain",
            "uv run python eval/run_chunk_ablation.py",
            "```",
            "",
        ]
    )
    OUTPUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nWrote {OUTPUT}")


def main() -> None:
    results: list[AblationRow] = []
    for size, overlap, note in CONFIGS:
        results.append(run_one(size, overlap, note))

    winner = pick_winner(results)
    write_report(results, winner)

    print(f"\n======== restore winner {winner.chunk_size}/{winner.chunk_overlap} ========")
    _import_kb(winner.chunk_size, winner.chunk_overlap)
    # 若赢家不是默认，写进报告即可；默认常量仍以 loader 为准，赢家非 500 时需改 loader
    if (winner.chunk_size, winner.chunk_overlap) != (
        DEFAULT_CHUNK_SIZE,
        DEFAULT_CHUNK_OVERLAP,
    ):
        print(
            f"NOTE: winner differs from loader default "
            f"{DEFAULT_CHUNK_SIZE}/{DEFAULT_CHUNK_OVERLAP}; "
            "update loader.py if you want code default to match."
        )
    print("U-012 done.")


if __name__ == "__main__":
    main()
