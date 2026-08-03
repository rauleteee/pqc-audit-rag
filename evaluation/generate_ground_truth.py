"""Generate a ground-truth set with the LLM (course-aligned).

For each corpus chunk, asks the local LLM for questions answerable only by that
chunk, and writes ``ground_truth.json`` ({question, chunk_id}). Needs a running
Ollama server (or any OpenAI-compatible endpoint) + the ``llm`` extra.

    # questions per chunk (default 6): 45 chunks -> ~270 questions
    PQC_RAG_QPC=6 python evaluation/generate_ground_truth.py

A curated ground_truth.json is committed as a fallback; this overwrites it (use
git to restore the curated one if needed).
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from pqc_audit_rag.config import settings
from pqc_audit_rag.knowledge_base.ingest import load_corpus

HERE = Path(__file__).parent
OUT = HERE / "ground_truth.json"
QUESTIONS_PER_CHUNK = int(os.environ.get("PQC_RAG_QPC", "6"))

_PROMPT = (
    "You are given a passage from a post-quantum cryptography knowledge base. "
    "Emit exactly {n} short, specific, and varied questions that this passage — "
    "and only this passage — answers. Use different phrasings and angles. "
    'Respond as JSON: {{"questions": ["...", "..."]}}.\n\n'
    "Passage:\n{passage}"
)


def _client():
    from openai import OpenAI

    return OpenAI(base_url=settings.llm_base_url, api_key=settings.llm_api_key)


def main() -> None:
    client = _client()
    rows: list[dict] = []
    seen: set[str] = set()
    for chunk in load_corpus():
        resp = client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {
                    "role": "user",
                    "content": _PROMPT.format(
                        n=QUESTIONS_PER_CHUNK, passage=chunk.text
                    ),
                }
            ],
            response_format={"type": "json_object"},
            temperature=0.4,  # a little diversity across the N questions
        )
        data = json.loads(resp.choices[0].message.content or "{}")
        for question in data.get("questions", []):
            question = str(question).strip()
            key = question.lower()
            # Keep only well-formed, non-duplicate questions.
            if question.endswith("?") and key not in seen:
                seen.add(key)
                rows.append({"question": question, "chunk_id": chunk.id})

    OUT.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    print(
        f"Wrote {len(rows)} questions ({QUESTIONS_PER_CHUNK}/chunk requested) "
        f"across {len(load_corpus())} chunks to {OUT}"
    )


if __name__ == "__main__":
    main()
