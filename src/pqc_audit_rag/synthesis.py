"""Synthesizers: turn an exposure + retrieved passages into a recommendation.

Two implementations behind one ``Synthesizer`` protocol:

- ``FakeSynthesizer`` — deterministic, no LLM. Used by tests and offline demos.
- ``LLMSynthesizer`` — any OpenAI-compatible endpoint (local Ollama by default,
  also OpenAI/Groq). Mirrors the LLM Zoomcamp pattern: the ``openai`` SDK with
  captured token ``usage`` (kept for the monitoring phase). The deterministic
  fields (algorithm, target, severity) are filled from the exposure; the model
  only writes the prose ``summary`` and ``steps`` grounded in the retrieved
  passages, which keeps the output faithful and low-risk.
"""

from __future__ import annotations

import json
from typing import Any, Protocol, runtime_checkable

from pqc_audit_rag.config import settings
from pqc_audit_rag.models import Exposure, MigrationRecommendation, Passage


@runtime_checkable
class Synthesizer(Protocol):
    name: str

    def synthesize(
        self, exposure: Exposure, passages: list[Passage]
    ) -> MigrationRecommendation: ...


def _citations(passages: list[Passage]) -> list[str]:
    seen: list[str] = []
    for p in passages:
        if p.source not in seen:
            seen.append(p.source)
    return seen


class FakeSynthesizer:
    """Deterministic synthesizer (no LLM) for tests and offline runs."""

    name = "fake"

    def synthesize(
        self, exposure: Exposure, passages: list[Passage]
    ) -> MigrationRecommendation:
        usage = exposure.usage.replace("_", " ")
        summary = (
            f"{exposure.algorithm} (used for {usage}) is {exposure.severity}; "
            f"migrate to {exposure.migration_target}."
        )
        steps = [
            f"Inventory the {exposure.occurrences} affected call site(s) in "
            f"'{exposure.library}'.",
            f"Replace {exposure.algorithm} with {exposure.migration_target} "
            f"following the retrieved guidance.",
            "Re-run the pqc-audit scanner to confirm the exposure is cleared.",
        ]
        return MigrationRecommendation(
            algorithm=exposure.algorithm,
            usage=exposure.usage,
            severity=exposure.severity,
            migration_target=exposure.migration_target,
            summary=summary,
            steps=steps,
            citations=_citations(passages),
        )


_JSON_INSTRUCTION = (
    "Respond ONLY with a JSON object of the form "
    '{"summary": "<one paragraph>", "steps": ["<step>", "..."]}.'
)

# Alternative synthesis prompt styles, compared in evaluation/evaluate_llm.py.
SYNTHESIS_STYLES = {
    "concise": (
        "You are a post-quantum cryptography migration assistant. Using ONLY the "
        "provided context passages, write concise, actionable migration guidance "
        "for the given cryptographic exposure. Do not invent facts not supported "
        "by the context."
    ),
    "detailed": (
        "You are a senior post-quantum cryptography migration consultant. Using "
        "ONLY the provided context passages, explain the risk and give thorough, "
        "step-by-step migration guidance for the exposure, referencing the "
        "relevant standard where the context supports it. Do not invent facts."
    ),
    "checklist": (
        "You are a post-quantum migration assistant. Using ONLY the provided "
        "context passages, produce guidance for the exposure as a short summary "
        "plus a concrete, ordered checklist of migration actions. Do not invent "
        "facts not supported by the context."
    ),
}


def _system_prompt(style: str) -> str:
    base = SYNTHESIS_STYLES.get(style, SYNTHESIS_STYLES["concise"])
    return f"{base} {_JSON_INSTRUCTION}"


class LLMSynthesizer:
    """LLM synthesizer over any OpenAI-compatible endpoint (Ollama by default)."""

    name = "llm"

    def __init__(
        self,
        model: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        prompt_style: str | None = None,
    ) -> None:
        self.model = model or settings.llm_model
        self.base_url = base_url or settings.llm_base_url
        self.api_key = api_key or settings.llm_api_key
        self.prompt_style = prompt_style or settings.synthesis_prompt
        # Token usage captured per call, kept for the monitoring phase.
        self.usages: list[Any] = []

    def _client(self):
        from openai import OpenAI

        return OpenAI(base_url=self.base_url, api_key=self.api_key)

    def _user_prompt(self, exposure: Exposure, passages: list[Passage]) -> str:
        context = "\n\n".join(
            f"[{i + 1}] {p.source}\n{p.text}" for i, p in enumerate(passages)
        ) or "(no context retrieved)"
        return (
            f"Exposure: {exposure.algorithm} used for "
            f"{exposure.usage.replace('_', ' ')} "
            f"(severity {exposure.severity}, suggested target "
            f"{exposure.migration_target}), {exposure.occurrences} occurrence(s) "
            f"in '{exposure.library}'.\n\n"
            f"Context passages:\n{context}\n\n"
            "Write a one-paragraph 'summary' and a list of concrete migration "
            "'steps'."
        )

    def synthesize(
        self, exposure: Exposure, passages: list[Passage]
    ) -> MigrationRecommendation:
        response = self._client().chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": _system_prompt(self.prompt_style)},
                {"role": "user", "content": self._user_prompt(exposure, passages)},
            ],
            response_format={"type": "json_object"},
            temperature=0,
        )
        self.usages.append(getattr(response, "usage", None))
        data = json.loads(response.choices[0].message.content or "{}")
        return MigrationRecommendation(
            algorithm=exposure.algorithm,
            usage=exposure.usage,
            severity=exposure.severity,
            migration_target=exposure.migration_target,
            summary=str(data.get("summary", "")),
            steps=[str(s) for s in data.get("steps", [])],
            citations=_citations(passages),
        )


# Backwards/naming convenience: the default LLM backend is a local Ollama server.
OllamaSynthesizer = LLMSynthesizer
