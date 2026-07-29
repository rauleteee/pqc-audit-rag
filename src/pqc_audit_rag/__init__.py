"""Public API for the PQC Audit RAG application.

Detection is delegated to the OSS ``pqc-audit`` engine; this package adds the
migration knowledge base (RAG), orchestration and reporting.
"""

from __future__ import annotations

from pqc_audit_rag.grouping import group_exposures
from pqc_audit_rag.models import (
    AuditReport,
    Exposure,
    MigrationRecommendation,
    Passage,
)
from pqc_audit_rag.pipeline import run_audit
from pqc_audit_rag.report import to_html, to_markdown
from pqc_audit_rag.retrieval import Retriever, build_query
from pqc_audit_rag.synthesis import FakeSynthesizer, LLMSynthesizer, OllamaSynthesizer
from pqc_audit_rag.version import __version__

__all__ = [
    "__version__",
    "run_audit",
    "group_exposures",
    "build_query",
    "Retriever",
    "FakeSynthesizer",
    "LLMSynthesizer",
    "OllamaSynthesizer",
    "to_markdown",
    "to_html",
    "Exposure",
    "Passage",
    "MigrationRecommendation",
    "AuditReport",
]
