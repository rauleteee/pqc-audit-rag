# Retrieval evaluation

Ground-truth questions: **269** · k = **4** · embedder: **OnnxEmbedder**

| Method | Hit Rate | MRR |
|---|---|---|
| dense (vector) | 0.822 | 0.686 |
| text (minsearch) | 0.758 | 0.595 |
| hybrid (RRF) | 0.840 | 0.679 |
| hybrid + rerank **(best)** | 0.870 | 0.704 |
| rewrite + rerank | 0.877 | 0.695 |

**Winner (by MRR): hybrid + rerank** — wired as the default retrieval method.

Hit Rate = fraction of questions whose relevant chunk is in the top-k. MRR = mean reciprocal rank of the relevant chunk (primary metric: ranking quality). Ground truth is LLM-generated (see generate_ground_truth.py).
