"""LLM-as-judge: score a migration recommendation.

Given an exposure, the context passages the assistant was shown, and the
assistant's recommendation, an LLM scores two dimensions on a 1-5 scale:

- faithfulness: is every claim supported by the provided context? (no hallucination)
- actionability: are the steps concrete and correct for this exposure?

Used by evaluation/evaluate_llm.py to compare synthesis prompt styles.
"""

from __future__ import annotations

import json

from pqc_audit_rag.config import settings
from pqc_audit_rag.models import Exposure, MigrationRecommendation, Passage

_JUDGE_SYSTEM = (
    "You are a strict evaluator of post-quantum cryptography migration guidance. "
    "You are given a cryptographic exposure, the context passages an assistant was "
    "shown, and the assistant's recommendation. Score two dimensions from 1 (poor) "
    "to 5 (excellent):\n"
    "- faithfulness: is every claim supported by the context passages, with no "
    "invented facts?\n"
    "- actionability: are the migration steps concrete and correct for this "
    "exposure?\n"
    'Respond ONLY as JSON: {"faithfulness": <1-5>, "actionability": <1-5>, '
    '"reasoning": "<one sentence>"}.'
)


def _client():
    from openai import OpenAI

    return OpenAI(base_url=settings.llm_base_url, api_key=settings.llm_api_key)


def _user_prompt(
    exposure: Exposure,
    passages: list[Passage],
    recommendation: MigrationRecommendation,
) -> str:
    context = (
        "\n\n".join(f"[{i + 1}] {p.source}\n{p.text}" for i, p in enumerate(passages))
        or "(no context)"
    )
    steps = "\n".join(f"- {s}" for s in recommendation.steps)
    return (
        f"Exposure: {exposure.algorithm} used for "
        f"{exposure.usage.replace('_', ' ')} (suggested target "
        f"{exposure.migration_target}).\n\n"
        f"Context passages:\n{context}\n\n"
        f"Assistant recommendation:\nSummary: {recommendation.summary}\n"
        f"Steps:\n{steps}"
    )


def _clamp(value) -> int:
    try:
        return max(1, min(5, int(value)))
    except (TypeError, ValueError):
        return 0


def judge_recommendation(
    exposure: Exposure,
    passages: list[Passage],
    recommendation: MigrationRecommendation,
    *,
    model: str | None = None,
    client=None,
) -> dict:
    """Return ``{faithfulness, actionability, reasoning}`` scored by the LLM."""
    client = client or _client()
    response = client.chat.completions.create(
        model=model or settings.llm_model,
        messages=[
            {"role": "system", "content": _JUDGE_SYSTEM},
            {
                "role": "user",
                "content": _user_prompt(exposure, passages, recommendation),
            },
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )
    data = json.loads(response.choices[0].message.content or "{}")
    return {
        "faithfulness": _clamp(data.get("faithfulness")),
        "actionability": _clamp(data.get("actionability")),
        "reasoning": str(data.get("reasoning", "")),
    }
