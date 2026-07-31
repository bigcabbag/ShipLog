"""eval 脚本共用的 Markdown 报告格式化。"""

from __future__ import annotations

from typing import Any, Protocol, Sequence


class GenRow(Protocol):
    question_id: str
    question: str
    answer: str
    abstained: bool
    hallucinated: bool


class RetrievalRow(Protocol):
    question_id: str
    question: str
    expected_sources: list[str]
    should_abstain: bool
    retrieved_sources: list[str]
    hit: bool
    first_relevant_rank: int | None


def _gen_mark(row: GenRow) -> tuple[str, str]:
    if row.abstained:
        return "ABSTAIN", "⛔"
    if row.hallucinated:
        return "HALLU", "⚠️"
    return "OK", "✅"


def format_gen_report(
    *,
    question_count: int,
    experiments: Sequence[tuple[str, Sequence[GenRow], dict[str, float]]],
) -> str:
    lines: list[str] = [f"# Generation Eval (questions={question_count})", ""]

    for label, rows, metrics in experiments:
        lines.append(f"## {label}")
        lines.append("")
        for row in rows:
            tag, icon = _gen_mark(row)
            lines.append(f"### {icon} [{tag}] {row.question_id}: {row.question}")
            lines.append("")
            lines.append("**回答：**")
            lines.append("")
            lines.append(row.answer.strip())
            lines.append("")
        lines.append(
            f"> **指标**：abstain_accuracy={metrics['abstain_accuracy']:.1%}  "
            f"false_abstain={metrics['false_abstain_rate']:.1%}  "
            f"hallucination={metrics['hallucination_rate']:.1%}"
        )
        lines.append("")

    lines.append("# Summary")
    lines.append("")
    lines.append("| 实验 | 拒答准确率 | 误拒答率 | 幻觉率 |")
    lines.append("| --- | ---: | ---: | ---: |")
    for label, _, metrics in experiments:
        lines.append(
            f"| {label} | {metrics['abstain_accuracy']:.1%} | "
            f"{metrics['false_abstain_rate']:.1%} | "
            f"{metrics['hallucination_rate']:.1%} |"
        )
    lines.append("")
    return "\n".join(lines)


def format_retrieval_report(
    *,
    top_k: int,
    mode: str,
    vector_count: int,
    bm25_count: int,
    question_count: int,
    scored_count: int,
    abstain_count: int,
    metrics: dict[str, float],
    rows: Sequence[RetrievalRow],
    abstain_stats: dict[str, Any] | None = None,
) -> str:
    lines: list[str] = [
        f"# Retrieval Eval @K={top_k} ({mode})",
        "",
        f"- vector_count={vector_count}, bm25_count={bm25_count}, questions={question_count}",
        f"- scored={scored_count}, abstain={abstain_count}",
        "",
        "## 指标",
        "",
        f"| 指标 | 值 |",
        f"| --- | ---: |",
        f"| Recall@{top_k} | {metrics['recall']:.1%} |",
        f"| Precision@{top_k} | {metrics['precision']:.1%} |",
        f"| MRR@{top_k} | {metrics['mrr']:.3f} |",
        "",
        "## 逐题明细",
        "",
    ]

    for row in rows:
        mark = "HIT" if row.hit else "MISS"
        icon = "✅" if row.hit else "❌"
        kind = "abstain" if row.should_abstain else "scored"
        rank_info = (
            f"（rank={row.first_relevant_rank}）" if row.first_relevant_rank else ""
        )
        lines.append(
            f"### {icon} [{mark}] {row.question_id} ({kind}){rank_info}"
        )
        lines.append("")
        lines.append(f"**问题：** {row.question}")
        lines.append("")
        expected = row.expected_sources or ["(none)"]
        lines.append(f"**期望：** {', '.join(expected)}")
        lines.append("")
        lines.append(f"**检索：** {', '.join(row.retrieved_sources) or '(empty)'}")
        lines.append("")

    if abstain_stats:
        lines.append("## abstain 集")
        lines.append("")
        lines.append(
            f"- 共 {abstain_stats['total']} 题，空检索 {abstain_stats['empty_retrieve']} 题"
        )
        lines.append(
            "- 检索层仅参考；生成层拒答看 CRAG / prompt"
        )
        lines.append("")

    return "\n".join(lines)
