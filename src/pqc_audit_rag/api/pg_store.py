"""Postgres-backed job store: the API and the worker share state through it."""

from __future__ import annotations

import uuid

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from pqc_audit_rag.api.schemas import AuditJob, JobStatus
from pqc_audit_rag.models import AuditReport

# Static SQL: no string building, so nothing user-controlled can reach the query
# text. Values always travel separately as %s parameters.
_INSERT = (
    "INSERT INTO audit_job (id, repo_url) VALUES (%s, %s) "
    "RETURNING id, repo_url, status, report, error, created_at"
)
_SELECT = (
    "SELECT id, repo_url, status, report, error, created_at "
    "FROM audit_job WHERE id = %s"
)
_CLAIM = (
    "UPDATE audit_job SET status = 'running', updated_at = now() "
    "WHERE id = %s AND status = 'queued' "
    "RETURNING id, repo_url, status, report, error, created_at"
)
_UPDATABLE = {"status", "report", "error"}


class PostgresJobStore:
    def __init__(self, dsn: str) -> None:
        self._dsn = dsn

    def _connect(self) -> psycopg.Connection:
        return psycopg.connect(self._dsn, row_factory=dict_row)

    def create(self, repo_url: str) -> AuditJob:
        job_id = uuid.uuid4().hex
        with self._connect() as conn:
            row = conn.execute(_INSERT, (job_id, repo_url)).fetchone()
        return AuditJob.model_validate(row)

    def get(self, job_id: str) -> AuditJob | None:
        with self._connect() as conn:
            row = conn.execute(_SELECT, (job_id,)).fetchone()
        return AuditJob.model_validate(row) if row else None

    def update(self, job_id: str, **fields) -> AuditJob:
        unknown = set(fields) - _UPDATABLE
        if unknown:
            raise ValueError(f"cannot update fields: {sorted(unknown)}")
        values = []
        for value in fields.values():
            if isinstance(value, JobStatus):
                value = value.value
            elif isinstance(value, AuditReport):
                value = Jsonb(value.model_dump(mode="json"))
            values.append(value)
        # Column names come from the _UPDATABLE whitelist above, never from input;
        # all values are bound parameters. Hence the narrow nosec below.
        assignments = ", ".join(f"{name} = %s" for name in fields)
        query = (
            f"UPDATE audit_job SET {assignments}, updated_at = now() "  # nosec B608
            "WHERE id = %s "
            "RETURNING id, repo_url, status, report, error, created_at"
        )
        with self._connect() as conn:
            row = conn.execute(query, (*values, job_id)).fetchone()
        if row is None:
            raise KeyError(job_id)
        return AuditJob.model_validate(row)

    def claim(self, job_id: str) -> AuditJob | None:
        """Atomically move queued -> running. None if someone got there first."""
        with self._connect() as conn:
            row = conn.execute(_CLAIM, (job_id,)).fetchone()
        return AuditJob.model_validate(row) if row else None