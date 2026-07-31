-- PQC Audit RAG — monitoring schema (Grafana source).
-- Mounted into the Postgres container's docker-entrypoint-initdb.d so the tables
-- exist on first boot. Kept in sync with SCHEMA_SQL in
-- src/pqc_audit_rag/monitoring.py (which also creates them lazily at write time).

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
