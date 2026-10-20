import os

import pytest

pytest.importorskip("psycopg")

from pqc_audit_rag.api.pg_store import PostgresJobStore  # noqa: E402
from pqc_audit_rag.api.schemas import JobStatus  # noqa: E402
from pqc_audit_rag.migrate import migrate  # noqa: E402
from pqc_audit_rag.models import AuditReport  # noqa: E402

DSN = os.environ.get("PQC_RAG_TEST_PG_DSN", "")
pytestmark = pytest.mark.skipif(not DSN, reason="set PQC_RAG_TEST_PG_DSN")


@pytest.fixture
def store():
    migrate(DSN)
    return PostgresJobStore(DSN)


def test_create_and_get(store):
    job = store.create("https://github.com/org/repo")
    assert job.status == JobStatus.queued
    assert store.get(job.id) == job


def test_get_unknown_returns_none(store):
    assert store.get("nope") is None


def test_update_status(store):
    job = store.create("https://github.com/org/repo")
    store.update(job.id, status=JobStatus.running)
    assert store.get(job.id).status == JobStatus.running


def test_report_round_trip(store):
    job = store.create("https://github.com/org/repo")
    report = AuditReport(path="https://github.com/org/repo", verdict="CRITICAL")
    store.update(job.id, status=JobStatus.done, report=report)
    saved = store.get(job.id)
    assert saved.status == JobStatus.done
    assert saved.report == report


def test_update_unknown_job_raises(store):
    with pytest.raises(KeyError):
        store.update("nope", status=JobStatus.running)
