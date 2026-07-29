# Retrieval evaluation

Ground-truth questions: **48** · k = **4** · embedder: **OnnxEmbedder**

| Method | Hit Rate | MRR |
|---|---|---|
| dense (vector) | 0.938 | 0.835 |
| text (minsearch) | 0.958 | 0.776 |
| hybrid (RRF) **(best)** | 0.938 | 0.861 |
| hybrid + rerank | 0.958 | 0.807 |

**Winner (by MRR): hybrid (RRF)** — wired as the default retrieval method.

Hit Rate = fraction of questions whose relevant chunk is in the top-k. MRR = mean reciprocal rank of the relevant chunk. MRR is the primary metric here (ranking quality); Hit Rate is near-saturated and only breaks ties.
