import os

import pytest

psycopg = pytest.importorskip("psycopg")

from pqc_audit_rag.migrate import migrate  # noqa: E402

DSN = os.environ.get("PQC_RAG_TEST_PG_DSN", "")
pytestmark = pytest.mark.skipif(not DSN, reason="set PQC_RAG_TEST_PG_DSN")


def test_migrate_is_idempotent_and_creates_audit_job():
    migrate(DSN)
    assert migrate(DSN) == []
    with psycopg.connect(DSN) as conn:
        row = conn.execute("SELECT to_regclass('audit_job')").fetchone()
    assert row[0] == "audit_job"
