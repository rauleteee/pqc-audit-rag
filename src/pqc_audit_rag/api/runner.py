import shutil
from collections.abc import Callable
from pathlib import Path

from pqc_audit_rag.api.schemas import JobStatus
from pqc_audit_rag.api.store import InMemoryJobStore
from pqc_audit_rag.pipeline import run_audit
from pqc_audit_rag.sources import SourceError, clone_github_repo
from pqc_audit_rag.synthesis import Synthesizer


def run_job(
    job_id: str,
    store: InMemoryJobStore,
    *,
    retriever,
    synthesizer_factory: Callable[[], Synthesizer],
) -> None:
    job = store.get(job_id)
    store.update(job_id, status=JobStatus.running)
    repo_dir: Path | None = None
    try:
        repo_dir = clone_github_repo(job.repo_url)
        report = run_audit(
            str(repo_dir),
            retriever=retriever,
            synthesizer=synthesizer_factory(),
        )
        report = report.model_copy(update={"path": job.repo_url})
        store.update(job_id, status=JobStatus.done, report=report)
    except SourceError as exc:
        store.update(job_id, status=JobStatus.failed, error=str(exc))
    except Exception as exc:
        store.update(job_id, status=JobStatus.failed, error=f"Unexpected error: {exc}")
    finally:
        if repo_dir is not None:
            shutil.rmtree(repo_dir, ignore_errors=True)
