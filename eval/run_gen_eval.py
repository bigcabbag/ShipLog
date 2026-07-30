"""M5.2：生成层评估——对比无 CRAG vs 有 CRAG，通用 prompt vs On-call prompt。

输出指标：
- 拒答准确率（abstain 题是否正确拒答）
- 误拒答率（不该拒答却拒答）
- 幻觉率（回答是否包含编造命令/步骤，用 LLM 评估）

用法（项目根目录，需先 import_docs + .env 有 DEEPSEEK_API_KEY）：
    uv run python eval/run_gen_eval.py
    uv run python eval/run_gen_eval.py --output eval/gen_eval_result_v6.md
    uv run python eval/run_gen_eval.py --limit 5
"""

from __future__ import annotations

import asyncio
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVAL_DIR = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(EVAL_DIR) not in sys.path:
    sys.path.insert(0, str(EVAL_DIR))

from app.llm import chat
from app.rag.context import RAG_SYSTEM_PROMPT, build_context
from app.rag.retriever import retrieve
from app.rag.store import get_index_stats
from report_md import format_gen_report

QUESTIONS_PATH = Path(__file__).with_name("questions.json")
DEFAULT_OUTPUT = Path(__file__).with_name("gen_eval_result.md")

GENERIC_PROMPT = """你是一个知识库助手。请根据以下参考文档回答问题。
如果参考文档中没有相关信息，请说「未找到相关信息」。

参考文档：
{context}"""

ONCALL_PROMPT = RAG_SYSTEM_PROMPT

HALLUCINATION_EVAL_PROMPT = """你是严格的幻觉检测评估员。请**逐条**检查以下回答中的每个具体命令、配置项、操作步骤，判断是否在参考文档中有对应。

用户问题：{question}

参考文档（知识库内容）：
{context}

AI 回答：
{answer}

检查规则：
1. 逐条列出回答中的每个具体 shell 命令、kubectl 命令、配置项、操作步骤
2. 对每条标注是否在参考文档中找到对应（YES/NO）
3. 如果回答只是换了说法组织文档已有内容（如加编号、加粗体、归纳总结）→ 标注 YES
4. 如果回答中的某条命令/步骤在文档中找不到对应 → 标注 NO
5. 正确拒答（说「未找到」「无法回答」等）→ 无需检查，直接 NOT_HALLUCINATED

判断标准：**有任何一条标注为 NO → HALLUCINATED；全部 YES → NOT_HALLUCINATED**

请先逐条列出检查结果，然后在最后一行输出总体判断：HALLUCINATED 或 NOT_HALLUCINATED。"""


@dataclass
class GenEvalRow:
    question_id: str
    question: str
    should_abstain: bool
    answer: str
    abstained: bool
    correct_abstain: bool
    hallucinated: bool = False
    sources: list[str] = field(default_factory=list)


def load_questions() -> list[dict]:
    data = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("questions.json 必须是数组")
    return data


def _is_abstain(answer: str) -> bool:
    keywords = ["未找到", "无法回答", "未找到相关", "知识库中暂无", "建议查阅", "请联系"]
    return any(kw in answer for kw in keywords)


async def _generate_no_crag(
    question: str, prompt_template: str
) -> tuple[str, list[str], str]:
    """返回 (answer, sources, context_used)。"""
    docs = retrieve(question, top_k=3, hybrid=True)
    if not docs:
        return "知识库中未找到相关文档。", [], ""
    context, sources = build_context(docs)
    prompt = prompt_template.format(context=context)
    answer = await chat(question, system_prompt=prompt)
    return answer, [s.get("source", "") for s in sources], context


async def _generate_with_crag(
    question: str,
) -> tuple[str, list[str], str]:
    """返回 (answer, sources, context_used)。CRAG 用改写后查询检索的文档作为 context。"""
    from app.rag.graph import run_crag_prepare

    rag_prompt, sources, early_reply, _ = await run_crag_prepare(
        question, top_k=3, system_prompt=None
    )
    if early_reply is not None:
        return early_reply, [], ""
    answer = await chat(question, system_prompt=rag_prompt or "")
    context_used = (
        rag_prompt.split("参考文档：\n", 1)[-1]
        if rag_prompt and "参考文档：" in rag_prompt
        else ""
    )
    return answer, [s.get("source", "") for s in sources], context_used


async def _eval_hallucination(question: str, answer: str, context: str) -> bool:
    """用 temperature=0 的 LLM 做幻觉评估，减少随机性。"""
    from langchain_core.messages import HumanMessage
    from langchain_openai import ChatOpenAI
    from pydantic import SecretStr

    from app.config import get_settings

    settings = get_settings()
    eval_llm = ChatOpenAI(
        model=settings["model"],
        api_key=SecretStr(settings["api_key"]),
        base_url=settings["base_url"],
        temperature=0,
    )
    prompt = HALLUCINATION_EVAL_PROMPT.format(
        question=question, context=context, answer=answer
    )
    response = await eval_llm.ainvoke([HumanMessage(content=prompt)])
    result = (
        response.content if isinstance(response.content, str) else str(response.content)
    )
    last_line = result.strip().split("\n")[-1].strip().upper()
    return "HALLUCINATED" in last_line and "NOT" not in last_line


async def run_experiment(
    questions: list[dict],
    mode: str,
    prompt_template: str,
) -> list[GenEvalRow]:
    rows: list[GenEvalRow] = []
    for item in questions:
        qid = str(item["id"])
        question = str(item["question"])
        should_abstain = bool(item.get("should_abstain", False))
        if mode == "no_crag":
            answer, sources, context_used = await _generate_no_crag(
                question, prompt_template
            )
        else:
            answer, sources, context_used = await _generate_with_crag(question)
        abstained = _is_abstain(answer)
        correct = should_abstain and abstained
        hallucinated = False
        if not abstained:
            if not context_used:
                docs = retrieve(question, top_k=3, hybrid=True)
                context_used, _ = build_context(docs) if docs else ("（空）", [])
            hallucinated = await _eval_hallucination(question, answer, context_used)
        rows.append(
            GenEvalRow(
                question_id=qid,
                question=question,
                should_abstain=should_abstain,
                answer=answer,
                abstained=abstained,
                correct_abstain=correct,
                hallucinated=hallucinated,
                sources=sources,
            )
        )
        mark = "ABSTAIN" if abstained else ("HALLU" if hallucinated else "OK")
        print(f"  [{mark}] {qid}: {question[:40]}...")
    return rows


def calc_gen_metrics(rows: list[GenEvalRow]) -> dict[str, float]:
    abstain_rows = [r for r in rows if r.should_abstain]
    answer_rows = [r for r in rows if not r.should_abstain]
    abstain_accuracy = 0.0
    if abstain_rows:
        correct = sum(1 for r in abstain_rows if r.correct_abstain)
        abstain_accuracy = correct / len(abstain_rows)
    false_abstain_rate = 0.0
    if answer_rows:
        false_abstain = sum(1 for r in answer_rows if r.abstained)
        false_abstain_rate = false_abstain / len(answer_rows)
    hallucination_rate = 0.0
    non_abstain = [r for r in answer_rows if not r.abstained]
    if non_abstain:
        hallu = sum(1 for r in non_abstain if r.hallucinated)
        hallucination_rate = hallu / len(non_abstain)
    return {
        "abstain_accuracy": abstain_accuracy,
        "false_abstain_rate": false_abstain_rate,
        "hallucination_rate": hallucination_rate,
    }


def print_summary(results: dict[str, dict[str, float]]) -> None:
    print("\n=== Summary ===")
    print(f"{'实验':<32} {'拒答准确率':>10} {'误拒答率':>10} {'幻觉率':>10}")
    for label, m in results.items():
        print(
            f"{label:<32} {m['abstain_accuracy']:>10.1%} "
            f"{m['false_abstain_rate']:>10.1%} {m['hallucination_rate']:>10.1%}"
        )


async def main_async(*, limit: int, output: Path | None) -> None:
    stats = get_index_stats()
    if int(stats["vector_count"]) == 0:
        print("vector_count=0，请先运行: uv run python scripts/import_docs.py")
        sys.exit(1)
    questions = load_questions()
    if limit > 0:
        questions = questions[:limit]
    print(f"=== Generation Eval (questions={len(questions)}) ===\n")

    experiments_cfg = [
        ("no_crag + generic_prompt", "no_crag", GENERIC_PROMPT),
        ("no_crag + oncall_prompt", "no_crag", ONCALL_PROMPT),
        ("with_crag + oncall_prompt", "with_crag", ONCALL_PROMPT),
    ]
    results: dict[str, dict[str, float]] = {}
    report_experiments: list[tuple[str, list[GenEvalRow], dict[str, float]]] = []

    for label, mode, prompt in experiments_cfg:
        print(f"--- {label} ---")
        rows = await run_experiment(questions, mode, prompt)
        metrics = calc_gen_metrics(rows)
        results[label] = metrics
        report_experiments.append((label, rows, metrics))
        print(
            f"  abstain_accuracy={metrics['abstain_accuracy']:.1%}  "
            f"false_abstain={metrics['false_abstain_rate']:.1%}  "
            f"hallucination={metrics['hallucination_rate']:.1%}\n"
        )

    print_summary(results)

    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        md = format_gen_report(
            question_count=len(questions),
            experiments=report_experiments,
        )
        output.write_text(md, encoding="utf-8")
        print(f"\nMarkdown 报告已写入: {output}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0, help="只跑前 N 题（0=全部）")
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Markdown 报告路径（默认 {DEFAULT_OUTPUT.name}）",
    )
    parser.add_argument(
        "--no-file",
        action="store_true",
        help="不写 Markdown 文件，仅控制台输出摘要",
    )
    args = parser.parse_args()
    asyncio.run(
        main_async(
            limit=args.limit,
            output=None if args.no_file else args.output,
        )
    )
