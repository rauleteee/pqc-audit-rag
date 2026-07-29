"""Pluggable text embedders.

The real embedder is **ONNX-based** (onnxruntime + tokenizers), mirroring the LLM
Zoomcamp course: light (no torch), local and free. It loads a model directory
(``tokenizer.json`` + ``model.onnx``); fetch one with ``download_model.py``.

When the model files or onnxruntime are unavailable we fall back to a
deterministic, dependency-free ``HashingEmbedder`` so the package and the test
suite run fully offline. The hashing embedder is a functional stand-in, not a
production-quality retriever.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Protocol, runtime_checkable

import numpy as np

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


@runtime_checkable
class Embedder(Protocol):
    """Anything that turns texts into an (n, dim) matrix of unit vectors."""

    dim: int

    def embed(self, texts: list[str]) -> np.ndarray: ...


class HashingEmbedder:
    """Deterministic bag-of-hashed-tokens embedder (offline fallback).

    Uses blake2b (not a security context) to map tokens to buckets, then L2
    normalizes so a dot product equals cosine similarity.
    """

    def __init__(self, dim: int = 256) -> None:
        self.dim = dim

    def _vector(self, text: str) -> np.ndarray:
        vec = np.zeros(self.dim, dtype=np.float32)
        for token in _tokenize(text):
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
            vec[int.from_bytes(digest, "big") % self.dim] += 1.0
        norm = float(np.linalg.norm(vec))
        return vec / norm if norm else vec

    def embed(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, self.dim), dtype=np.float32)
        return np.vstack([self._vector(t) for t in texts])


class OnnxEmbedder:
    """Local ONNX sentence embeddings (mean-pooled, L2-normalized).

    Same approach as the course embedder: onnxruntime + a HuggingFace fast
    tokenizer, CPU provider, mean pooling over the token embeddings.
    """

    def __init__(self, model_dir: str) -> None:
        import onnxruntime as ort
        from tokenizers import Tokenizer

        path = Path(model_dir)
        self.tokenizer = Tokenizer.from_file(str(path / "tokenizer.json"))
        self.session = ort.InferenceSession(
            str(path / "model.onnx"), providers=["CPUExecutionProvider"]
        )
        self.input_names = {inp.name for inp in self.session.get_inputs()}
        out_dim = self.session.get_outputs()[0].shape[-1]
        self.dim = int(out_dim) if isinstance(out_dim, int) else 384

    def embed(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, self.dim), dtype=np.float32)
        self.tokenizer.enable_padding()
        encoded = self.tokenizer.encode_batch(texts)
        feed: dict[str, np.ndarray] = {}
        if "input_ids" in self.input_names:
            feed["input_ids"] = np.array([e.ids for e in encoded], dtype=np.int64)
        if "attention_mask" in self.input_names:
            feed["attention_mask"] = np.array(
                [e.attention_mask for e in encoded], dtype=np.int64
            )
        if "token_type_ids" in self.input_names:
            feed["token_type_ids"] = np.array(
                [e.type_ids for e in encoded], dtype=np.int64
            )
        hidden = self.session.run(None, feed)[0]
        mask = feed["attention_mask"][..., None]
        pooled = (hidden * mask).sum(axis=1) / np.clip(mask.sum(axis=1), 1, None)
        norms = np.clip(np.linalg.norm(pooled, axis=1, keepdims=True), 1e-12, None)
        return (pooled / norms).astype(np.float32)


def get_embedder(model_dir: str | None = None) -> Embedder:
    """Return an ONNX embedder if its model files are present, else the
    deterministic offline fallback."""
    if model_dir and (Path(model_dir) / "model.onnx").exists():
        try:
            return OnnxEmbedder(model_dir)
        except Exception:
            pass
    return HashingEmbedder()
