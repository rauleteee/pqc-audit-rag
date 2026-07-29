"""Generate a ground-truth set with the LLM (course-aligned, optional).

For each corpus chunk, asks the local LLM for questions answerable only by that
chunk, and writes ``ground_truth.json`` ({question, chunk_id}). A curated
ground_truth.json is committed for reproducibility; run this to regenerate it
(needs a running Ollama server + the ``llm`` extra).

    python evaluation/generate_ground_truth.py
"""

from __future__ import annotations

import json
from pathlib import Path

from pqc_audit_rag.config import settings
from pqc_audit_rag.knowledge_base.ingest import load_corpus

HERE = Path(__file__).parent
OUT = HERE / "ground_truth.json"
QUESTIONS_PER_CHUNK = 2

_PROMPT = (
    "You are given a passage from a post-quantum cryptography knowledge base. "
    "Emit exactly {n} short, specific questions that this passage — and only this "
    'passage — answers. Respond as JSON: {{"questions": ["...", "..."]}}.\n\n'
    "Passage:\n{passage}"
)


def _client():
    from openai import OpenAI

    return OpenAI(base_url=settings.llm_base_url, api_key=settings.llm_api_key)


def main() -> None:
    client = _client()
    rows: list[dict] = []
    for chunk in load_corpus():
        resp = client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {
                    "role": "user",
                    "content": _PROMPT.format(n=QUESTIONS_PER_CHUNK, passage=chunk.text),
                }
            ],
            response_format={"type": "json_object"},
            temperature=0,
        )
        data = json.loads(resp.choices[0].message.content or "{}")
        for question in data.get("questions", []):
            rows.append({"question": str(question), "chunk_id": chunk.id})

    OUT.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {len(rows)} questions to {OUT}")


if __name__ == "__main__":
    main()
