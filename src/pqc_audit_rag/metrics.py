"""Retrieval metrics: Hit Rate and MRR over a ground-truth set.

Ground truth is a list of ``{"question": str, "chunk_id": str}`` rows. A retriever
is anything with ``retrieve(query, top_k) -> [Passage]`` (``.id`` per passage).
"""

from __future__ import annotations


def evaluate(retriever, ground_truth: list[dict], k: int = 4) -> dict:
    """Return ``{hit_rate, mrr, n}`` for ``retriever`` over ``ground_truth`` at k."""
    hits = 0
    reciprocal = 0.0
    for row in ground_truth:
        ranked_ids = [p.id for p in retriever.retrieve(row["question"], k)]
        gid = row["chunk_id"]
        if gid in ranked_ids:
            hits += 1
            reciprocal += 1.0 / (ranked_ids.index(gid) + 1)
    n = len(ground_truth)
    if not n:
        return {"hit_rate": 0.0, "mrr": 0.0, "n": 0}
    return {"hit_rate": hits / n, "mrr": reciprocal / n, "n": n}
