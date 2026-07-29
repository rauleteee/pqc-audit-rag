"""Retrieval: turn an exposure into a query and fetch supporting passages."""

from __future__ import annotations

from pqc_audit_rag.knowledge_base.embedder import Embedder
from pqc_audit_rag.knowledge_base.store import VectorStore
from pqc_audit_rag.models import Exposure, Passage


def build_query(exposure: Exposure) -> str:
    """A natural-language retrieval query describing the exposure."""
    return (
        f"Post-quantum migration guidance for {exposure.algorithm} used for "
        f"{exposure.usage.replace('_', ' ')} "
        f"(classification {exposure.classification}). "
        f"Recommended migration target {exposure.migration_target}."
    )


class Retriever:
    """Embeds a query and searches the vector store for relevant passages."""

    def __init__(self, store: VectorStore, embedder: Embedder) -> None:
        self.store = store
        self.embedder = embedder

    def retrieve(self, query: str, top_k: int = 4) -> list[Passage]:
        vector = self.embedder.embed([query])[0]
        hits = self.store.search(vector, top_k)
        return [
            Passage(id=chunk.id, text=chunk.text, source=chunk.source, score=score)
            for chunk, score in hits
        ]

    def for_exposure(self, exposure: Exposure, top_k: int = 4) -> list[Passage]:
        return self.retrieve(build_query(exposure), top_k)
