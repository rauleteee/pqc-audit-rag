"""Kafka consumer: take job ids off the queue and run the audits."""

from __future__ import annotations

import json
import logging
import signal

from confluent_kafka import Consumer

from pqc_audit_rag.api.pg_store import PostgresJobStore
from pqc_audit_rag.api.runner import default_synthesizer_factory, run_job
from pqc_audit_rag.config import settings
from pqc_audit_rag.messaging import ensure_topic
from pqc_audit_rag.migrate import migrate
from pqc_audit_rag.search import make_retriever

log = logging.getLogger("pqc_audit_rag.worker")

GROUP_ID = "workers"
# An audit can take minutes. If the worker doesn't poll within this time, Kafka
# assumes it died and gives its messages to someone else.
MAX_POLL_INTERVAL_MS = 900_000


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
    run_job(job_id, store, retriever=retriever, synthesizer_factory=synthesizer_factory)
    return "ran"


def run_worker() -> None:
    bootstrap, topic = settings.kafka_bootstrap, settings.kafka_topic
    if not bootstrap or not settings.pg_dsn:
        raise SystemExit("Set PQC_RAG_KAFKA_BOOTSTRAP and PQC_RAG_PG_DSN first")

    migrate(settings.pg_dsn)
    ensure_topic(bootstrap, topic)
    store = PostgresJobStore(settings.pg_dsn)
    retriever = make_retriever(settings.retrieval_method)
    synthesizer_factory = default_synthesizer_factory()

    consumer = Consumer(
        {
            "bootstrap.servers": bootstrap,
            "group.id": GROUP_ID,
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,
            "max.poll.interval.ms": MAX_POLL_INTERVAL_MS,
        }
    )
    consumer.subscribe([topic])

    running = True

    def stop(_signum, _frame) -> None:
        nonlocal running
        running = False

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)

    log.info("worker ready: topic=%s group=%s", topic, GROUP_ID)
    try:
        while running:
            msg = consumer.poll(1.0)
            if msg is None:
                continue
            if msg.error():
                log.error("kafka error: %s", msg.error())
                continue
            process_message(
                msg.value(),
                store,
                retriever=retriever,
                synthesizer_factory=synthesizer_factory,
            )
            consumer.commit(message=msg, asynchronous=False)
    finally:
        consumer.close()
        log.info("worker stopped")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    run_worker()
