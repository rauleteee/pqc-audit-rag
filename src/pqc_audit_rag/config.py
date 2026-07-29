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


@dataclass(frozen=True)
class Settings:
    """Resolved settings. Read once at import as ``settings``."""

    # LLM: any OpenAI-compatible endpoint. Default = local Ollama (free, no key).
    llm_base_url: str = os.environ.get(
        "OPENAI_BASE_URL", "http://localhost:11434/v1"
    )
    llm_api_key: str = os.environ.get("OPENAI_API_KEY", "ollama")
    llm_model: str = os.environ.get("PQC_RAG_LLM", "llama3.1")

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


settings = Settings()
