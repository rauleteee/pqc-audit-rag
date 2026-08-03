"""Evaluate synthesis prompt styles with an LLM-as-judge.

For each prompt style (concise / detailed / checklist), synthesize a migration
recommendation for every exposure in the sample project, then have the LLM judge
score faithfulness and actionability (1-5). Aggregates the scores, picks the best
style and writes LLM_RESULTS.md. Needs a running Ollama server + the ``llm`` extra.

    python evaluation/evaluate_llm.py
"""

from __future__ import annotations

from pathlib import Path

from pqc_scanner import scan

from pqc_audit_rag.config import settings
from pqc_audit_rag.grouping import group_exposures
from pqc_audit_rag.judge import judge_recommendation
from pqc_audit_rag.search import make_retriever
from pqc_audit_rag.synthesis import SYNTHESIS_STYLES, LLMSynthesizer

HERE = Path(__file__).parent
RESULTS = HERE / "LLM_RESULTS.md"
SAMPLE = Path(__file__).parents[1] / "examples" / "vulnerable_sample.py"


def main() -> None:
    exposures = group_exposures(scan(str(SAMPLE)))
    retriever = make_retriever(settings.retrieval_method)
    # Retrieve once per exposure (retrieval is fixed; only the prompt varies).
    contexts = {
        e.algorithm: retriever.for_exposure(e, settings.top_k) for e in exposures
    }

    rows: dict[str, dict] = {}
    for style in SYNTHESIS_STYLES:
        synth = LLMSynthesizer(prompt_style=style)
        faith, act = 0.0, 0.0
        for exposure in exposures:
            passages = contexts[exposure.algorithm]
            rec = synth.synthesize(exposure, passages)
            scores = judge_recommendation(exposure, passages, rec)
            faith += scores["faithfulness"]
            act += scores["actionability"]
        n = len(exposures)
        rows[style] = {
            "faithfulness": faith / n,
            "actionability": act / n,
            "overall": (faith + act) / (2 * n),
        }
        print(
            f"{style:10} faith={rows[style]['faithfulness']:.2f} "
            f"act={rows[style]['actionability']:.2f} overall={rows[style]['overall']:.2f}"
        )

    best = max(rows, key=lambda s: rows[s]["overall"])
    header = (
        f"# LLM evaluation (synthesis prompt styles)\n\n"
        f"Exposures judged: **{len(exposures)}** · judge & synthesizer: "
        f"**{settings.llm_model}** · retrieval: **{settings.retrieval_method}**\n\n"
        f"| Prompt style | Faithfulness (1-5) | Actionability (1-5) | Overall |\n"
        f"|---|---|---|---|\n"
    )
    body = "".join(
        f"| {style}{' **(best)**' if style == best else ''} "
        f"| {m['faithfulness']:.2f} | {m['actionability']:.2f} | {m['overall']:.2f} |\n"
        for style, m in rows.items()
    )
    footer = (
        f"\n**Winner: {best}** — wired as the default synthesis prompt "
        f"(`settings.synthesis_prompt`). Scores are LLM-as-judge (1-5): "
        "faithfulness (grounded in context) and actionability (concrete, correct "
        "steps).\n"
    )
    RESULTS.write_text(header + body + footer, encoding="utf-8")
    print(header + body + footer)
    print(f"Wrote {RESULTS}")


if __name__ == "__main__":
    main()
