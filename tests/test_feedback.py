import json

from pqc_audit_rag.feedback import record_feedback
from pqc_audit_rag.models import AuditReport


def test_record_feedback_appends_jsonl(tmp_path):
    report = AuditReport(
        path="proj/",
        verdict="quantum-critical cryptography in use — migration needed",
        counts={"CRITICAL": 2, "MEDIUM": 1, "INFO": 0, "total": 3},
        recommendations=[],
        generated_by="fake",
    )
    dest = tmp_path / "fb.jsonl"

    record_feedback(report, "up", path=dest)
    record_feedback(report, "down", path=dest)

    lines = dest.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    first = json.loads(lines[0])
    assert first["rating"] == "up"
    assert first["counts"]["CRITICAL"] == 2
    assert first["generated_by"] == "fake"
    assert "ts" in first
    assert json.loads(lines[1])["rating"] == "down"
