# RAG 检索评估基线（Recall@K）

> 只评 **Retrieve 层**（`retriever.retrieve`），不调 LLM。  
> 跑之前必须先索引文档：`uv run python scripts/import_docs.py`

## 怎么跑

```powershell
cd E:\01_Dev\langChain
uv run python eval/run_eval.py
# 可选：--top-k 5
```

网络不好、模型已缓存时（避免 HuggingFace 超时）：

```powershell
$env:HF_HUB_OFFLINE="1"
uv run python eval/run_eval.py
```

## 指标含义

**Recall@3**：18 道「有标答文档」题里，Top-3 检索结果的 `metadata.source` 是否包含 **任一** `expected_sources` 文件名。

- **Hit**：例如期望 `M3-steps.md`，Top-3 里出现了 `M3-steps.md`
- **Miss**：Top-3 都没出现期望文件
- **should_abstain**：2 题不参与 Recall 分子；检索层仅记录（生成拒答在 M4.2+）

## 基线记录

| 阶段 | Top-K | Recall | 说明 | 日期 |
|------|-------|--------|------|------|
| M4.1 纯向量（import_docs 后） | 3 | **94.4%** (17/18) | vector_count=128 | 2026-07-21 |
| M4.3 混合检索 RRF 后 | 3 | **94.4%** (17/18) | BM25+向量加权 RRF，与 M4.1 持平；精确词排序更稳 | 2026-07-21 |

### M4.1 已知 Miss

| id | 问题 | 期望 | 实际 Top-3 | 可能原因 |
|----|------|------|------------|----------|
| q10 | M4.2 LangGraph CRAG 要做什么？ | M4-steps.md | PLAN.md ×3 | PLAN 也含 M4 摘要，语义更近 |

### abstain 集（仅参考）

| id | 问题 | 说明 |
|----|------|------|
| q19 | 骆健渤月薪 | 检索仍命中旧 PDF/无关 chunk；M4.2 拒答 + 清库可改善 |
| q20 | 公司年假 | 误命中 PLAN.md；需 generate 层拒答 |

## 面试怎么说

> 自建 20 题 eval，标注期望来源文件；脚本 `eval/run_eval.py` 跑 Recall@3。  
> M4.1 纯向量基线 **94.4%**；Miss 主要是 M4 摘要在 PLAN 与 M4-steps 间混淆；M4.3 混合检索后复测并对比此表。
