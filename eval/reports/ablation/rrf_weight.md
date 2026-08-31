# RRF / BM25 权重消融（U-031）

> 同一知识库、同一 `questions.json`、Top-K=3、**不重嵌**、关 Rerank。  
> 库规模：vector_count=48, bm25_count=48。  
> 代码默认：`VECTOR_RRF_WEIGHT=1.0` / `BM25_RRF_WEIGHT=0.35`（`app/rag/retriever.py`）。

## 结果表

| 配置 | scored | Recall@3 | Precision@3 | MRR@3 | 说明 |
|------|-------:|---------:|------------:|------:|------|
| dense-only | 38 | **86.8%** | 49.1% | 0.855 | 纯向量基线（关 BM25） |
| hybrid 1/0.35 | 38 | **86.8%** | 50.9% | 0.842 | 现行默认（向量主、BM25 辅） ← 选用 |
| hybrid 1.0/0.2 | 38 | **86.8%** | 50.9% | 0.855 | BM25 更弱 |
| hybrid 1.0/0.5 | 38 | **86.8%** | 50.0% | 0.842 | BM25 略强 |
| hybrid 1.0/1.0 | 38 | **86.8%** | 48.2% | 0.829 | 两路等权（易被关键词堆叠带偏） |

## 结论

- **选用**：`hybrid 1/0.35`（Recall@3=86.8%，MRR@3=0.842，P@3=50.9%）。
- 判定：hybrid 组先比 Recall；**Recall 与现行默认并列 → 保留 1.0/0.35**（本库各组 Recall 常持平，MRR 微差不改口述口径）。
- 观察：等权 **1.0/1.0** 的 P@3 / MRR 最差，印证「勿等权、防关键词堆叠」；`1.0/0.2` MRR 略高但 Recall 持平。
- 面试口述：「跑过纯向量与多档 BM25 权重；Recall 持平下保留向量主、BM25=0.35；等权会掉排序质量。」

## 怎么复现

```powershell
cd E:\01_Dev\langChain
uv run python eval/run_rrf_ablation.py
```
