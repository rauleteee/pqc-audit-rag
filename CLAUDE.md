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
  providers.py     # LLM provider presets (local Ollama, Groq, OpenRouter, OpenAI)
  synthesis.py     # FakeSynthesizer (tests) + LLMSynthesizer + prompt styles;
                   #   robust reply parsing (_extract_payload) + TLS verify option
  judge.py         # LLM-as-judge (faithfulness / actionability)
  metrics.py       # Hit Rate / MRR
  pipeline.py      # run_audit(...) orchestrator (+ latency/token metadata)
  report.py        # to_markdown / to_html
  feedback.py      # record_feedback (Postgres if configured, else JSONL)
  monitoring.py    # best-effort Postgres persistence (audit_run/exposure/feedback)
  cli.py           # pqc-audit-rag audit|ingest
  knowledge_base/  # corpus/*.md, embedder (ONNX + hashing fallback), store
                   #   (LanceDB + in-memory), ingest, download_model
app/streamlit_app.py     # web UI (example picker, progress, feedback)
evaluation/              # ground_truth.json, evaluate_retrieval.py, evaluate_llm.py,
                         #   generate_ground_truth.py, RESULTS.md, LLM_RESULTS.md
ingestion/dlt_pipeline.py  # course-aligned dlt -> DuckDB ingestion
examples/                # sample projects for the demo / UI picker
tests/                   # 34 tests, all offline (no Ollama / no network / no DB)
monitoring/              # docker-compose (Postgres + Grafana), schema.sql,
                         #   grafana/ provisioning + pqc_rag.json dashboard
docs/                    # ui-guide.md (how to use the Streamlit app)
images/                  # README screenshots (UI + Grafana)
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
- Monitoring: `docker compose -f monitoring/docker-compose.yml up -d`, then
  `export PQC_RAG_PG_DSN=postgresql://pqc:pqc@localhost:5432/pqc_rag` and run
  audits. Grafana at `http://localhost:3000` (dashboard "PQC Audit RAG";
  anonymous viewing, admin/admin). Needs the `monitoring` extra (`psycopg`).

## Current state — phases done

- **0–1** scaffold + RAG core.
- **2** automated ingestion (persistent LanceDB + dlt→DuckDB).
- **3** retrieval evaluation (dense/text/hybrid/rerank + query rewriting; Hit
  Rate/MRR over 269 LLM-generated questions). Winner `rerank`. → `RESULTS.md`.
- **4** LLM evaluation (3 prompt styles vs LLM-as-judge). Winner `concise`. +
  query-rewriting best practice. → `LLM_RESULTS.md`.
- **5** Streamlit UI + user feedback.
- **6** monitoring (Postgres + Grafana). `monitoring.py` persists every audit
  (`audit_run` + per-exposure `audit_exposure`) and feedback to Postgres,
  best-effort (no-op without `PQC_RAG_PG_DSN`; never breaks an audit). Pipeline
  now captures latency + token usage; `calc_cost` prices hosted models (local
  Ollama = $0). `feedback.py` writes Postgres when configured, JSONL otherwise.
  `monitoring/` ships `docker-compose.yml` (Postgres + Grafana), `schema.sql`,
  and a provisioned Grafana dashboard (`pqc_rag.json`, **11 panels / 7 charts**:
  audits over time, severity mix, feedback, tokens & cost, latency, method/prompt
  usage table, top algorithms). Verified end-to-end against the live stack.
- **LLM providers + robustness (post-phase-6, this session).** The synthesizer now
  works against local Ollama **and** any hosted OpenAI-compatible API. New
  `providers.py` (presets: local Ollama / Groq / OpenRouter / OpenAI / custom),
  wired into the Streamlit sidebar (provider selector + Base URL + model + masked
  API-key field that is never stored + `Advanced — TLS` + max-tokens slider) and
  the CLI (`--provider/--base-url/--api-key/--ca-bundle/--insecure`). Internal /
  self-signed gateways: `LLMSynthesizer(verify_tls=True|False|ca_path)` +
  `PQC_RAG_LLM_VERIFY`; needed because httpx/certifi doesn't trust a company's
  private CA (curl does) → surfaced as `Connection error`. Reply parsing is now
  robust (`_extract_payload`): handles fenced JSON, JSON embedded in prose, and
  **truncated** JSON (salvages summary + complete steps instead of dumping raw
  braces); on an empty `json_object` reply it retries without the format hint.
  Default `PQC_RAG_MAX_TOKENS` raised 300 → 700 (was truncating guidance).
  **Verified live by the user with a company LiteLLM gateway (private CA,
  `--insecure`) and with Groq** — both render clean summaries + steps.
