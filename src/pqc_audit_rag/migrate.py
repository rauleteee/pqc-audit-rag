"""Apply the numbered SQL files in ``migrations/`` that Postgres hasn't seen yet."""

from __future__ import annotations

from pathlib import Path

import psycopg

from pqc_audit_rag.config import settings

MIGRATIONS_DIR = Path(__file__).parent / "migrations"
_LOCK_ID = 727274  # any constant; every process must use the same one


def migrate(dsn: str) -> list[str]:
    """Run pending migrations in order. Return the names applied now."""
    applied_now: list[str] = []
    with psycopg.connect(dsn) as conn:
        conn.execute("SELECT pg_advisory_xact_lock(%s)", (_LOCK_ID,))
        conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations ("
            "name TEXT PRIMARY KEY, "
            "applied_at TIMESTAMPTZ NOT NULL DEFAULT now())"
        )
        done = {row[0] for row in conn.execute("SELECT name FROM schema_migrations")}
        for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
            if path.name in done:
                continue
            conn.execute(path.read_text(encoding="utf-8"))
            conn.execute("INSERT INTO schema_migrations (name) VALUES (%s)", (path.name,))
            applied_now.append(path.name)
    return applied_now


if __name__ == "__main__":
    applied = migrate(settings.pg_dsn)
    print("applied:", applied or "nothing to do")
