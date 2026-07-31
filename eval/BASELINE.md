# RAG 评估基线（检索层 + 生成层）

> **检索层** `eval/run_eval.py`：只评 Retrieve（不调 LLM），输出 Recall@K / Precision@K / MRR。  
> **生成层** `eval/run_gen_eval.py`：调 LLM 对比无 CRAG vs 有 CRAG、通用 prompt vs On-call prompt，输出拒答准确率 / 误拒答率 / 幻觉率。  
> 跑之前必须先索引文档：`uv run python scripts/import_docs.py`

## 怎么跑

```powershell
cd E:\01_Dev\langChain
# 检索层
uv run python eval/run_eval.py              # 混合检索 → eval/retrieval_eval_result.md
uv run python eval/run_eval.py --dense-only # 纯向量 → eval/retrieval_eval_result_dense.md
uv run python eval/run_eval.py --top-k 5

# 生成层（需 .env 有 DEEPSEEK_API_KEY，约 18 分钟）→ eval/gen_eval_result.md
uv run python eval/run_gen_eval.py
uv run python eval/run_gen_eval.py --output eval/gen_eval_result_v6.md  # 保留版本
uv run python eval/run_gen_eval.py --limit 5  # 快速测试
```

## 指标含义

### 检索层

- **Recall@K**：有标答题里，Top-K 是否包含任一期望文件（命中率）
- **Precision@K**：Top-K 里命中期望文件的比例（检索精度）
- **MRR@K**：第一个命中期望文件的排名倒数均值（排序质量，越接近 1 越好）
- **should_abstain**：不在库内的题，不参与 Recall 分子；检索层仅记录

### 生成层

- **拒答准确率**：应该拒答的题里，确实拒答的比例（越高越好）
- **误拒答率**：不该拒答的题里，却拒答了的比例（越低越好）
- **幻觉率**：非拒答回答里，LLM 判定包含编造命令/步骤的比例（越低越好）
  - 评估器用 temperature=0 的 LLM 逐条检查回答中的命令是否在文档中有对应

## 检索层基线记录

| 阶段 | Top-K | Recall | Precision | MRR | 说明 | 日期 |
|------|-------|--------|-----------|-----|------|------|
| M4.1 纯向量（DevKit 18题） | 3 | **94.4%** | — | — | vector_count=128 | 2026-07-21 |
| M4.3 混合检索 RRF（DevKit 18题） | 3 | **94.4%** | — | — | 与 M4.1 持平 | 2026-07-21 |
| M5.2 纯向量（ShipLog 38题） | 3 | **86.8%** | 51.8% | 0.855 | vector_count=44，10 篇 kb | 2026-07-29 |
| M5.2 混合检索 RRF（ShipLog 38题） | 3 | **86.8%** | 52.6% | 0.855 | 与纯向量持平（库小） | 2026-07-29 |

### M4.1 已知 Miss（DevKit 阶段）

| id | 问题 | 期望 | 实际 Top-3 | 可能原因 |
|----|------|------|------------|----------|
| q10 | M4.2 LangGraph CRAG 要做什么？ | M4-steps.md | PLAN.md ×3 | PLAN 也含 M4 摘要，语义更近 |

### M5.2 检索层分析

- **Recall 86.8%**：38 道 scored 题中 33 道命中，5 道 miss（q39-q43 是知识库不覆盖的 On-call 场景，如 Prometheus 告警、NetworkPolicy、SSL 证书等，期望 Runbook 不存在）
- 纯向量与混合检索结果一致，因为知识库小（10 篇文档）、主题明确
- **Precision@3≈52%**：Top-3 里有重复 chunk（同一文件多块），拉低了 Precision
- **MRR≈0.855**：命中题中绝大多数第一个结果就命中，排序质量高

## 生成层评估记录（M5.2）

33 题（28 scored + 5 abstain），3 组对比实验：

