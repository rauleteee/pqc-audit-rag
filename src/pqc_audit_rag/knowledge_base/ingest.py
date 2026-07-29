"""Ingestion pipeline: corpus markdown -> chunks -> embeddings -> vector store.

Run as a script to build a persistent index:
    python -m pqc_audit_rag.knowledge_base.ingest
"""

from __future__ import annotations

import re
from pathlib import Path

from pqc_audit_rag.config import CORPUS_DIR, settings
from pqc_audit_rag.knowledge_base.embedder import Embedder, get_embedder
from pqc_audit_rag.knowledge_base.store import (
    Chunk,
    InMemoryStore,
    VectorStore,
    open_store,
)

# Split a markdown document into chunks at level-2 (``## ``) headings.
_SECTION_RE = re.compile(r"(?m)^(?=##\s)")


def chunk_markdown(text: str, source: str) -> list[Chunk]:
    """One chunk per ``## `` section (with any leading preamble as chunk 0)."""
    chunks: list[Chunk] = []
    for i, part in enumerate(_SECTION_RE.split(text)):
        part = part.strip()
        if not part:
            continue
        heading = part.splitlines()[0].lstrip("#").strip()
        chunks.append(Chunk(id=f"{source}#{i}", text=part, source=f"{source} :: {heading}"))
    return chunks


def load_corpus(corpus_dir: Path | str = CORPUS_DIR) -> list[Chunk]:
    """Read and chunk every ``*.md`` file in the corpus directory."""
    chunks: list[Chunk] = []
    for path in sorted(Path(corpus_dir).glob("*.md")):
        chunks.extend(chunk_markdown(path.read_text(encoding="utf-8"), path.name))
    return chunks


def build_index(
    corpus_dir: Path | str = CORPUS_DIR,
    store: VectorStore | None = None,
    embedder: Embedder | None = None,
) -> tuple[VectorStore, Embedder]:
    """Embed the corpus and load it into ``store``; return both.

    Defaults to an in-memory store (always works). Pass ``open_store(path)`` for
    a persistent LanceDB index.
    """
    embedder = embedder or get_embedder(settings.embed_model_dir)
    store = store if store is not None else InMemoryStore()
    chunks = load_corpus(corpus_dir)
    vectors = embedder.embed([c.text for c in chunks])
    store.add(chunks, vectors)
    return store, embedder


def main() -> None:
    """Build a persistent index at ``settings.db_path``."""
    store = open_store(settings.db_path)
    store, embedder = build_index(store=store)
    print(
        f"Ingested {len(store)} chunks into {settings.db_path!r} "
        f"(embedder dim={embedder.dim})."
    )


if __name__ == "__main__":
    main()
