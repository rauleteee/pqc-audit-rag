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
import re
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


_SUMMARY_RE = re.compile(r'"summary"\s*:\s*"((?:[^"\\]|\\.)*)"', re.S)
_STEPS_RE = re.compile(r'"steps"\s*:\s*\[(.*)', re.S)
_QUOTED_RE = re.compile(r'"((?:[^"\\]|\\.)*)"')


def _unescape(value: str) -> str:
    """Turn a raw JSON-string body back into text (handles \\n, \\" …)."""
    try:
        return json.loads(f'"{value}"')
    except json.JSONDecodeError:
        return value


def _extract_payload(content: str) -> tuple[str, list[str]]:
    """Pull ``(summary, steps)`` from a model reply that may not be clean JSON.

    Handles, in order: a plain JSON object; a ```json fenced object; a JSON object
    embedded in prose; a **truncated** JSON object (max_tokens cut it off) — the
    summary and any complete steps are salvaged by regex rather than dumping the
    raw braces; and, last, free-form prose (used as the summary). A working LLM
    call therefore never renders raw JSON or an empty recommendation.
    """
    text = (content or "").strip()
    if not text:
        return "", []

    # Strip a leading ``` or ```json fence, keep what's before the closing fence.
    if text.startswith("```"):
        inner = text[3:]
        if inner[:4].lower() == "json":
            inner = inner[4:]
        text = inner.rsplit("```", 1)[0].strip()

    # 1) Well-formed JSON (whole string, or a {...} block embedded in prose).
    data: Any = None
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end > start:
            try:
                data = json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                data = None

    if isinstance(data, dict):
        summary = str(data.get("summary", "")).strip()
        raw_steps = data.get("steps", [])
        if isinstance(raw_steps, str):
            raw_steps = [raw_steps]
        steps = [str(s).strip() for s in raw_steps if str(s).strip()]
        if summary or steps:
            return summary, steps

    # 2) Broken/truncated JSON: salvage the summary and any complete steps.
    match = _SUMMARY_RE.search(text)
    if match:
        summary = _unescape(match.group(1)).strip()
        steps: list[str] = []
        steps_match = _STEPS_RE.search(text)
        if steps_match:
            steps = [
                _unescape(s).strip()
                for s in _QUOTED_RE.findall(steps_match.group(1))
                if _unescape(s).strip()
            ]
        return summary, steps

    # 3) No JSON structure at all — fall back to the raw prose as the summary.
    return text, []


class LLMSynthesizer:
    """LLM synthesizer over any OpenAI-compatible endpoint (Ollama by default)."""

    name = "llm"

    def __init__(
        self,
        model: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        prompt_style: str | None = None,
        max_tokens: int | None = None,
        verify_tls: bool | str | None = None,
    ) -> None:
        self.model = model or settings.llm_model
        self.base_url = base_url or settings.llm_base_url
        self.api_key = api_key or settings.llm_api_key
        self.prompt_style = prompt_style or settings.synthesis_prompt
        self.max_tokens = max_tokens or settings.llm_max_tokens
        # TLS verification: True (default, use certifi), False (skip — insecure,
        # for trusted internal endpoints), or a path to a CA bundle to trust
        # (e.g. a company root CA). Needed for self-signed / private-CA gateways.
        self.verify_tls: bool | str = (
            settings.llm_verify_tls if verify_tls is None else verify_tls
        )
        # Token usage captured per call, kept for the monitoring phase.
        self.usages: list[Any] = []

    def _client(self):
        from openai import OpenAI

        kwargs: dict[str, Any] = {}
        if self.verify_tls is not True:
            import httpx

            kwargs["http_client"] = httpx.Client(verify=self.verify_tls)
        return OpenAI(base_url=self.base_url, api_key=self.api_key, **kwargs)

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

    def _complete(self, messages: list[dict], *, json_format: bool) -> str:
        """One chat completion; returns the message content (may be empty)."""
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": 0,
            "max_tokens": self.max_tokens,
        }
        if json_format:
            kwargs["response_format"] = {"type": "json_object"}
        response = self._client().chat.completions.create(**kwargs)
        self.usages.append(getattr(response, "usage", None))
        if not response.choices:
            return ""
        return response.choices[0].message.content or ""

    def synthesize(
        self, exposure: Exposure, passages: list[Passage]
    ) -> MigrationRecommendation:
        messages = [
            {"role": "system", "content": _system_prompt(self.prompt_style)},
            {"role": "user", "content": self._user_prompt(exposure, passages)},
        ]
        # Ask for a JSON object first. Many gateways / non-OpenAI models behind a
        # proxy (e.g. LiteLLM) either reject the response_format param or return an
        # empty body for it, so on empty/error we retry as plain text and parse
        # leniently — the user should always get prose, never an empty card.
        try:
            content = self._complete(messages, json_format=True)
        except Exception:
            content = ""
        if not content.strip():
            content = self._complete(messages, json_format=False)

        summary, steps = _extract_payload(content)
        return MigrationRecommendation(
            algorithm=exposure.algorithm,
            usage=exposure.usage,
            severity=exposure.severity,
            migration_target=exposure.migration_target,
            summary=summary,
            steps=steps,
            citations=_citations(passages),
        )


# Backwards/naming convenience: the default LLM backend is a local Ollama server.
OllamaSynthesizer = LLMSynthesizer
