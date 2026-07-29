from pqc_audit_rag.models import Exposure
from pqc_audit_rag.retrieval import build_query


def test_build_query_mentions_algorithm_and_target():
    exp = Exposure(
        library="cryptography",
        algorithm="RSA-2048",
        usage="key_generation",
        classification="SHOR",
        severity="CRITICAL",
        migration_target="ML-KEM",
    )
    query = build_query(exp)
    assert "RSA-2048" in query and "ML-KEM" in query and "key generation" in query


def test_retrieve_returns_scored_passages(retriever):
    passages = retriever.retrieve("migrate RSA key exchange to ML-KEM", top_k=3)
    assert 1 <= len(passages) <= 3
    # Scores are sorted descending.
    scores = [p.score for p in passages]
    assert scores == sorted(scores, reverse=True)
    # Each passage carries a human-readable source.
    assert all(p.source for p in passages)


def test_retrieve_finds_relevant_corpus_chunk(retriever):
    exp = Exposure(
        library="cryptography",
        algorithm="RSA-2048",
        usage="key_exchange",
        classification="SHOR",
        severity="CRITICAL",
        migration_target="ML-KEM",
    )
    passages = retriever.for_exposure(exp, top_k=4)
    joined = " ".join(p.text for p in passages).lower()
    assert "ml-kem" in joined  # the mapping/standards chunks surface