| 实验 | 拒答准确率 | 误拒答率 | 幻觉率 | 说明 |
|------|-----------|----------|--------|------|
| 无 CRAG + 通用 prompt | 90.0% | 12.1% | 10.3% | 基线：直接检索→生成 |
| 无 CRAG + On-call prompt | 90.0% | 12.1% | 17.2% | 加安全 prompt 但无评分/改写 |
| 有 CRAG + On-call prompt | 90.0% | 21.2% | **11.5%** | 完整 CRAG：检索→评分→改写/拒答 |

> 数据由 `eval/run_gen_eval.py` 生成（~24min），幻觉率由 temperature=0 的 LLM 评估器逐条检查判定。  
> 完整逐题日志见 [`eval/gen_eval_result_v5.md`](gen_eval_result_v5.md)（历史版本 v2–v4 同目录）。

### 量化改进分析

**拒答准确率三组均为 90%**：10 道 abstain 题中 9 道正确拒答，1 道未拒答（q23「线上服务挂了怎么办」太模糊，LLM 倾向于给出通用建议而非拒答）。CRAG 和无 CRAG 在拒答准确率上持平，因为 abstain 题检索不到相关文档时，grade 节点和 LLM 自身都会选择拒答。

**幻觉率 10.3% → 17.2% → 11.5%**：On-call prompt 要求"按步骤编号、给出具体命令和预期输出"，诱导 LLM 补全文档中没有的命令细节（如 `jmap -dump`、`SLOWLOG GET`），导致幻觉率从通用 prompt 的 10.3% 升到 17.2%。CRAG 通过 grade 过滤不相关文档，把幻觉率从 17.2% 降到 11.5%（-5.7pp），接近通用 prompt 水平。

**误拒答率 12.1% → 21.2%**：CRAG 的 grade 节点有时太严格，把相关文档判为不相关导致误拒答。这是 safety vs availability 的 trade-off——On-call 场景下宁可误拒答也不编造命令。

### abstain 集（应拒答题，均不在知识库内）

| id | 问题 | 说明 |
|----|------|------|
| q23 | 线上服务挂了怎么办？ | 太模糊，不在库内 |
| q27 | 怎么用 kubectl 查看节点资源使用情况？ | 不在库内 |
| q31 | 怎么配置 Redis AOF 持久化？ | 不在库内 |
| q32 | MySQL 主从切换怎么做？ | 不在库内 |
| q33 | Consul 服务注册失败怎么排查？ | 不在库内 |
| q39 | 怎么配置 Prometheus 告警规则？ | 知识库不覆盖（期望 Runbook 不存在） |
| q40 | K8s NetworkPolicy 怎么配置？ | 知识库不覆盖 |
| q41 | 怎么给 Nginx 配置 SSL 证书？ | 知识库不覆盖 |
| q42 | Docker 镜像构建有哪些最佳实践？ | 知识库不覆盖 |
| q43 | GitLab CI/CD 流水线怎么配置？ | 知识库不覆盖 |

## 面试怎么说

> 自建 43 题 eval（38 scored + 10 abstain），标注期望来源文件。  
> **检索层**：`run_eval.py` 跑 Recall@3 / Precision@3 / MRR。ShipLog 库 Recall 86.8%（5 道知识库不覆盖的 On-call 场景 miss）、MRR 0.855。  
> **生成层**：`run_gen_eval.py` 对比无 CRAG vs 有 CRAG、通用 vs On-call prompt，用 temperature=0 的 LLM 逐条检查幻觉。  
> 量化改进：CRAG 把幻觉率从 **17.2% → 11.5%**（-5.7pp），代价是误拒答率从 12.1% → 21.2%（grade 偏严格的 trade-off）。  
> 意外发现：On-call prompt 要求"给出具体命令"反而诱导幻觉（10.3% → 17.2%），因为 LLM 会补全文档中没有的命令细节——prompt 设计需要平衡"详细"和"保守"。
