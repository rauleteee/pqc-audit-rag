import os
import time
import uuid

import pytest

pytest.importorskip("confluent_kafka")
pytest.importorskip("psycopg")
pytest.importorskip("fastapi")

from confluent_kafka import Consumer  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from pqc_audit_rag.api import runner  # noqa: E402
from pqc_audit_rag.api.main import create_app  # noqa: E402
from pqc_audit_rag.api.pg_store import PostgresJobStore  # noqa: E402
from pqc_audit_rag.messaging import (  # noqa: E402
    ensure_topic,
    make_producer,
    publish_job,
)
from pqc_audit_rag.migrate import migrate  # noqa: E402
from pqc_audit_rag.synthesis import FakeSynthesizer  # noqa: E402
from pqc_audit_rag.worker import process_message  # noqa: E402

PG_DSN = os.environ.get("PQC_RAG_TEST_PG_DSN", "")
KAFKA = os.environ.get("PQC_RAG_TEST_KAFKA_BOOTSTRAP", "")
pytestmark = pytest.mark.skipif(
    not (PG_DSN and KAFKA),
    reason="needs PQC_RAG_TEST_PG_DSN and PQC_RAG_TEST_KAFKA_BOOTSTRAP",
)


def _poll(consumer: Consumer, seconds: float = 20.0):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        msg = consumer.poll(1.0)
        if msg is not None and msg.error() is None:
            return msg
    raise AssertionError("no message arrived in Kafka")


def test_job_travels_from_api_through_kafka_to_the_worker(
    retriever, tmp_path, vulnerable_file, monkeypatch
):
    repo = tmp_path / "repo"
    repo.mkdir()
    code = vulnerable_file.read_text(encoding="utf-8")
    (repo / "vuln.py").write_text(code, encoding="utf-8")
    monkeypatch.setattr(runner, "clone_github_repo", lambda url: repo)

    migrate(PG_DSN)
    topic = f"test.{uuid.uuid4().hex[:8]}"
    ensure_topic(KAFKA, topic)
    producer = make_producer(KAFKA)
    store = PostgresJobStore(PG_DSN)
    app = create_app(
        store=store,
        retriever=retriever,
        synthesizer_factory=FakeSynthesizer,
        publisher=lambda job_id: publish_job(producer, topic, job_id),
    )

    with TestClient(app) as client:
        response = client.post("/audits", json={"repo_url": "https://github.com/o/r"})
        assert response.status_code == 202
        job_id = response.json()["id"]
        assert client.get(f"/audits/{job_id}").json()["status"] == "queued"

        consumer = Consumer(
            {
                "bootstrap.servers": KAFKA,
                "group.id": f"test-{uuid.uuid4().hex[:8]}",
                "auto.offset.reset": "earliest",
                "enable.auto.commit": False,
            }
        )
        consumer.subscribe([topic])
        try:
            msg = _poll(consumer)
            result = process_message(
                msg.value(),
                store,
                retriever=retriever,
                synthesizer_factory=FakeSynthesizer,
            )
            consumer.commit(message=msg, asynchronous=False)
        finally:
            consumer.close()

        assert result == "ran"
        body = client.get(f"/audits/{job_id}").json()
        assert body["status"] == "done"
        assert body["report"]["counts"]["CRITICAL"] >= 1
