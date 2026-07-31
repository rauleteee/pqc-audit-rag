"""Domain models for the RAG pipeline (pydantic).

These are flat, JSON-friendly models: an ``Exposure`` (a grouped finding from the
scanner), a ``Passage`` (a retrieved corpus chunk), a ``MigrationRecommendation``
(the LLM's per-exposure output) and the ``AuditReport`` that ties it together.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class Exposure(BaseModel):
    """A group of scanner findings that share (library, algorithm, usage).

    One exposure is the unit the RAG pipeline reasons about: it is what we build
    a retrieval query from and what the synthesizer writes a recommendation for.
    """

    library: str
    algorithm: str
    usage: str
    classification: str
    severity: str
    migration_target: str
    occurrences: int = 1
    locations: list[str] = Field(default_factory=list)
    representative_symbol: str = ""


class Passage(BaseModel):
    """A retrieved chunk of the knowledge base, with its similarity score."""

    id: str
    text: str
    source: str
    score: float = 0.0


class MigrationRecommendation(BaseModel):
    """The synthesized, cited migration guidance for a single exposure."""

    algorithm: str
    usage: str
    severity: str
    migration_target: str
    summary: str
    steps: list[str] = Field(default_factory=list)
    citations: list[str] = Field(default_factory=list)


class AuditReport(BaseModel):
    """The full result of an audit: verdict, counts and per-exposure guidance.

    The trailing fields are run metadata (retrieval method, prompt style, model,
    latency and token usage). They are populated by the pipeline and consumed by
    the monitoring layer; they default to empty so nothing else has to set them.
    """

    path: str
    verdict: str
    counts: dict[str, int] = Field(default_factory=dict)
    recommendations: list[MigrationRecommendation] = Field(default_factory=list)
    generated_by: str = "fake"
    # Run metadata (for monitoring / Grafana).
    model: str = ""
    retrieval_method: str = ""
    prompt_style: str = ""
    top_k: int = 0
    latency_ms: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
