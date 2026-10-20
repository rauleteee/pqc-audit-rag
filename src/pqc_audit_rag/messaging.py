"""Kafka plumbing shared by the API (producer) and the worker (consumer)."""

from __future__ import annotations

from confluent_kafka import KafkaError, KafkaException
from confluent_kafka.admin import AdminClient, NewTopic

from pqc_audit_rag.config import settings


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


if __name__ == "__main__":
    bootstrap = settings.kafka_bootstrap or "localhost:9092"
    created = ensure_topic(bootstrap, settings.kafka_topic)
    print(("created" if created else "already existed"), settings.kafka_topic)
