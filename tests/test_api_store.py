from pqc_audit_rag.api.schemas import JobStatus
from pqc_audit_rag.api.store import InMemoryJobStore


def test_create_and_get():
    store = InMemoryJobStore()
    job = store.create("https://github.com/org/repo")
    assert job.status == JobStatus.queued
    assert store.get(job.id) == job


def test_get_unknown_returns_none():
    assert InMemoryJobStore().get("nope") is None


def test_update_changes_status():
    store = InMemoryJobStore()
    job = store.create("https://github.com/org/repo")
    store.update(job.id, status=JobStatus.running)
    assert store.get(job.id).status == JobStatus.running
