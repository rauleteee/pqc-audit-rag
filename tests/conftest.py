"""Shared fixtures. Everything runs offline: hashing embedder, in-memory store,
deterministic synthesizer — no Ollama, no ONNX model, no network."""

from __future__ import annotations

import pytest

from pqc_audit_rag.knowledge_base.embedder import HashingEmbedder
from pqc_audit_rag.knowledge_base.ingest import build_index
from pqc_audit_rag.knowledge_base.store import InMemoryStore
from pqc_audit_rag.retrieval import Retriever


@pytest.fixture
def vulnerable_file(tmp_path):
    """A tiny Python file with a quantum-critical RSA key generation."""
    p = tmp_path / "vuln.py"
    p.write_text(
        "from cryptography.hazmat.primitives.asymmetric import rsa\n"
        "key = rsa.generate_private_key(public_exponent=65537, key_size=2048)\n",
        encoding="utf-8",
    )
    return p


@pytest.fixture
def retriever():
    """A retriever over the real corpus, using the offline embedder + store."""
    store, embedder = build_index(store=InMemoryStore(), embedder=HashingEmbedder())
    return Retriever(store, embedder)
