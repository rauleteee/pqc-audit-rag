from pqc_audit_rag.pipeline import run_audit
from pqc_audit_rag.synthesis import FakeSynthesizer


def test_run_audit_end_to_end(vulnerable_file, retriever):
    report = run_audit(
        str(vulnerable_file),
        retriever=retriever,
        synthesizer=FakeSynthesizer(),
    )

    assert report.counts["CRITICAL"] >= 1
    assert report.counts["total"] >= 1
    assert report.generated_by == "fake"
    assert "migration needed" in report.verdict

    assert report.recommendations
    rec = report.recommendations[0]
    assert "RSA" in rec.algorithm
    assert rec.migration_target
    assert rec.steps
    assert rec.citations  # grounded in retrieved passages


def test_run_audit_default_retrieval(vulnerable_file):
    # No retriever injected: exercises make_retriever with the default method.
    report = run_audit(str(vulnerable_file), synthesizer=FakeSynthesizer())
    assert report.counts["CRITICAL"] >= 1
    assert report.recommendations
    assert report.recommendations[0].citations


def test_run_audit_populates_run_metadata(vulnerable_file, retriever):
    report = run_audit(
        str(vulnerable_file),
        retriever=retriever,
        synthesizer=FakeSynthesizer(),
        method="hybrid",
        top_k=3,
    )
    # Metadata the monitoring layer persists.
    assert report.retrieval_method == "hybrid"
    assert report.top_k == 3
    assert report.latency_ms >= 0.0
    # FakeSynthesizer makes no LLM calls -> no token usage.
    assert report.total_tokens == 0
    assert report.model == ""


def test_run_audit_clean_file(tmp_path, retriever):
    clean = tmp_path / "clean.py"
    clean.write_text("x = 1 + 1\n")
    report = run_audit(str(clean), retriever=retriever, synthesizer=FakeSynthesizer())
    assert report.counts["total"] == 0
    assert report.recommendations == []
    assert "no cryptography" in report.verdict
