import pytest
from fastapi.testclient import TestClient

from pqc_audit_rag.api import runner
from pqc_audit_rag.api.main import create_app
from pqc_audit_rag.api.schemas import JobStatus
from pqc_audit_rag.synthesis import FakeSynthesizer


@pytest.fixture
def client(retriever, tmp_path, vulnerable_file, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    code = vulnerable_file.read_text(encoding="utf-8")
    (repo / "vuln.py").write_text(code, encoding="utf-8")
    monkeypatch.setattr(runner, "clone_github_repo", lambda url: repo)
    app = create_app(retriever=retriever, synthesizer_factory=FakeSynthesizer)
    with TestClient(app) as test_client:
        yield test_client


def test_create_audit_returns_202_and_id(client):
    response = client.post("/audits", json={"repo_url": "https://github.com/org/repo"})
    assert response.status_code == 202
    assert response.json()["id"]
    assert response.json()["status"] == "queued"


def test_get_audit_done_with_report(client):
    created = client.post("/audits", json={"repo_url": "https://github.com/org/repo"})
    job_id = created.json()["id"]

    response = client.get(f"/audits/{job_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == JobStatus.done.value
    assert body["report"]["counts"]["CRITICAL"] >= 1


def test_get_unknown_audit_returns_404(client):
    assert client.get("/audits/nope").status_code == 404


def test_create_audit_requires_repo_url(client):
    assert client.post("/audits", json={}).status_code == 422
