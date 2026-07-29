"""Lightweight user-feedback logging (append-only JSONL).

Records a thumbs up/down against an audit, plus enough context to chart later.
This is the seed of the monitoring phase; it will be swapped for Postgres then,
but the record shape stays the same.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

from pqc_audit_rag.models import AuditReport


def feedback_path() -> Path:
    """Where feedback is appended (override with ``PQC_RAG_FEEDBACK``)."""
    return Path(os.environ.get("PQC_RAG_FEEDBACK", ".pqc_rag_feedback.jsonl"))


def record_feedback(
    report: AuditReport, rating: str, *, path: Path | None = None
) -> dict:
    """Append one feedback event and return the stored entry."""
    entry = {
        "ts": time.time(),
        "scanned_path": report.path,
        "verdict": report.verdict,
        "counts": report.counts,
        "generated_by": report.generated_by,
        "recommendations": len(report.recommendations),
        "rating": rating,
    }
    dest = path or feedback_path()
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")
    return entry
