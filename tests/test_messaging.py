import os
import uuid

import pytest

pytest.importorskip("confluent_kafka")

from pqc_audit_rag.messaging import ensure_topic  # noqa: E402

pytestmark = pytest.mark.skipif(
    not os.environ.get("PQC_RAG_KAFKA_BOOTSTRAP"),
    reason="needs a running Kafka (set PQC_RAG_KAFKA_BOOTSTRAP)",
)


def test_ensure_topic_is_idempotent():
    bootstrap = os.environ["PQC_RAG_KAFKA_BOOTSTRAP"]
    topic = f"test.{uuid.uuid4().hex[:8]}"
    assert ensure_topic(bootstrap, topic) is True
    assert ensure_topic(bootstrap, topic) is False
