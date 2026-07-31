"""LLM provider presets (local Ollama or a hosted OpenAI-compatible API).

The synthesizer works against any OpenAI-compatible endpoint, so switching from
the free local Ollama to a remote provider is only a base URL + model + key. This
registry gives the UI (and anyone scripting) ready-made presets so that swap is a
single choice instead of three env vars. Nothing here is a secret — the API key is
always supplied by the user at call time, never stored.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Provider:
    """One OpenAI-compatible LLM endpoint preset."""

    label: str
    base_url: str
    default_model: str
    needs_key: bool
    signup: str = ""
    note: str = ""


# Keyed by a short slug. "local" is the free default; the rest are hosted APIs the
# user points at with their own key. Groq and OpenRouter both offer a free tier.
PROVIDERS: dict[str, Provider] = {
    "local": Provider(
        label="Local Ollama (free, on-device)",
        base_url="http://localhost:11434/v1",
        default_model="llama3.2:3b",
        needs_key=False,
        note="No key, private, but CPU inference is slow.",
    ),
    "groq": Provider(
        label="Groq (free hosted API)",
        base_url="https://api.groq.com/openai/v1",
        default_model="llama-3.3-70b-versatile",
        needs_key=True,
        signup="https://console.groq.com/keys",
        note="Free, no card, very fast. Cost reads $0 (free tier).",
    ),
    "openrouter": Provider(
        label="OpenRouter (free models available)",
        base_url="https://openrouter.ai/api/v1",
        default_model="meta-llama/llama-3.3-70b-instruct:free",
        needs_key=True,
        signup="https://openrouter.ai/keys",
        note="Many models; ':free' variants cost nothing.",
    ),
    "openai": Provider(
        label="OpenAI",
        base_url="https://api.openai.com/v1",
        default_model="gpt-4o-mini",
        needs_key=True,
        signup="https://platform.openai.com/api-keys",
        note="Priced per token -> the monitoring cost panel fills in.",
    ),
    "custom": Provider(
        label="Custom (any OpenAI-compatible endpoint)",
        base_url="",
        default_model="",
        needs_key=False,
        note="Fill in the base URL, model and (if needed) key yourself.",
    ),
}

DEFAULT_PROVIDER = "local"
