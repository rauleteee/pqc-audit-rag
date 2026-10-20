"""Kafka consumer: take job ids off the queue and run the audits."""

from __future__ import annotations

import json
import logging

from pqc_audit_rag.api.pg_store import PostgresJobStore
from pqc_audit_rag.api.runner import run_job

log = logging.getLogger("pqc_audit_rag.worker")


def process_message(
    raw: bytes, store: PostgresJobStore, *, retriever, synthesizer_factory
) -> str:
    """Handle one message. Return 'ran', 'skipped' or 'invalid'."""
    try:
        job_id = json.loads(raw)["job_id"]
    except (ValueError, KeyError, TypeError):
        log.warning("dropping malformed message: %r", raw)
        return "invalid"
    if store.claim(job_id) is None:
        log.info("job %s already taken or finished, skipping", job_id)
        return "skipped"
    run_job(
        job_id, store, retriever=retriever, synthesizer_factory=synthesizer_factory
    )
    return "ran"
