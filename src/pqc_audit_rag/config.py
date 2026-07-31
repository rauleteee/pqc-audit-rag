"""Runtime configuration, driven by environment variables with safe defaults.

Kept dependency-light (dataclass + os.environ) so importing the package never
requires pydantic-settings or a config file. Defaults target a free local stack:
an Ollama server exposing an OpenAI-compatible API, and a local ONNX embedding
model — the same shape used throughout the LLM Zoomcamp course.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

# Location of the curated corpus shipped with the package.
CORPUS_DIR = Path(__file__).parent / "knowledge_base" / "corpus"


def _parse_verify(value: str) -> bool | str:
    """Parse ``PQC_RAG_LLM_VERIFY``: true/false toggle, or a CA-bundle path.

    ``true`` (default) verifies with certifi; ``false`` skips verification (for
    trusted internal endpoints with a private/self-signed CA); anything else is
    treated as a path to a CA bundle to trust.
    """
    low = value.strip().lower()
    if low in ("", "true", "1", "yes", "on"):
        return True
    if low in ("false", "0", "no", "off"):
        return False
    return value.strip()


@dataclass(frozen=True)
class Settings:
    """Resolved settings. Read once at import as ``settings``."""

    # LLM: any OpenAI-compatible endpoint. Default = local Ollama (free, no key).
    llm_base_url: str = os.environ.get(
        "OPENAI_BASE_URL", "http://localhost:11434/v1"
    )
    llm_api_key: str = os.environ.get("OPENAI_API_KEY", "ollama")
    llm_model: str = os.environ.get("PQC_RAG_LLM", "llama3.1")
    # TLS verification for the LLM endpoint: True | False | path to a CA bundle.
    # Set PQC_RAG_LLM_VERIFY=false for an internal gateway with a private CA.
    llm_verify_tls: bool | str = _parse_verify(os.environ.get("PQC_RAG_LLM_VERIFY", "true"))
    # Cap synthesis output length. High enough that a summary + several steps fit
    # without the JSON being truncated; lower it (e.g. 300) for faster CPU runs.
    llm_max_tokens: int = int(os.environ.get("PQC_RAG_MAX_TOKENS", "700"))

    # Embeddings: a local ONNX model directory (tokenizer.json + model.onnx).
    embed_model: str = os.environ.get("PQC_RAG_EMBED", "Xenova/all-MiniLM-L6-v2")
    embed_model_dir: str = os.environ.get(
        "PQC_RAG_EMBED_DIR", "models/Xenova/all-MiniLM-L6-v2"
    )

    db_path: str = os.environ.get("PQC_RAG_DB", ".pqc_rag_index")
    top_k: int = int(os.environ.get("PQC_RAG_TOPK", "4"))
    # Default retrieval strategy (dense|text|hybrid|rerank). The evaluation
    # (evaluation/evaluate_retrieval.py) picks "rerank" as the best.
    retrieval_method: str = os.environ.get("PQC_RAG_RETRIEVAL", "rerank")
    # Synthesis prompt style (concise|detailed|checklist). The LLM evaluation
    # (evaluation/evaluate_llm.py) picks the best.
    synthesis_prompt: str = os.environ.get("PQC_RAG_PROMPT", "concise")

    # Monitoring: Postgres DSN for persisting audits + feedback (Grafana source).
    # Empty by default -> monitoring is a no-op (the free stack needs no server).
    pg_dsn: str = os.environ.get("PQC_RAG_PG_DSN", "")


settings = Settings()
