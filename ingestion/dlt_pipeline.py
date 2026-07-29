"""dlt ingestion pipeline (course-aligned automated ingestion).

Mirrors the LLM Zoomcamp dlt pattern — ``dlt.pipeline(destination="duckdb")`` —
as an automated, re-runnable ingestion tool. It extracts and chunks the curated
corpus and loads the chunk records into a local DuckDB dataset: a structured,
queryable knowledge-base table (also the seed of a future CBOM export).

This is the "special tool" ingestion path. The retrieval vector index is built
separately by ``python -m pqc_audit_rag.knowledge_base.ingest`` (embeddings ->
LanceDB); both read the same corpus.

Run:  python ingestion/dlt_pipeline.py   (needs the ``ingest`` extra: dlt[duckdb])
"""

from __future__ import annotations

import dlt

from pqc_audit_rag.knowledge_base.ingest import load_corpus


@dlt.resource(name="corpus_chunks", write_disposition="replace")
def corpus_chunks():
    """Yield one record per corpus chunk."""
    for chunk in load_corpus():
        yield {"id": chunk.id, "source": chunk.source, "text": chunk.text}


def run():
    """Run the dlt pipeline; returns dlt's load info."""
    pipeline = dlt.pipeline(
        pipeline_name="pqc_corpus",
        destination="duckdb",
        dataset_name="knowledge_base",
    )
    return pipeline.run(corpus_chunks())


if __name__ == "__main__":
    print(run())
