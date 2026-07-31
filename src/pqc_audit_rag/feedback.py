"""User-feedback logging: Postgres when configured, JSONL otherwise.

Records a thumbs up/down against an audit, plus enough context to chart later.
When a Postgres DSN is configured (``PQC_RAG_PG_DSN``) the event is stored there
for the Grafana dashboard; with no DSN it falls back to an append-only JSONL file
so the free local stack (and the offline tests) need no database. The stored
record shape is unchanged from the JSONL seed.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

from pqc_audit_rag import monitoring
from pqc_audit_rag.models import AuditReport


def feedback_path() -> Path:
    """Where JSONL feedback is appended (override with ``PQC_RAG_FEEDBACK``)."""
    return Path(os.environ.get("PQC_RAG_FEEDBACK", ".pqc_rag_feedback.jsonl"))


def record_feedback(
    report: AuditReport,
    rating: str,
    *,
    run_id: int | None = None,
    path: Path | None = None,
) -> dict:
    """Store one feedback event and return the entry.

    Prefers Postgres (linked to ``run_id`` when known); falls back to JSONL if
    monitoring is disabled or the database is unreachable.
    """
    entry = {
        "ts": time.time(),
        "scanned_path": report.path,
        "verdict": report.verdict,
        "counts": report.counts,
        "generated_by": report.generated_by,
        "recommendations": len(report.recommendations),
        "rating": rating,
    }
    if monitoring.record_feedback(entry, run_id=run_id):
        return entry

    dest = path or feedback_path()
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")
    return entry
