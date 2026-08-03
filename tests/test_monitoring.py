"""Offline tests for the monitoring layer (no Postgres needed).

They exercise the pure helpers (cost, row flattening, DSN resolution) and the
best-effort no-op contract: with no DSN configured, nothing is persisted and no
exception escapes.
"""

from pqc_audit_rag import monitoring
from pqc_audit_rag.models import AuditReport, MigrationRecommendation


def _report(**kw) -> AuditReport:
    base = {
        "path": "proj/",
        "verdict": "quantum-critical cryptography in use — migration needed",
        "counts": {"CRITICAL": 2, "MEDIUM": 1, "INFO": 0, "total": 3},
        "recommendations": [
            MigrationRecommendation(
                algorithm="RSA-2048",
                usage="key_generation",
                severity="CRITICAL",
                migration_target="ML-KEM",
                summary="x",
                steps=["a"],
            )
        ],
        "generated_by": "llm",
        "model": "llama3.1",
        "retrieval_method": "rerank",
        "prompt_style": "concise",
        "top_k": 4,
        "latency_ms": 1234.5,
        "prompt_tokens": 100,
        "completion_tokens": 50,
        "total_tokens": 150,
    }
    base.update(kw)
    return AuditReport(**base)


def test_calc_cost_local_model_is_free():
    assert monitoring.calc_cost("llama3.1", 1000, 1000) == 0.0
    assert monitoring.calc_cost("", 1000, 1000) == 0.0


def test_calc_cost_priced_model():
    # gpt-4o-mini: $0.15 / $0.60 per 1M tokens.
    cost = monitoring.calc_cost("gpt-4o-mini", 1_000_000, 1_000_000)
    assert round(cost, 4) == 0.75


def test_dsn_and_enabled_use_override():
    assert monitoring.dsn("  postgres://x  ") == "postgres://x"
    assert monitoring.enabled("postgres://x") is True
    assert monitoring.enabled("") is False


def test_run_row_flattens_report():
    row = monitoring._run_row(_report())
    assert row["scanned_path"] == "proj/"
    assert row["critical"] == 2 and row["medium"] == 1 and row["total"] == 3
    assert row["recommendations"] == 1
    assert row["retrieval_method"] == "rerank"
    assert row["prompt_style"] == "concise"
    assert row["total_tokens"] == 150
    assert row["cost_usd"] == 0.0  # local model


def test_run_row_costs_a_priced_model():
    row = monitoring._run_row(_report(model="gpt-4o-mini"))
    assert row["cost_usd"] > 0.0


def test_record_is_noop_without_dsn():
    # Default settings have no DSN -> both calls are safe no-ops.
    assert monitoring.record_run(_report(), override="") is None
    assert monitoring.record_feedback({"rating": "up"}, override="") is False
    assert monitoring.init_schema(override="") is False
