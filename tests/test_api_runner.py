from pqc_audit_rag.api import runner
from pqc_audit_rag.api.schemas import JobStatus
from pqc_audit_rag.api.store import InMemoryJobStore
from pqc_audit_rag.sources import SourceError
from pqc_audit_rag.synthesis import FakeSynthesizer


def _fake_repo(tmp_path, vulnerable_file):
    repo = tmp_path / "repo"
    repo.mkdir()
    code = vulnerable_file.read_text(encoding="utf-8")
    (repo / "vuln.py").write_text(code, encoding="utf-8")
    return repo


def test_run_job_success(monkeypatch, tmp_path, vulnerable_file, retriever):
    repo = _fake_repo(tmp_path, vulnerable_file)
    monkeypatch.setattr(runner, "clone_github_repo", lambda url: repo)
    store = InMemoryJobStore()
    job = store.create("https://github.com/org/repo")

    runner.run_job(
        job.id, store, retriever=retriever, synthesizer_factory=FakeSynthesizer
    )

    done = store.get(job.id)
    assert done.status == JobStatus.done
    assert done.report is not None
    assert done.report.counts["CRITICAL"] >= 1
    assert done.report.path == job.repo_url
    assert not repo.exists()  # the temp repo was cleaned up


def test_run_job_clone_failure(monkeypatch, retriever):
    def boom(url):
        raise SourceError("Clone failed")

    monkeypatch.setattr(runner, "clone_github_repo", boom)
    store = InMemoryJobStore()
    job = store.create("https://github.com/org/repo")

    runner.run_job(
        job.id, store, retriever=retriever, synthesizer_factory=FakeSynthesizer
    )

    failed = store.get(job.id)
    assert failed.status == JobStatus.failed
    assert "Clone failed" in failed.error
