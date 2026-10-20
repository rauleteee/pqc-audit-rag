from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field

from pqc_audit_rag.models import AuditReport


class JobStatus(str, Enum):
    queued = "queued"
    running = "running"
    done = "done"
    failed = "failed"


class AuditRequest(BaseModel):
    repo_url: str = Field(examples=["https://github.com/paramiko/paramiko"])


class AuditJob(BaseModel):
    id: str
    repo_url: str
    status: JobStatus = JobStatus.queued
    report: AuditReport | None = None
    error: str | None = None
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )