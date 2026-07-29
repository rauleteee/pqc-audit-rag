"""Orchestrator: scan -> group -> retrieve -> synthesize -> report.

The control flow is deterministic; the LLM is used only to synthesize prose for
each exposure. This mirrors the OSS engine's discipline: interfaces stay thin,
knowledge lives in the corpus, and detection is delegated to ``pqc-audit``.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable

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
    on_event: Callable[[str, float | None], None] | None = None,
) -> AuditReport:
    """Run a full audit and return an ``AuditReport``.

    Retrieval wiring: pass a ready ``retriever``, or a ``store`` + ``embedder``,
    or an ``index_path`` to a persistent LanceDB index, or nothing. ``method``
    selects the retrieval strategy (dense|text|hybrid|rerank); the default comes
    from the evaluation (``settings.retrieval_method``).

    ``on_event(message, progress)`` is called with human-readable progress
    updates (``progress`` is a 0..1 fraction, or ``None``) so an interface can
    show what step is running.
    """
    top_k = top_k or settings.top_k

    def emit(message: str, progress: float | None = None) -> None:
        if on_event is not None:
            on_event(message, progress)

    if retriever is None:
        emit("Preparing knowledge base…", 0.0)
        retriever = make_retriever(
            method or settings.retrieval_method,
            store=store,
            embedder=embedder,
            index_path=index_path,
            rebuild=rebuild_index,
        )

    synthesizer = synthesizer or FakeSynthesizer()

    emit(f"Scanning {path} for vulnerable cryptography…", 0.05)
    findings = scan(path)
    files = sorted({f.path for f in findings})
    exposures = group_exposures(findings)
    emit(
        f"Found {len(findings)} finding(s) in {len(files)} file(s) → "
        f"{len(exposures)} distinct exposure(s).",
        0.1,
    )

    recommendations = []
    total = len(exposures) or 1
    for i, exp in enumerate(exposures, 1):
        base = 0.1 + 0.9 * (i - 1) / total
        emit(
            f"[{i}/{len(exposures)}] Retrieving migration guidance for "
            f"{exp.algorithm} ({exp.usage.replace('_', ' ')})…",
            base,
        )
        passages = retriever.for_exposure(exp, top_k)
        emit(
            f"[{i}/{len(exposures)}] Synthesizing migration plan for "
            f"{exp.algorithm}…",
            base + 0.45 * 0.9 / total,
        )
        recommendations.append(synthesizer.synthesize(exp, passages))

    emit("Building report…", 1.0)
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
