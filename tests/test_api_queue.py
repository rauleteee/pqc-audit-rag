from fastapi.testclient import TestClient

from pqc_audit_rag.api.main import create_app
from pqc_audit_rag.api.schemas import JobStatus
from pqc_audit_rag.api.store import InMemoryJobStore
from pqc_audit_rag.errors import PublishError
from pqc_audit_rag.synthesis import FakeSynthesizer


def _client(retriever, store, publisher):
    app = create_app(
        store=store,
        retriever=retriever,
        synthesizer_factory=FakeSynthesizer,
        publisher=publisher,
    )
    return TestClient(app)


def test_post_publishes_job_id_and_leaves_job_queued(retriever):
    store = InMemoryJobStore()
    sent: list[str] = []
    with _client(retriever, store, sent.append) as client:
        response = client.post("/audits", json={"repo_url": "https://github.com/o/r"})

    job_id = response.json()["id"]
    assert response.status_code == 202
    assert sent == [job_id]
    assert store.get(job_id).status == JobStatus.queued


def test_publish_failure_returns_503_and_marks_job_failed(retriever):
    store = InMemoryJobStore()

    def broken(job_id: str) -> None:
        raise PublishError("kafka down")

    with _client(retriever, store, broken) as client:
        response = client.post("/audits", json={"repo_url": "https://github.com/o/r"})

    assert response.status_code == 503
    (job,) = store._jobs.values()
    assert job.status == JobStatus.failed
    assert "kafka down" in job.error
