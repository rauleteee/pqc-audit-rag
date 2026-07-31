"""Monitoring: persist audits + feedback to Postgres for a Grafana dashboard.

Optional and **best-effort by design**. If no DSN is configured (env
``PQC_RAG_PG_DSN``) or psycopg / the database is unavailable, every function is a
safe no-op that returns ``None``/``False`` — monitoring must never break an
audit. This is the Postgres backend the JSONL feedback log seeded; the feedback
record shape is unchanged.

Schema (see also ``monitoring/schema.sql``, kept in sync for the docker initdb):

- ``audit_run``      — one row per audit (verdict, counts, method, tokens, cost…)
- ``audit_exposure`` — one row per recommendation (algorithm-level charts)
- ``feedback``       — one 👍/👎 per audit, optionally linked to a run
"""

from __future__ import annotations

from pqc_audit_rag.config import settings
from pqc_audit_rag.models import AuditReport

# Rough USD price per 1M tokens (input, output) for a few hosted models, so the
# cost chart works when an OpenAI-compatible cloud endpoint is used. Local Ollama
# models are not listed and cost $0 — the default free stack.
PRICES: dict[str, tuple[float, float]] = {
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o": (2.50, 10.00),
    "gpt-4.1-mini": (0.40, 1.60),
    "gpt-4.1": (2.00, 8.00),
}

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS audit_run (
    id                BIGSERIAL PRIMARY KEY,
    ts                TIMESTAMPTZ NOT NULL DEFAULT now(),
    scanned_path      TEXT NOT NULL,
    verdict           TEXT NOT NULL,
    critical          INTEGER NOT NULL DEFAULT 0,
    medium            INTEGER NOT NULL DEFAULT 0,
    info              INTEGER NOT NULL DEFAULT 0,
    total             INTEGER NOT NULL DEFAULT 0,
    recommendations   INTEGER NOT NULL DEFAULT 0,
    generated_by      TEXT NOT NULL DEFAULT '',
    model             TEXT NOT NULL DEFAULT '',
    retrieval_method  TEXT NOT NULL DEFAULT '',
    prompt_style      TEXT NOT NULL DEFAULT '',
    top_k             INTEGER NOT NULL DEFAULT 0,
    latency_ms        DOUBLE PRECISION NOT NULL DEFAULT 0,
    prompt_tokens     INTEGER NOT NULL DEFAULT 0,
    completion_tokens INTEGER NOT NULL DEFAULT 0,
    total_tokens      INTEGER NOT NULL DEFAULT 0,
    cost_usd          DOUBLE PRECISION NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS audit_exposure (
    id                BIGSERIAL PRIMARY KEY,
    run_id            BIGINT NOT NULL REFERENCES audit_run(id) ON DELETE CASCADE,
    ts                TIMESTAMPTZ NOT NULL DEFAULT now(),
    algorithm         TEXT NOT NULL,
    usage             TEXT NOT NULL DEFAULT '',
    severity          TEXT NOT NULL DEFAULT '',
    migration_target  TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS feedback (
    id                BIGSERIAL PRIMARY KEY,
    ts                TIMESTAMPTZ NOT NULL DEFAULT now(),
    run_id            BIGINT REFERENCES audit_run(id) ON DELETE SET NULL,
    scanned_path      TEXT NOT NULL DEFAULT '',
    verdict           TEXT NOT NULL DEFAULT '',
    recommendations   INTEGER NOT NULL DEFAULT 0,
    rating            TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS audit_run_ts_idx ON audit_run (ts);
CREATE INDEX IF NOT EXISTS audit_exposure_algo_idx ON audit_exposure (algorithm);
CREATE INDEX IF NOT EXISTS feedback_ts_idx ON feedback (ts);
"""


def dsn(override: str | None = None) -> str:
    """The configured Postgres DSN (empty string means monitoring is disabled)."""
    return (override if override is not None else settings.pg_dsn).strip()


def enabled(override: str | None = None) -> bool:
    """True when a DSN is configured (does not test connectivity)."""
    return bool(dsn(override))


def calc_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Estimated USD cost for a call. Local/unknown models are free ($0)."""
    rate = PRICES.get((model or "").lower())
    if rate is None:
        return 0.0
    price_in, price_out = rate
    return (prompt_tokens * price_in + completion_tokens * price_out) / 1_000_000


def _connect(override: str | None = None):
    import psycopg  # lazy: optional dependency

    return psycopg.connect(dsn(override))


def _run_row(report: AuditReport) -> dict:
    """Flatten an ``AuditReport`` into an ``audit_run`` row (pure; testable)."""
    counts = report.counts
    return {
        "scanned_path": report.path,
        "verdict": report.verdict,
        "critical": counts.get("CRITICAL", 0),
        "medium": counts.get("MEDIUM", 0),
        "info": counts.get("INFO", 0),
        "total": counts.get("total", 0),
        "recommendations": len(report.recommendations),
        "generated_by": report.generated_by,
        "model": report.model,
        "retrieval_method": report.retrieval_method,
        "prompt_style": report.prompt_style,
        "top_k": report.top_k,
        "latency_ms": report.latency_ms,
        "prompt_tokens": report.prompt_tokens,
        "completion_tokens": report.completion_tokens,
        "total_tokens": report.total_tokens,
        "cost_usd": calc_cost(
            report.model, report.prompt_tokens, report.completion_tokens
        ),
    }


_RUN_COLUMNS = (
    "scanned_path, verdict, critical, medium, info, total, recommendations, "
    "generated_by, model, retrieval_method, prompt_style, top_k, latency_ms, "
    "prompt_tokens, completion_tokens, total_tokens, cost_usd"
)


def init_schema(override: str | None = None) -> bool:
    """Create the tables if missing. Returns True on success, False otherwise."""
    if not enabled(override):
        return False
    try:
        with _connect(override) as conn:
            conn.execute(SCHEMA_SQL)
        return True
    except Exception:  # pragma: no cover - needs a live/broken DB
        return False


def record_run(report: AuditReport, override: str | None = None) -> int | None:
    """Persist one audit (+ its exposures) and return the new run id, or None.

    No-op returning None when monitoring is disabled or the DB is unreachable.
    """
    if not enabled(override):
        return None
    row = _run_row(report)
    try:
        with _connect(override) as conn:
            conn.execute(SCHEMA_SQL)
            placeholders = ", ".join(["%s"] * len(row))
            with conn.cursor() as cur:
                cur.execute(
                    f"INSERT INTO audit_run ({_RUN_COLUMNS}) "
                    f"VALUES ({placeholders}) RETURNING id",
                    list(row.values()),
                )
                run_id = cur.fetchone()[0]
                for rec in report.recommendations:
                    cur.execute(
                        "INSERT INTO audit_exposure "
                        "(run_id, algorithm, usage, severity, migration_target) "
                        "VALUES (%s, %s, %s, %s, %s)",
                        (
                            run_id,
                            rec.algorithm,
                            rec.usage,
                            rec.severity,
                            rec.migration_target,
                        ),
                    )
        return int(run_id)
    except Exception:  # pragma: no cover - needs a live/broken DB
        return None


def record_feedback(entry: dict, run_id: int | None = None,
                    override: str | None = None) -> bool:
    """Persist one feedback event. Returns True if stored in Postgres.

    ``entry`` uses the JSONL feedback shape; only the charted fields are mapped.
    """
    if not enabled(override):
        return False
    try:
        with _connect(override) as conn:
            conn.execute(SCHEMA_SQL)
            conn.execute(
                "INSERT INTO feedback "
                "(run_id, scanned_path, verdict, recommendations, rating) "
                "VALUES (%s, %s, %s, %s, %s)",
                (
                    run_id,
                    entry.get("scanned_path", ""),
                    entry.get("verdict", ""),
                    entry.get("recommendations", 0),
                    entry.get("rating", ""),
                ),
            )
        return True
    except Exception:  # pragma: no cover - needs a live/broken DB
        return False
