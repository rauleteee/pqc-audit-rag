import json

from pqc_audit_rag.judge import judge_recommendation
from pqc_audit_rag.models import Exposure, MigrationRecommendation


class _FakeClient:
    """Minimal stand-in for the OpenAI client returning a canned JSON content."""

    def __init__(self, content: str) -> None:
        message = type("M", (), {"content": content})
        choice = type("C", (), {"message": message})
        response = type("R", (), {"choices": [choice]})
        create = lambda **kwargs: response  # noqa: E731
        self.chat = type(
            "Chat",
            (),
            {"completions": type("Cmp", (), {"create": staticmethod(create)})},
        )


def _exposure():
    return Exposure(
        library="cryptography",
        algorithm="RSA-2048",
        usage="key_generation",
        classification="SHOR",
        severity="CRITICAL",
        migration_target="ML-KEM",
    )


def _rec():
    return MigrationRecommendation(
        algorithm="RSA-2048",
        usage="key_generation",
        severity="CRITICAL",
        migration_target="ML-KEM",
        summary="x",
        steps=["a"],
    )


def test_judge_parses_scores():
    client = _FakeClient(
        json.dumps({"faithfulness": 5, "actionability": 4, "reasoning": "ok"})
    )
    out = judge_recommendation(_exposure(), [], _rec(), client=client)
    assert out == {"faithfulness": 5, "actionability": 4, "reasoning": "ok"}


def test_judge_clamps_and_handles_bad_values():
    client = _FakeClient(json.dumps({"faithfulness": 9, "actionability": "bad"}))
    out = judge_recommendation(_exposure(), [], _rec(), client=client)
    assert out["faithfulness"] == 5  # clamped into 1..5
    assert out["actionability"] == 0  # unparseable -> 0
