import pytest

from pqc_audit_rag.metrics import check_mrr_gate

ROWS = {"hybrid + rerank": {"hit_rate": 0.87, "mrr": 0.704}}


def test_gate_passes_above_minimum():
    passed, message = check_mrr_gate(ROWS, "hybrid + rerank", 0.69)
    assert passed
    assert "PASSED" in message


def test_gate_passes_exactly_at_minimum():
    passed, _ = check_mrr_gate(ROWS, "hybrid + rerank", 0.704)
    assert passed


def test_gate_fails_below_minimum():
    passed, message = check_mrr_gate(ROWS, "hybrid + rerank", 0.71)
    assert not passed
    assert "FAILED" in message and "0.704" in message


def test_gate_rejects_unknown_method():
    with pytest.raises(KeyError):
        check_mrr_gate(ROWS, "nope", 0.7)
