# RAG 评估基线（检索层 + 生成层）

> **检索层** `eval/run_eval.py`：只评 Retrieve（不调 LLM），输出 Recall@K / Precision@K / MRR。  
> **生成层** `eval/run_gen_eval.py`：调 LLM 对比无 CRAG vs 有 CRAG、通用 prompt vs On-call prompt，输出拒答准确率 / 误拒答率 / 幻觉率。  
> 跑之前必须先索引文档：`uv run python scripts/import_docs.py`

## 怎么跑

```powershell
cd E:\01_Dev\langChain
# 检索层
uv run python eval/run_eval.py              # 混合检索 → reports/retrieval/retrieval_eval_result.md
uv run python eval/run_eval.py --dense-only # 纯向量 → reports/retrieval/retrieval_eval_result_dense.md
uv run python eval/run_eval.py --rerank     # M6.25：RRF + CE → reports/retrieval/retrieval_eval_result_rerank.md
uv run python eval/run_eval.py --top-k 5

# 生成层（需 .env 有 DEEPSEEK_API_KEY，约 18 分钟）→ reports/generation/gen_eval_result.md
uv run python eval/run_gen_eval.py
uv run python eval/run_gen_eval.py --output eval/reports/generation/gen_eval_result_v6.md  # 保留版本
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
| M6.25 同库 RRF（vector=148） | 3 | **86.8%** | 54.4% | 0.829 | 含 demo/samples，噪声↑ | 2026-08-25 |
| M6.25 同库 RRF+Rerank（vector=148） | 3 | **84.2%** | 56.1% | 0.759 | CE 抬 postmortem，q26 miss | 2026-08-25 |

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
> 完整逐题日志见 [`generation/gen_eval_result_v5.md`](generation/gen_eval_result_v5.md)（历史版本 v2–v4 / v6 同目录）。

### 量化改进分析

**拒答准确率三组均为 90%**：10 道 abstain 题中 9 道正确拒答，1 道未拒答（q23「线上服务挂了怎么办」太模糊，LLM 倾向于给出通用建议而非拒答）。CRAG 和无 CRAG 在拒答准确率上持平，因为 abstain 题检索不到相关文档时，grade 节点和 LLM 自身都会选择拒答。

**幻觉率 10.3% → 17.2% → 11.5%**：On-call prompt 要求"按步骤编号、给出具体命令和预期输出"，诱导 LLM 补全文档中没有的命令细节（如 `jmap -dump`、`SLOWLOG GET`），导致幻觉率从通用 prompt 的 10.3% 升到 17.2%。CRAG 通过 grade 过滤不相关文档，把幻觉率从 17.2% 降到 11.5%（-5.7pp），接近通用 prompt 水平。

**误拒答率 12.1% → 21.2%**：CRAG 的 grade 节点有时太严格，把相关文档判为不相关导致误拒答。这是 safety vs availability 的 trade-off——On-call 场景下宁可误拒答也不编造命令。

### M6.27 / U-018：压低误拒答（代码已合，数字待刷新）

| 手段 | 行为 |
|------|------|
| Grade 偏召回 | 同故障域线索即相关；仅完全无关才 `NONE` |
| Soft-fallback | 改写后仍 `NONE` 且检索非空 → 带谨慎说明的 generate（默认 `CRAG_SOFT_FALLBACK=1`） |
| 硬 abstain | `CRAG_SOFT_FALLBACK=0` 可对比旧行为 |

**预期方向**（需 `run_gen_eval` 验证，挂 U-020）：误拒答 **↓**；幻觉可能略 **↑**；应拒答题若仍检索到噪声块，也可能被 soft-fallback「硬答」→ **拒答准确率**需一起看。  
当前对外口述仍可用上表 **21.2% / 11.5%** 作「优化前基线」，并说明已上 soft-fallback、全量数字待 v6。

**风险（审查备忘）**：soft-fallback = 可用性优先；库外题只要 Top-K 非空就可能不再硬 abstain。对比实验请用 `CRAG_SOFT_FALLBACK=0`。

### 与 RAGAS / faithfulness 对照（M6.26 · U-002 轻量）

> **不做**官方 `ragas` Python 包（依赖与 API 兼容成本高）。用已有 LLM-judge **幻觉率**对齐面试常说的 faithfulness 口径，并诚实区分粒度。

| 概念 | RAGAS 官方常见做法 | 本项目（`run_gen_eval.py`） |
|------|-------------------|---------------------------|
| Faithfulness | 拆答案 claim，逐条看是否被 **contexts** 蕴含，再算比例 | **答案级**：非拒答答案中，是否含「文档没有的命令/步骤」（任一即 HALLU） |
| 换算（口述用） | — | 同组 **答案级 faithfulness ≈ 1 − 幻觉率** |
| Answer relevancy | 另有指标 | 未单独测；用人工看 sources + 回答是否跑题 |

**同组换算（v5 / BASELINE 上表）**：

| 实验 | 幻觉率 | 答案级 faithfulness（≈1−幻觉率） |
|------|--------|----------------------------------|
| 无 CRAG + 通用 prompt | 10.3% | ≈ **89.7%** |
| 无 CRAG + On-call prompt | 17.2% | ≈ **82.8%** |
| 有 CRAG + On-call prompt | 11.5% | ≈ **88.5%** |

**分母（必须说清）**：幻觉率 =「**标注为应答题**（`should_abstain=false`）且模型**未拒答**」的题目里，被判 HALLU 的比例。  
**不是**「全部 43 题」的平均。应拒答却硬答的题进 **拒答准确率**，不进幻觉率分母（见 `calc_gen_metrics`）。

**重要（防穿帮）**：这是 **答案级**「整答有没有胡编」比例，**不是** RAGAS 的 **claim 级** faithfulness。数字接近时不要说「我们跑了官方 RAGAS」。可说：「目标同构——答案必须 grounded 在检索 context；实现是 DeepSeek temperature=0 的 LLM-as-judge。」

#### Case：Retrieve 命中，Generate 仍胡编

| id | 实验组 | 现象 | 说明 |
|----|--------|------|------|
| **q02** | 无 CRAG + On-call | `[HALLU]`「Redis 连接数打满了怎么办」 | 检索侧通常能命中 `redis-timeout.md`，但 On-call prompt 逼写具体命令，judge 判存在文档未覆盖细节 → **检索层 HIT ≠ 生成层 faithfulness** |
| **q08** | 有 CRAG + On-call | `[HALLU]`「服务回滚怎么操作」 | 回答已引用 `runbooks/rollback.md`，CRAG 也放行，仍被判 HALLU → 说明 grade 管「相关」，不管「生成是否逐步可溯源」 |

完整原文见 [`generation/gen_eval_result_v5.md`](generation/gen_eval_result_v5.md) 对应 `[HALLU]` 节。

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
> **生成层**：`run_gen_eval.py` 对比无 CRAG vs 有 CRAG、通用 vs On-call prompt，用 temperature=0 的 LLM 逐条检查幻觉（**答案级 faithfulness ≈ 1−幻觉率**，非官方 RAGAS 包）。  
> 量化改进：CRAG 把幻觉率从 **17.2% → 11.5%**（答案级 faithfulness ≈82.8%→88.5%），代价是误拒答率从 12.1% → 21.2%。  
> **M6.27**：grade 偏召回 + soft-fallback 降低误拒答（默认开）；全量 gen_eval 数字待刷新（U-020）。  
> 意外发现：On-call prompt 要求"给出具体命令"反而诱导幻觉（10.3% → 17.2%）。  
> **Retrieve≠Faithful**：如 q02/q08，Runbook 已命中仍可能 HALLU——要分层评测。