- **Docs/README refresh (this session).** README corrected (was stale:
  sentence-transformers → ONNX embeddings; "Hosted LLM section" → provider
  selector; diagram feedback → Postgres/JSONL + a Monitoring node; env-var list +
  `PQC_RAG_LLM_VERIFY`; hosted CLI examples; two UI screenshots). New `docs/`
  folder: `ui-guide.md` (full sidebar walkthrough + hosted providers + TLS +
  troubleshooting), linked from the README.
- **CI / quality / security pipelines (this session).** `.github/workflows/`:
  `ci.yml` (ruff lint + format check, `pytest` on py3.10/3.11/3.12, build +
  `twine check`), `security.yml` (bandit, `pip-audit`, **CycloneDX SBOM** artifact,
  gitleaks), `codeql.yml`, `dependency-review.yml`; `.github/dependabot.yml`
  (weekly pip + actions). Ruff config in `pyproject.toml` (`[tool.ruff]`: curated
  select E/F/I/W/UP/B/C4, line-length 88 — deliberately NOT the pedantic style
  plugins, since monitoring uses intentional blind-except). Whole codebase
  `ruff format`-normalised once. Security fixes made to reach a clean scan: HF
  download pins `revision` (bandit B615); a justified `# nosec B608` on the
  parameterised SQL in `monitoring.py`; `.gitleaks.toml` allowlists the corpus
  (crypto identifiers like `sntrup761x25519-sha512` read as high-entropy secrets).
  All gates verified green locally before committing.

Rubric best practices covered: **hybrid search, re-ranking, query rewriting** (all
in `search.py`, all evaluated).

**Tests:** 48 offline (no Ollama/ONNX/network/DB). New this session:
`test_providers.py`, `test_tls.py`, `test_synthesis_parse.py` (incl. truncated-JSON
salvage), `test_monitoring.py`.

## Next steps

### Phase 7 — Containerization + reproducibility — DONE
- Root `docker-compose.yml`: app (Streamlit) + Postgres + Grafana + Ollama, one
  `docker compose up -d --build`. `Dockerfile` (python:3.12-slim, installs
  `.[app,local-embed,vector,llm,monitoring]`, bakes the ONNX model), `.dockerignore`,
  `Makefile` (`make help`), `uv.lock` (pinned deps). Grafana provisioning + schema
  reused from `monitoring/`. `ollama-pull` one-shot pulls the default model.
  **Verified:** whole stack healthy, an audit in the app container persisted to the
  containerized Postgres (Grafana reads it). NOTE: the ollama service port is NOT
  published (avoids clashing with a host Ollama on 11434); the app reaches it over
  the compose network. `monitoring/docker-compose.yml` stays as the monitoring-only
  stack.

### Phase 8 — Cloud deployment (bonus)
- Deploy (HF Spaces / Render / a VM). Document it.

## Gotchas / conventions

- **Ollama is slow on CPU.** Use `PQC_RAG_LLM=llama3.2:3b` and
  `PQC_RAG_MAX_TOKENS=280`; Offline mode needs no LLM. Ollama runs as a **systemd
  service** (`systemctl {status,stop} ollama`).
- **Eval scripts are slow** (LLM per item) — launch them in the background.
- **Restarting Streamlit:** kill by port, not `pkill -f "streamlit run"` — the
  pattern matches the launcher shell itself and self-kills. Use
  `kill $(ss -ltnp | grep :8501 | grep -oP 'pid=\K[0-9]+')`, then relaunch.
- **Hosted `Connection error`** on an internal endpoint = TLS: httpx/certifi
  doesn't trust the private CA (curl, using the system store, does). Fix with a CA
  bundle or `--insecure` / TLS-verify off (see the LLM-providers note above).
- **Ground truth** (`evaluation/ground_truth.json`) is LLM-generated and
  committed for reproducibility; regenerate with `generate_ground_truth.py`
  (`PQC_RAG_QPC` = questions/chunk).
- **Git**: commit as `rauleteee <raul22520@gmail.com>` — the repo-local git config
  is already set (the machine's global identity is different).
- **Real source PDFs** (NIST, CCN-STIC, BSI, ANSSI) are intentionally out of scope
  here; they belong to the separate `pqc-audit-pro` product.
- **Monitoring is best-effort.** All `monitoring.py` calls no-op (return
  `None`/`False`) without `PQC_RAG_PG_DSN` or if the DB is unreachable — an audit
  never fails because of the metrics store. `SCHEMA_SQL` (in `monitoring.py`) and
  `monitoring/schema.sql` are kept in sync by hand. Grafana panels use Postgres
  macros (`$__timeGroupAlias`, `$__timeFilter`); the datasource has `uid: pqc_pg`.
```
