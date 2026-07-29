"""Vector stores.

``InMemoryStore`` (numpy cosine) is the default — zero dependencies, used by the
tests and offline runs. ``LanceDBStore`` is the on-disk store for real,
persistent indexes (optional dependency). Both implement the same ``VectorStore``
protocol so the retriever does not care which is behind it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np


@dataclass
class Chunk:
    """A stored unit of the knowledge base."""

    id: str
    text: str
    source: str


class VectorStore(Protocol):
    def add(self, chunks: list[Chunk], vectors: np.ndarray) -> None: ...

    def search(self, vector: np.ndarray, top_k: int) -> list[tuple[Chunk, float]]: ...

    def __len__(self) -> int: ...


class InMemoryStore:
    """Cosine-similarity search over an in-memory matrix of unit vectors."""

    def __init__(self) -> None:
        self._chunks: list[Chunk] = []
        self._matrix: np.ndarray | None = None

    def add(self, chunks: list[Chunk], vectors: np.ndarray) -> None:
        if not chunks:
            return
        self._chunks.extend(chunks)
        self._matrix = (
            vectors if self._matrix is None else np.vstack([self._matrix, vectors])
        )

    def search(self, vector: np.ndarray, top_k: int) -> list[tuple[Chunk, float]]:
        if self._matrix is None or not self._chunks:
            return []
        sims = self._matrix @ vector
        top = np.argsort(-sims)[: max(top_k, 0)]
        return [(self._chunks[i], float(sims[i])) for i in top]

    def __len__(self) -> int:
        return len(self._chunks)


class LanceDBStore:
    """On-disk vector store backed by LanceDB (optional dependency)."""

    def __init__(self, path: str, table: str = "corpus") -> None:
        import lancedb

        self._db = lancedb.connect(path)
        self._table = table

    def add(self, chunks: list[Chunk], vectors: np.ndarray) -> None:
        if not chunks:
            return
        rows = [
            {
                "id": c.id,
                "text": c.text,
                "source": c.source,
                "vector": vectors[i].tolist(),
            }
            for i, c in enumerate(chunks)
        ]
        if self._table in self._db.list_tables().tables:
            self._db.open_table(self._table).add(rows)
        else:
            self._db.create_table(self._table, data=rows)

    def search(self, vector: np.ndarray, top_k: int) -> list[tuple[Chunk, float]]:
        if self._table not in self._db.list_tables().tables:
            return []
        rows = (
            self._db.open_table(self._table)
            .search(vector.tolist())
            .limit(top_k)
            .to_list()
        )
        results: list[tuple[Chunk, float]] = []
        for r in rows:
            # LanceDB returns L2 distance in ``_distance``; convert to a score.
            score = 1.0 / (1.0 + float(r.get("_distance", 0.0)))
            results.append((Chunk(id=r["id"], text=r["text"], source=r["source"]), score))
        return results

    def __len__(self) -> int:
        if self._table not in self._db.list_tables().tables:
            return 0
        return self._db.open_table(self._table).count_rows()


def open_store(path: str | None = None, table: str = "corpus") -> VectorStore:
    """Open a persistent LanceDB store at ``path``; fall back to in-memory."""
    if path:
        try:
            return LanceDBStore(path, table=table)
        except Exception:
            pass
    return InMemoryStore()
