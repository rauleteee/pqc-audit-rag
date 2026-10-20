import threading
import uuid
from typing import Protocol

from pqc_audit_rag.api.schemas import AuditJob


class InMemoryJobStore:
    def __init__(self) -> None:
        self._jobs: dict[str, AuditJob] = {}
        self._lock = threading.Lock()

    def create(self, repo_url: str) -> AuditJob:
        job = AuditJob(id=uuid.uuid4().hex, repo_url=repo_url)
        with self._lock:
            self._jobs[job.id] = job
        return job

    def get(self, job_id: str) -> AuditJob | None:
        with self._lock:
            return self._jobs.get(job_id)

    def update(self, job_id: str, **fields) -> AuditJob:
        with self._lock:
            job = self._jobs[job_id].model_copy(update=fields)
            self._jobs[job_id] = job
            return job

class JobStore(Protocol):
    def create(self, repo_url: str) -> AuditJob: ...
    def get(self, job_id: str) -> AuditJob | None: ...
    def update(self, job_id: str, **fields) -> AuditJob: ...
