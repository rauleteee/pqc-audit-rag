# CLAUDE.md — pqc-audit-rag

Project guide and next steps. For user-facing docs and the run instructions, see
`README.md`.

## What this is

An end-to-end **RAG / agent application** (the LLM Zoomcamp final project) that
turns a cryptography inventory into an actionable **post-quantum migration plan**.
It scans a Python project for quantum-vulnerable crypto (via the OSS `pqc-audit`
engine), retrieves migration guidance from a curated knowledge base, and a local
LLM synthesizes a cited, per-finding migration recommendation.

Runs on a **free, local stack** (no paid API keys): Ollama for the LLM, ONNX for
embeddings, LanceDB + minsearch for search.

## Architecture

Deterministic pipeline; the LLM only writes prose. See the component diagram in
`README.md`.

```
scan (pqc-audit) -> group_exposures -> retrieve (RAG) -> synthesize (LLM) -> report
```

- **Detection** — `pqc-audit` (OSS, PyPI), static AST scan. Consumed as a
  dependency, **never reimplemented**.
- **Knowledge base** — curated Markdown corpus (`knowledge_base/corpus/`, 8 files
  / ~45 chunks, each with inline `**Sources:**` references) → chunked (ingest) →
  ONNX MiniLM embeddings → LanceDB (or in-memory) vector store + minsearch keyword
  index.
- **Retriever** (`search.py`) — dense / text / hybrid (RRF) / rerank / rewrite.
  Default = `rerank` (best by evaluation).
- **Synthesizer** (`synthesis.py`) — `LLMSynthesizer` over any OpenAI-compatible
  endpoint (Ollama by default), structured JSON output, captured token `usage`.
  Prompt styles: concise / detailed / checklist (default `concise`).
- **Report** (`report.py`) — Markdown / HTML. **Interfaces**: `cli.py`,
  `app/streamlit_app.py`.
- **Feedback** (`feedback.py`) — 👍/👎 appended to a JSONL (monitoring seed).

## Layout

```
src/pqc_audit_rag/
  config.py        # env-driven settings (single source)
  models.py        # pydantic: Exposure, Passage, MigrationRecommendation, AuditReport
  grouping.py      # findings -> exposures
  retrieval.py     # dense Retriever + build_query
  search.py        # TextRetriever, HybridRetriever (RRF), RerankRetriever,
                   #   QueryRewriteRetriever, make_retriever
  synthesis.py     # FakeSynthesizer (tests) + LLMSynthesizer + prompt styles
  judge.py         # LLM-as-judge (faithfulness / actionability)
  metrics.py       # Hit Rate / MRR
  pipeline.py      # run_audit(...) orchestrator (+ on_event progress callback)
  report.py        # to_markdown / to_html
  feedback.py      # record_feedback (JSONL)
  cli.py           # pqc-audit-rag audit|ingest
  knowledge_base/  # corpus/*.md, embedder (ONNX + hashing fallback), store
                   #   (LanceDB + in-memory), ingest, download_model
app/streamlit_app.py     # web UI (example picker, progress, feedback)
evaluation/              # ground_truth.json, evaluate_retrieval.py, evaluate_llm.py,
                         #   generate_ground_truth.py, RESULTS.md, LLM_RESULTS.md
ingestion/dlt_pipeline.py  # course-aligned dlt -> DuckDB ingestion
examples/                # sample projects for the demo / UI picker
tests/                   # 27 tests, all offline (no Ollama / no network)
```

## Running

See `README.md` Quickstart. Short version: install Ollama + `ollama pull llama3.1`
(or `llama3.2:3b` on CPU), `uv venv --python 3.12`, `uv pip install -e
".[dev,local-embed,vector,llm]"`, `python -m pqc_audit_rag.knowledge_base.download_model`,
then `streamlit run app/streamlit_app.py`.

- Tests: `pytest -q` — fully offline (hashing embedder, in-memory store, fake
  synthesizer). No Ollama/ONNX/network needed.
- Evaluations (need Ollama): `python evaluation/generate_ground_truth.py`,
  `python evaluation/evaluate_llm.py`, `python evaluation/evaluate_retrieval.py`.

## Current state — phases done

- **0–1** scaffold + RAG core.
- **2** automated ingestion (persistent LanceDB + dlt→DuckDB).
- **3** retrieval evaluation (dense/text/hybrid/rerank + query rewriting; Hit
  Rate/MRR over 269 LLM-generated questions). Winner `rerank`. → `RESULTS.md`.
- **4** LLM evaluation (3 prompt styles vs LLM-as-judge). Winner `concise`. +
  query-rewriting best practice. → `LLM_RESULTS.md`.
- **5** Streamlit UI + user feedback.

Rubric best practices covered: **hybrid search, re-ranking, query rewriting** (all
in `search.py`, all evaluated).

## Next steps

### Phase 6 — Monitoring (Postgres + Grafana)
- Persist each audit/answer to **Postgres**: timestamp, scanned path, exposure,
  retrieval method, prompt style, tokens + estimated cost + latency, and the
  👍/👎 feedback. Migrate `feedback.py` from JSONL to Postgres (keep the same
  record shape). Capture `LLMSynthesizer.usages` (tokens) for cost.
- **Grafana** dashboard with **≥5 charts** (e.g. audits over time, severity mix,
  feedback rate, tokens/cost, latency, method/prompt usage).

### Phase 7 — Containerization + reproducibility
- `docker-compose` for **everything**: app (Streamlit), Postgres, Grafana, and
  Ollama. Pin dependency versions, add a `Makefile`, ensure `docker compose up`
  runs end-to-end. Add screenshots to the README.

### Phase 8 — Cloud deployment (bonus)
- Deploy (HF Spaces / Render / a VM). Document it.

## Gotchas / conventions

- **Ollama is slow on CPU.** Use `PQC_RAG_LLM=llama3.2:3b` and
  `PQC_RAG_MAX_TOKENS=280`; Offline mode needs no LLM. Ollama runs as a **systemd
  service** (`systemctl {status,stop} ollama`).
- **Eval scripts are slow** (LLM per item) — launch them in the background.
- **Ground truth** (`evaluation/ground_truth.json`) is LLM-generated and
  committed for reproducibility; regenerate with `generate_ground_truth.py`
  (`PQC_RAG_QPC` = questions/chunk).
- **Git**: commit as `rauleteee <raul22520@gmail.com>` — the repo-local git config
  is already set (the machine's global identity is different).
- **Real source PDFs** (NIST, CCN-STIC, BSI, ANSSI) are intentionally out of scope
  here; they belong to the separate `pqc-audit-pro` product.
```
