"""Retrieval strategies: dense, text (minsearch), hybrid (RRF) and re-ranking.

All strategies expose the same interface as ``Retriever`` — ``retrieve(query,
top_k) -> list[Passage]`` and ``for_exposure(exposure, top_k)`` — so the pipeline
can use any of them interchangeably. Which one is the default is decided by the
retrieval evaluation (``evaluation/evaluate_retrieval.py``).
"""

from __future__ import annotations

import re

from pqc_audit_rag.knowledge_base.store import Chunk
from pqc_audit_rag.models import Exposure, Passage
from pqc_audit_rag.retrieval import Retriever, build_query

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> set[str]:
    return set(_TOKEN_RE.findall(text.lower()))


class TextRetriever:
    """Keyword search via minsearch (the course's text-search engine)."""

    def __init__(self, chunks: list[Chunk]) -> None:
        from minsearch import Index

        self._by_id = {c.id: c for c in chunks}
        self.index = Index(text_fields=["text", "source"], keyword_fields=["id"])
        self.index.fit(
            [{"id": c.id, "text": c.text, "source": c.source} for c in chunks]
        )

    def retrieve(self, query: str, top_k: int = 4) -> list[Passage]:
        docs = self.index.search(query, num_results=top_k)
        passages = []
        for rank, doc in enumerate(docs):
            chunk = self._by_id[doc["id"]]
            passages.append(
                Passage(
                    id=chunk.id,
                    text=chunk.text,
                    source=chunk.source,
                    score=1.0 / (rank + 1),
                )
            )
        return passages

    def for_exposure(self, exposure: Exposure, top_k: int = 4) -> list[Passage]:
        return self.retrieve(build_query(exposure), top_k)


class HybridRetriever:
    """Fuse dense + text rankings with Reciprocal Rank Fusion (RRF)."""

    def __init__(
        self,
        dense: Retriever,
        text: TextRetriever,
        k: int = 60,
        candidates: int = 10,
    ) -> None:
        self.dense = dense
        self.text = text
        self.k = k
        self.candidates = candidates

    def retrieve(self, query: str, top_k: int = 4) -> list[Passage]:
        dense_hits = self.dense.retrieve(query, self.candidates)
        text_hits = self.text.retrieve(query, self.candidates)

        scores: dict[str, float] = {}
        passages: dict[str, Passage] = {}
        for hits in (dense_hits, text_hits):
            for rank, passage in enumerate(hits):
                scores[passage.id] = scores.get(passage.id, 0.0) + 1.0 / (
                    self.k + rank + 1
                )
                passages.setdefault(passage.id, passage)

        ranked = sorted(scores, key=lambda cid: scores[cid], reverse=True)[:top_k]
        return [passages[cid].model_copy(update={"score": scores[cid]}) for cid in ranked]

    def for_exposure(self, exposure: Exposure, top_k: int = 4) -> list[Passage]:
        return self.retrieve(build_query(exposure), top_k)


class RerankRetriever:
    """Second-stage re-ranking of a base retriever's candidates.

    Re-scores candidates by lexical coverage of the query (a light, offline,
    deterministic re-ranker; a cross-encoder or LLM re-ranker can be dropped in
    behind the same interface).
    """

    def __init__(self, base, candidates: int = 10) -> None:
        self.base = base
        self.candidates = candidates

    def _score(self, query_tokens: set[str], passage: Passage) -> float:
        if not query_tokens:
            return 0.0
        return len(query_tokens & _tokens(passage.text)) / len(query_tokens)

    def retrieve(self, query: str, top_k: int = 4) -> list[Passage]:
        candidates = self.base.retrieve(query, self.candidates)
        query_tokens = _tokens(query)
        rescored = sorted(
            candidates, key=lambda p: self._score(query_tokens, p), reverse=True
        )
        return [
            p.model_copy(update={"score": self._score(query_tokens, p)})
            for p in rescored[:top_k]
        ]

    def for_exposure(self, exposure: Exposure, top_k: int = 4) -> list[Passage]:
        return self.retrieve(build_query(exposure), top_k)


def make_retriever(
    method: str = "hybrid",
    *,
    store=None,
    embedder=None,
    index_path: str | None = None,
    rebuild: bool = False,
):
    """Build a retriever for ``method`` in {dense, text, hybrid, rerank}."""
    from pqc_audit_rag.knowledge_base.ingest import load_corpus, load_or_build

    if store is None or embedder is None:
        store, embedder = load_or_build(index_path, embedder, rebuild)
    dense = Retriever(store, embedder)
    if method == "dense":
        return dense

    text = TextRetriever(load_corpus())
    if method == "text":
        return text
    hybrid = HybridRetriever(dense, text)
    if method == "hybrid":
        return hybrid
    if method == "rerank":
        return RerankRetriever(hybrid)
    raise ValueError(f"unknown retrieval method: {method!r}")
