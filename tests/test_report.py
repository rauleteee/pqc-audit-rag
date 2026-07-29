from pqc_audit_rag.pipeline import run_audit
from pqc_audit_rag.report import to_html, to_markdown
from pqc_audit_rag.synthesis import FakeSynthesizer


def _report(vulnerable_file, retriever):
    return run_audit(
        str(vulnerable_file), retriever=retriever, synthesizer=FakeSynthesizer()
    )


def test_markdown_has_headline_and_target(vulnerable_file, retriever):
    md = to_markdown(_report(vulnerable_file, retriever))
    assert "# Post-Quantum Exposure & Migration Report" in md
    assert "Verdict:" in md
    assert "RSA" in md
    assert "migrate to" in md


def test_html_is_self_contained_and_escaped(vulnerable_file, retriever):
    html_out = to_html(_report(vulnerable_file, retriever))
    assert html_out.startswith("<!doctype html>")
    assert "<title>" in html_out
    # Self-contained: no external assets pulled in.
    assert "src=" not in html_out
    assert "<link" not in html_out
    assert "RSA" in html_out
