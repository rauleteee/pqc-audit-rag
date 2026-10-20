import json
import os

import pytest

pytest.importorskip("psycopg")

from pqc_audit_rag.api import runner  # noqa: E402
from pqc_audit_rag.api.pg_store import PostgresJobStore  # noqa: E402
from pqc_audit_rag.api.schemas import JobStatus  # noqa: E402
from pqc_audit_rag.migrate import migrate  # noqa: E402
from pqc_audit_rag.synthesis import FakeSynthesizer  # noqa: E402
from pqc_audit_rag.worker import process_message  # noqa: E402

DSN = os.environ.get("PQC_RAG_TEST_PG_DSN", "")
pytestmark = pytest.mark.skipif(not DSN, reason="set PQC_RAG_TEST_PG_DSN")


@pytest.fixture
def store():
    migrate(DSN)
    return PostgresJobStore(DSN)


def test_claim_only_works_once(store):
    job = store.create("https://github.com/org/repo")
    first = store.claim(job.id)
    assert first.status == JobStatus.running
    assert store.claim(job.id) is None


def test_process_message_runs_job_once(
    store, retriever, tmp_path, vulnerable_file, monkeypatch
):
    repo = tmp_path / "repo"
    repo.mkdir()
    code = vulnerable_file.read_text(encoding="utf-8")
    (repo / "vuln.py").write_text(code, encoding="utf-8")
    monkeypatch.setattr(runner, "clone_github_repo", lambda url: repo)

    job = store.create("https://github.com/org/repo")
    raw = json.dumps({"job_id": job.id}).encode()
    kwargs = {"retriever": retriever, "synthesizer_factory": FakeSynthesizer}

    assert process_message(raw, store, **kwargs) == "ran"
    done = store.get(job.id)
    assert done.status == JobStatus.done
    assert done.report.counts["CRITICAL"] >= 1
    assert process_message(raw, store, **kwargs) == "skipped"


def test_malformed_message_is_dropped(store, retriever):
    result = process_message(
        b"not json", store, retriever=retriever, synthesizer_factory=FakeSynthesizer
    )
    assert result == "invalid"
