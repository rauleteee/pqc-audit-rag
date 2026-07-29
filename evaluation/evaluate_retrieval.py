"""Evaluate retrieval strategies (dense / text / hybrid / rerank).

Builds each retriever over the corpus, scores it against the ground-truth set
with Hit Rate and MRR, prints a comparison table and writes RESULTS.md. Uses the
real ONNX embeddings if the model is present (see download_model.py), otherwise
the offline hashing embedder (weaker numbers, still runnable).

    python evaluation/evaluate_retrieval.py
"""

from __future__ import annotations

import json
from pathlib import Path

from pqc_audit_rag.config import settings
from pqc_audit_rag.knowledge_base.embedder import get_embedder
from pqc_audit_rag.knowledge_base.ingest import build_index, load_corpus
from pqc_audit_rag.knowledge_base.store import InMemoryStore
from pqc_audit_rag.metrics import evaluate
from pqc_audit_rag.retrieval import Retriever
from pqc_audit_rag.search import HybridRetriever, RerankRetriever, TextRetriever

HERE = Path(__file__).parent
GROUND_TRUTH = HERE / "ground_truth.json"
RESULTS = HERE / "RESULTS.md"
K = 4


def build_retrievers():
    """One instance of each strategy, all over the same corpus/index."""
    embedder = get_embedder(settings.embed_model_dir)
    store, embedder = build_index(store=InMemoryStore(), embedder=embedder)
    dense = Retriever(store, embedder)
    text = TextRetriever(load_corpus())
    hybrid = HybridRetriever(dense, text)
    return {
        "dense (vector)": dense,
        "text (minsearch)": text,
        "hybrid (RRF)": hybrid,
        "hybrid + rerank": RerankRetriever(hybrid),
    }, embedder


def main() -> None:
    ground_truth = json.loads(GROUND_TRUTH.read_text(encoding="utf-8"))
    retrievers, embedder = build_retrievers()
    embedder_name = type(embedder).__name__

    rows = {name: evaluate(r, ground_truth, k=K) for name, r in retrievers.items()}
    # MRR is the primary metric (ranking quality); Hit Rate is near-saturated on
    # this corpus, so it only breaks ties.
    best = max(rows, key=lambda name: (rows[name]["mrr"], rows[name]["hit_rate"]))

    header = (
        f"# Retrieval evaluation\n\n"
        f"Ground-truth questions: **{len(ground_truth)}** · k = **{K}** · "
        f"embedder: **{embedder_name}**\n\n"
        f"| Method | Hit Rate | MRR |\n|---|---|---|\n"
    )
    body = "".join(
        f"| {name}{' **(best)**' if name == best else ''} "
        f"| {m['hit_rate']:.3f} | {m['mrr']:.3f} |\n"
        for name, m in rows.items()
    )
    footer = (
        f"\n**Winner (by MRR): {best}** — wired as the default retrieval method.\n\n"
        "Hit Rate = fraction of questions whose relevant chunk is in the top-k. "
        "MRR = mean reciprocal rank of the relevant chunk (primary metric: ranking "
        "quality). Ground truth is LLM-generated (see generate_ground_truth.py).\n"
    )
    RESULTS.write_text(header + body + footer, encoding="utf-8")

    print(header + body + footer)
    print(f"Wrote {RESULTS}")


if __name__ == "__main__":
    main()
