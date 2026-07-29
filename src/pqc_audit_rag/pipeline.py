"""Orchestrator: scan -> group -> retrieve -> synthesize -> report.

The control flow is deterministic; the LLM is used only to synthesize prose for
each exposure. This mirrors the OSS engine's discipline: interfaces stay thin,
knowledge lives in the corpus, and detection is delegated to ``pqc-audit``.
"""

from __future__ import annotations

from collections import Counter

from pqc_scanner import scan

from pqc_audit_rag.config import settings
from pqc_audit_rag.grouping import group_exposures
from pqc_audit_rag.knowledge_base.embedder import Embedder
from pqc_audit_rag.knowledge_base.store import VectorStore
from pqc_audit_rag.models import AuditReport
from pqc_audit_rag.retrieval import Retriever
from pqc_audit_rag.search import make_retriever
from pqc_audit_rag.synthesis import FakeSynthesizer, Synthesizer


def _verdict(counts: Counter) -> str:
    if counts.get("CRITICAL"):
        return "quantum-critical cryptography in use — migration needed"
    if counts.get("MEDIUM"):
        return "quantum-weakened cryptography in use — review recommended"
    if counts.get("INFO"):
        return "only post-quantum cryptography detected"
    return "no cryptography detected in scope"


def run_audit(
    path: str,
    *,
    synthesizer: Synthesizer | None = None,
    retriever: Retriever | None = None,
    store: VectorStore | None = None,
    embedder: Embedder | None = None,
    index_path: str | None = None,
    rebuild_index: bool = False,
    method: str | None = None,
    top_k: int | None = None,
) -> AuditReport:
    """Run a full audit and return an ``AuditReport``.

    Retrieval wiring: pass a ready ``retriever``, or a ``store`` + ``embedder``,
    or an ``index_path`` to a persistent LanceDB index, or nothing. ``method``
    selects the retrieval strategy (dense|text|hybrid|rerank); the default comes
    from the evaluation (``settings.retrieval_method``).
    """
    top_k = top_k or settings.top_k

    if retriever is None:
        retriever = make_retriever(
            method or settings.retrieval_method,
            store=store,
            embedder=embedder,
            index_path=index_path,
            rebuild=rebuild_index,
        )

    synthesizer = synthesizer or FakeSynthesizer()

    findings = scan(path)
    exposures = group_exposures(findings)
    recommendations = [
        synthesizer.synthesize(exp, retriever.for_exposure(exp, top_k))
        for exp in exposures
    ]

    counts = Counter(f.severity.value for f in findings)
    return AuditReport(
        path=str(path),
        verdict=_verdict(counts),
        counts={
            "CRITICAL": counts.get("CRITICAL", 0),
            "MEDIUM": counts.get("MEDIUM", 0),
            "INFO": counts.get("INFO", 0),
            "total": len(findings),
        },
        recommendations=recommendations,
        generated_by=synthesizer.name,
    )
