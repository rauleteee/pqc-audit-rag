# Retrieval evaluation

Ground-truth questions: **18** · k = **4** · embedder: **OnnxEmbedder**

| Method | Hit Rate | MRR |
|---|---|---|
| dense (vector) | 1.000 | 0.847 |
| text (minsearch) | 1.000 | 0.796 |
| hybrid (RRF) | 1.000 | 0.824 |
| hybrid + rerank **(best)** | 1.000 | 0.898 |

**Winner: hybrid + rerank** — wired as the default retrieval method.

Hit Rate = fraction of questions whose relevant chunk is in the top-k. MRR = mean reciprocal rank of the relevant chunk.
