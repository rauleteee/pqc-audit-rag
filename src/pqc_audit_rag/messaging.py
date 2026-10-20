"""Kafka plumbing shared by the API (producer) and the worker (consumer)."""

from __future__ import annotations

import json

from confluent_kafka import KafkaError, KafkaException, Producer
from confluent_kafka.admin import AdminClient, NewTopic

from pqc_audit_rag.config import settings
from pqc_audit_rag.errors import PublishError


def ensure_topic(
    bootstrap: str,
    topic: str,
    *,
    partitions: int = 1,
    timeout: float = 15.0,
) -> bool:
    """Create the topic if missing. Return True if created, False if it existed."""
    admin = AdminClient({"bootstrap.servers": bootstrap})
    new_topic = NewTopic(topic, num_partitions=partitions, replication_factor=1)
    futures = admin.create_topics([new_topic], request_timeout=timeout)
    try:
        futures[topic].result(timeout=timeout)
    except KafkaException as exc:
        if exc.args[0].code() == KafkaError.TOPIC_ALREADY_EXISTS:
            return False
        raise
    return True


def make_producer(bootstrap: str) -> Producer:
    return Producer(
        {
            "bootstrap.servers": bootstrap,
            "acks": "all",
            "enable.idempotence": True,
        }
    )


def publish_job(
    producer: Producer, topic: str, job_id: str, *, timeout: float = 10.0
) -> None:
    """Send one job id to the topic and wait until Kafka confirms it."""
    errors: list[KafkaError] = []

    def on_delivery(err: KafkaError | None, _msg) -> None:
        if err is not None:
            errors.append(err)

    payload = json.dumps({"job_id": job_id}).encode("utf-8")
    try:
        producer.produce(
            topic, key=job_id.encode("utf-8"), value=payload, on_delivery=on_delivery
        )
    except (BufferError, KafkaException) as exc:
        raise PublishError(str(exc)) from exc
    pending = producer.flush(timeout)
    if pending or errors:
        raise PublishError(str(errors[0]) if errors else "timed out waiting for Kafka")


if __name__ == "__main__":
    bootstrap = settings.kafka_bootstrap or "localhost:9092"
    created = ensure_topic(bootstrap, settings.kafka_topic)
    print(("created" if created else "already existed"), settings.kafka_topic)
