from pqc_audit_rag.metrics import evaluate
from pqc_audit_rag.models import Passage


class StubRetriever:
    """Returns a fixed ranked id list per question."""

    def __init__(self, mapping: dict[str, list[str]]) -> None:
        self.mapping = mapping

    def retrieve(self, query: str, top_k: int):
        ids = self.mapping[query][:top_k]
        return [Passage(id=i, text="", source="") for i in ids]


def test_hit_rate_and_mrr():
    gt = [
        {"question": "q1", "chunk_id": "a"},  # relevant at rank 2 -> RR 0.5
        {"question": "q2", "chunk_id": "z"},  # not retrieved -> miss
    ]
    retriever = StubRetriever({"q1": ["x", "a", "b"], "q2": ["c", "d", "e"]})
    m = evaluate(retriever, gt, k=3)
    assert m["n"] == 2
    assert m["hit_rate"] == 0.5
    assert abs(m["mrr"] - 0.25) < 1e-9  # (0.5 + 0) / 2


def test_perfect_retrieval():
    gt = [{"question": "q", "chunk_id": "a"}]
    m = evaluate(StubRetriever({"q": ["a", "b"]}), gt, k=3)
    assert m["hit_rate"] == 1.0 and m["mrr"] == 1.0


def test_empty_ground_truth():
    m = evaluate(StubRetriever({}), [], k=3)
    assert m == {"hit_rate": 0.0, "mrr": 0.0, "n": 0}
