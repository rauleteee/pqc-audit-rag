from pqc_audit_rag.knowledge_base.embedder import HashingEmbedder
from pqc_audit_rag.knowledge_base.ingest import build_index, load_corpus
from pqc_audit_rag.knowledge_base.store import InMemoryStore
from pqc_audit_rag.retrieval import Retriever
from pqc_audit_rag.search import (
    HybridRetriever,
    RerankRetriever,
    TextRetriever,
    heuristic_rewrite,
    make_retriever,
)


def _dense():
    store, embedder = build_index(store=InMemoryStore(), embedder=HashingEmbedder())
    return Retriever(store, embedder)


def test_text_retriever_returns_passages():
    passages = TextRetriever(load_corpus()).retrieve("ML-KEM key exchange", top_k=3)
    assert 1 <= len(passages) <= 3
    assert all(p.id and p.source for p in passages)


def test_hybrid_scores_descending():
    hybrid = HybridRetriever(_dense(), TextRetriever(load_corpus()))
    passages = hybrid.retrieve("migrate RSA signatures to ML-DSA", top_k=4)
    assert passages and len(passages) <= 4
    scores = [p.score for p in passages]
    assert scores == sorted(scores, reverse=True)


def test_rerank_returns_topk():
    rerank = RerankRetriever(HybridRetriever(_dense(), TextRetriever(load_corpus())))
    passages = rerank.retrieve("AES-128 quantum symmetric encryption", top_k=3)
    assert 1 <= len(passages) <= 3


def test_make_retriever_all_methods_build():
    for method in ("dense", "text", "hybrid", "rerank"):
        retriever = make_retriever(method, embedder=HashingEmbedder())
        passages = retriever.retrieve("post-quantum migration guidance", top_k=2)
        assert len(passages) <= 2


def test_make_retriever_rejects_unknown():
    import pytest

    with pytest.raises(ValueError):
        make_retriever("nonsense", embedder=HashingEmbedder())


def test_heuristic_rewrite_expands_acronyms():
    out = heuristic_rewrite("How to migrate RSA and ECDH keys?")
    assert "Rivest-Shamir-Adleman" in out
    assert "Diffie-Hellman" in out
    # No known acronym -> query unchanged.
    assert heuristic_rewrite("hello world") == "hello world"


def test_make_retriever_rewrite_builds():
    retriever = make_retriever("rewrite", embedder=HashingEmbedder())
    assert retriever.retrieve("migrate RSA to post-quantum", top_k=2)
