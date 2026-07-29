import pytest

pytest.importorskip("lancedb")

from pqc_audit_rag.knowledge_base.embedder import HashingEmbedder
from pqc_audit_rag.knowledge_base.ingest import build_index, load_or_build
from pqc_audit_rag.knowledge_base.store import LanceDBStore, open_store
from pqc_audit_rag.retrieval import Retriever


def test_lancedb_index_persists_and_reloads(tmp_path):
    path = str(tmp_path / "idx")

    store = open_store(path)
    assert isinstance(store, LanceDBStore)
    build_index(store=store, embedder=HashingEmbedder())
    n = len(store)
    assert n > 0

    # Reload without rebuilding: same rows, no re-embedding.
    store2, embedder2 = load_or_build(path=path, embedder=HashingEmbedder())
    assert isinstance(store2, LanceDBStore)
    assert len(store2) == n

    passages = Retriever(store2, embedder2).retrieve("migrate RSA to ML-KEM", top_k=3)
    assert passages
    assert "ML-KEM" in " ".join(p.text for p in passages)
