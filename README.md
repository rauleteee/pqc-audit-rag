# PQC Audit RAG — post-quantum migration assistant

[![CI](https://github.com/rauleteee/pqc-audit-rag/actions/workflows/ci.yml/badge.svg)](https://github.com/rauleteee/pqc-audit-rag/actions/workflows/ci.yml)
[![Security](https://github.com/rauleteee/pqc-audit-rag/actions/workflows/security.yml/badge.svg)](https://github.com/rauleteee/pqc-audit-rag/actions/workflows/security.yml)
[![CodeQL](https://github.com/rauleteee/pqc-audit-rag/actions/workflows/codeql.yml/badge.svg)](https://github.com/rauleteee/pqc-audit-rag/actions/workflows/codeql.yml)

**▶️ Live demo: <https://pqc-audit-rag.streamlit.app>** — scan a public GitHub repo
(e.g. `https://github.com/paramiko/paramiko`) or upload your own.

A retrieval-augmented **agent that turns a cryptography inventory into an
actionable post-quantum (PQC) migration plan**. It scans a Python project for
quantum-vulnerable cryptography (RSA, ECC, DSA, Diffie-Hellman, Ed25519), then,
for each exposure, retrieves guidance from a curated knowledge base (NIST
standards, migration mappings, regulatory timelines) and an LLM synthesizes a
cited, per-finding migration recommendation.

![PQC Audit RAG scanning a public GitHub repo — verdict, severity chips and a cited ECDSA → ML-DSA migration plan](images/streamlit_github_scan.png)

Built for the **LLM Zoomcamp** final project. Runs on a **100% free, local
stack** by default (no paid API keys) — and can point at any hosted
OpenAI-compatible API (OpenAI, Groq, a company gateway…) when you want speed:

- **Detection:** [`pqc-audit`](https://pypi.org/project/pqc-audit/) (OSS engine).
- **LLM:** [Ollama](https://ollama.com) (local, free) by default, or any hosted
  OpenAI-compatible endpoint.
- **Embeddings:** ONNX MiniLM (`onnxruntime` + `tokenizers`, `all-MiniLM-L6-v2`)
  — local, no torch, with a dependency-free hashing fallback so the package and
  tests run offline.
- **Vector store:** LanceDB (on-disk) / in-memory.

## The problem

Regulators (US CNSA 2.0 / OMB, EU BSI/ANSSI) are pushing a migration to
post-quantum cryptography with deadlines through 2030–2035. The bottleneck is
visibility and *knowing what to do next*: "you can't migrate what you can't
see", and once you see it you still need per-primitive migration guidance. This
app closes that loop — inventory → retrieved guidance → concrete migration plan.

## Status

Complete and live. **Phases 0–8 done:** RAG core (scan → group exposures →
retrieve → synthesize → report), automated ingestion, retrieval + LLM evaluation,
a Streamlit UI (scan an example, a public GitHub repo, or an upload), a
Postgres + Grafana monitoring stack, a full docker-compose deployment, CI/security
pipelines, and a **live cloud demo** (<https://pqc-audit-rag.streamlit.app>). See
the roadmap below.

## Architecture

```mermaid
flowchart TB
    subgraph interfaces["Interfaces"]
        cli["CLI"]
        ui["Web UI<br/>(Streamlit)"]
    end

    orch["Orchestrator<br/>(run_audit)"]
    engine["Detection engine<br/>(pqc-audit)"]
    report["Report<br/>(Markdown / HTML)"]
    feedback["Feedback store<br/>(Postgres / JSONL)"]
    monitor["Monitoring<br/>(Postgres + Grafana)"]

    subgraph rag["Retrieval-augmented generation"]
        retriever["Retriever<br/>(hybrid + rerank + rewrite)"]
        synth["LLM synthesizer"]
    end

    llm["LLM runtime<br/>(Ollama or any<br/>OpenAI-compatible API)"]

    subgraph kbase["Knowledge base"]
        corpus["Corpus<br/>(Markdown + sources)"]
        ingest["Ingestion<br/>(chunking)"]
        embed["Embeddings<br/>(ONNX MiniLM)"]
        vstore["Vector store<br/>(LanceDB)"]
        kindex["Keyword index<br/>(minsearch)"]
    end

    evalz["Evaluation<br/>(retrieval + LLM-as-judge)"]

    cli --> orch
    ui --> orch
    ui --> feedback
    orch --> engine
    orch --> retriever
    orch --> synth
    orch --> report
    orch --> monitor
    feedback --> monitor
    retriever --> vstore
    retriever --> kindex
    synth --> llm
    corpus --> ingest
    ingest --> embed
    embed --> vstore
    ingest --> kindex
    evalz -.-> retriever
    evalz -.-> synth

    classDef iface fill:#eaf2fb,stroke:#2f6fb0,color:#12395c;
    classDef kbc fill:#eef7ee,stroke:#2e7d32,color:#14471a;
    classDef llmc fill:#fdf0e6,stroke:#c77800,color:#5c3a00;
    classDef evalc fill:#f4eef9,stroke:#7a4fb5,color:#3a2159;
    classDef monc fill:#fdeaea,stroke:#c0392b,color:#5c1a1a;
    class cli,ui iface;
    class corpus,ingest,embed,vstore,kindex kbc;
    class llm,synth llmc;
    class evalz evalc;
    class monitor monc;
```

**Components**

| Component | Implementation |
|---|---|
| CLI / Web UI | `pqc-audit-rag` command · a Streamlit app |
| Orchestrator | `run_audit()` — deterministic scan → group → retrieve → synthesize → report |
| Detection engine | `pqc-audit` (OSS), static AST scan — consumed as a dependency, not reimplemented |
| Retriever | hybrid search (RRF of vector + keyword) + re-ranking + query rewriting |
| Corpus | curated Markdown with source references (NIST, CNSA 2.0, …) |
| Ingestion | chunk the corpus by section |
| Embeddings | ONNX MiniLM (`all-MiniLM-L6-v2`) — local, no torch |
| Vector store | LanceDB (on-disk) or in-memory |
| Keyword index | minsearch |
| LLM synthesizer | writes the cited migration plan grounded in retrieved passages; robust reply parsing (fenced / embedded / truncated JSON) |
| LLM runtime | Ollama (default `llama3.1`) **or** any hosted OpenAI-compatible API (OpenAI, Groq, OpenRouter, a company gateway) |
| LLM provider | preset selector in `providers.py` (base URL + model) with a TLS-verify option for private-CA / self-signed gateways |
| Report | Markdown / HTML |
| Feedback store | thumbs up/down persisted to Postgres (JSONL fallback) |
| Monitoring | Postgres metrics store + provisioned Grafana dashboard |
| Evaluation | retrieval (Hit Rate / MRR) + LLM-as-judge (faithfulness / actionability) |

The LLM only synthesizes prose; the control flow is deterministic code.

## Quickstart

Prerequisites: **Python 3.12** (via [uv](https://docs.astral.sh/uv/)) and
**[Ollama](https://ollama.com)** for the local LLM.

```bash
# 1. Install Ollama (the local, free LLM runtime) and pull a model.
#    The installer starts the ollama service on http://localhost:11434.
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.1            # good quality; or a lighter/faster model on CPU:
# ollama pull llama3.2:3b

# 2. Python environment.
uv venv --python 3.12 && source .venv/bin/activate
uv pip install -e ".[dev,local-embed,vector,llm]"

# 3. Download the local ONNX embedding model (once, ~90 MB).
python -m pqc_audit_rag.knowledge_base.download_model

# 4a. Launch the web UI — pick a bundled example or point it at your own project.
streamlit run app/streamlit_app.py        # http://localhost:8501

# 4b. ...or use the CLI.
pqc-audit-rag audit ./path/to/project --md
```

### Run the whole stack with Docker

One command brings up the app, Postgres, Grafana **and** a local Ollama (the model
is pulled automatically on first start):

```bash
docker compose up -d --build     # or: make up
#   app      -> http://localhost:8501   (Streamlit UI)
#   grafana  -> http://localhost:3000   (dashboard "PQC Audit RAG", admin/admin)
# audits + feedback are persisted to Postgres and show up in Grafana.
docker compose down              # stop  (make down)   ·   -v to wipe data (make clean)
```

`make help` lists the common tasks (venv, test, lint, security/SBOM, up/down).
A fixed Python base image plus resolved dependencies keep installs reproducible.
The monitoring-only
stack still lives in `monitoring/docker-compose.yml`.

The UI can scan a **bundled example**, a **public GitHub repo** (by URL), an
**uploaded `.zip`/`.py`**, or a **local path** (when run on your own machine) —
plus a verdict banner, severity chips,
per-exposure cards with cited migration guidance, live progress, and 👍/👎
feedback. **Offline mode** in the sidebar runs everything except the LLM (instant,
no Ollama needed). The **LLM provider** selector switches between local Ollama and
a hosted OpenAI-compatible API (see below).

**New to the UI?** See the **[UI guide](docs/ui-guide.md)** — every sidebar
control, running an audit, reading the report, hosted providers and TLS, and
troubleshooting.

Same app, two backends — a local Ollama model, and a hosted Groq model returning a
fuller cited migration plan:

![PQC Audit RAG UI with the local Ollama provider — verdict, severity chips and a cited RSA-2048 recommendation](images/streamlit_ui.png)

![PQC Audit RAG UI with the Groq hosted provider — masked API key and a detailed ML-KEM / ML-DSA migration plan](images/streamlit_groq.png)

### Why is it slow? (and how to speed it up)

By default the LLM runs **locally on CPU** via Ollama — free and private, but
slow. In the monitoring screenshots a full scan of the kitchen-sink example took
~3 minutes. The latency comes entirely from LLM token generation, not from the
scan or retrieval (those are milliseconds):

- **CPU-only inference.** With no GPU, every generated token is CPU matrix math.
  A GPU (Ollama uses it automatically) is an order of magnitude faster.
- **One synthesis call per exposure, run sequentially.** A repo with many
  distinct exposures makes many LLM calls back-to-back.
- **Output length and model size.** Each call generates up to
  `PQC_RAG_MAX_TOKENS` tokens; an 8B model (`llama3.1`) is slower than a 3B one
  (`llama3.2:3b`).

Ways to make it fast:

```bash
# Smaller model + shorter output (still local & free):
PQC_RAG_LLM=llama3.2:3b PQC_RAG_MAX_TOKENS=280 streamlit run app/streamlit_app.py
# ...or Offline mode in the sidebar — deterministic, instant, no LLM at all.
```

### Using a hosted LLM instead of local Ollama

The synthesizer talks to **any OpenAI-compatible endpoint**, so you can swap the
free local Ollama for a hosted API (OpenAI, Groq, OpenRouter, a company gateway…) —
much faster than CPU inference — with no code change.

**In the UI:** the sidebar **LLM provider** selector offers *Local Ollama*, *Groq*,
*OpenRouter*, *OpenAI* and *Custom*; picking one fills the **Base URL** and a
default **model**, and reveals a masked **API key** field (used only for the
request, never stored). Screenshots above show the local Ollama and Groq runs.

**On the CLI:** use `--provider` (or `--base-url`) plus `--api-key`:

```bash
# Groq (free) — get a key at https://console.groq.com/keys
pqc-audit-rag audit examples/vulnerable_sample.py \
  --provider groq --api-key "$GROQ_API_KEY" --md

# OpenAI
pqc-audit-rag audit examples/vulnerable_sample.py \
  --provider openai --model gpt-4o-mini --api-key "$OPENAI_API_KEY" --md

# ...or via env vars, for any OpenAI-compatible endpoint:
export OPENAI_BASE_URL=https://api.openai.com/v1
export OPENAI_API_KEY=sk-...
export PQC_RAG_LLM=gpt-4o-mini
pqc-audit-rag audit examples/vulnerable_sample.py --md
```

Hosted models have a known per-token price, so the monitoring **cost** panel fills
in (see `PRICES` / `calc_cost` in `monitoring.py`; `gpt-4o-mini`, `gpt-4o`,
`gpt-4.1`… are priced, local/unknown models read $0).

**Internal / self-signed gateways.** If your company endpoint uses a private CA,
verification will fail (`Connection error`). Point at the company CA bundle
(secure) or disable verification (trusted internal endpoints only): in the UI use
the sidebar **Advanced — TLS** section; on the CLI use `--ca-bundle /path/ca.pem`
or `--insecure`; or set `PQC_RAG_LLM_VERIFY=false` (or a CA path).

Key environment variables: `OPENAI_BASE_URL` (default `http://localhost:11434/v1`),
`OPENAI_API_KEY` (default `ollama`), `PQC_RAG_LLM`, `PQC_RAG_MAX_TOKENS`
(default `700`), `PQC_RAG_LLM_VERIFY` (`true` | `false` | CA-bundle path),
`PQC_RAG_RETRIEVAL` (dense|text|hybrid|rerank), `PQC_RAG_PROMPT`, `PQC_RAG_TOPK`,
`PQC_RAG_PG_DSN` (Postgres DSN for monitoring; unset = disabled).

Run the tests (no Ollama / no ONNX / no network — uses offline fallbacks):

```bash
uv pip install -e ".[dev]"
pytest -q
```

## Retrieval evaluation

Four retrieval strategies are evaluated against a ground-truth question set
(`evaluation/ground_truth.json`) with **Hit Rate** and **MRR**; the best is wired
as the default. Reproduce with `python evaluation/evaluate_retrieval.py` (writes
`evaluation/RESULTS.md`). Latest run (**269 LLM-generated questions** over a
45-chunk corpus, k=4, ONNX embeddings):

| Method | Hit Rate | MRR |
|---|---|---|
| dense (vector) | 0.822 | 0.686 |
| text (minsearch) | 0.758 | 0.595 |
| hybrid (RRF) | 0.840 | 0.679 |
| **hybrid + rerank — best (MRR)** | 0.870 | **0.704** |
| rewrite + rerank | **0.877** | 0.695 |

The ground truth is generated with the LLM (`evaluation/generate_ground_truth.py`,
~6 questions/chunk), the course-aligned approach. **MRR** is the primary metric
(ranking quality). The full pipeline — hybrid search (Reciprocal Rank Fusion of
dense + keyword) **plus** re-ranking — wins on MRR, and the re-ranker clearly
helps (0.704 > 0.679). **Query rewriting** (acronym expansion) was also evaluated:
it gives the best Hit Rate (0.877) but slightly lower MRR, so `rerank` stays the
default. All three best practices (hybrid, re-ranking, query rewriting) live in
`search.py`; `PQC_RAG_RETRIEVAL` / the UI selector switch strategy.

## LLM evaluation

Three synthesis prompt styles (concise / detailed / checklist) are compared with an
**LLM-as-judge** (`evaluation/evaluate_llm.py`, writes `LLM_RESULTS.md`): the judge
scores each recommendation for **faithfulness** (grounded in the retrieved context)
and **actionability** (concrete, correct steps), 1–5, over the sample's 6 exposures.
Latest run (judge & synthesizer = llama3.1):

| Prompt style | Faithfulness | Actionability | Overall |
|---|---|---|---|
| **concise — best** | 5.00 | 4.17 | **4.58** |
| detailed | 4.83 | 4.17 | 4.50 |
| checklist | 4.83 | 4.17 | 4.50 |

Margins are small (all three are solid); `concise` edges ahead on faithfulness and
is the default (`PQC_RAG_PROMPT`).

## Monitoring (Postgres + Grafana)

Every audit is persisted to **Postgres** (`audit_run` + a per-exposure
`audit_exposure` table) together with the retrieval method, prompt style,
synthesizer, latency, token usage and estimated cost; 👍/👎 feedback goes to a
`feedback` table linked to the run. A provisioned **Grafana** dashboard reads it —
**7 charts** plus 4 stat tiles: audits over time, severity mix, feedback split,
tokens & estimated cost, latency, a usage-by-method/prompt table, and top exposed
algorithms.

![Grafana dashboard — stat tiles, audits over time, severity mix, user feedback, tokens & cost, latency](images/grafana1.png)

![Grafana dashboard — usage by retrieval method/prompt and top exposed algorithms](images/grafana2.png)

The screenshots above are a live run: 18 audits (6 with real `llama3.2:3b`
synthesis, ~13.7k tokens) over the bundled examples. Cost reads $0 because the
model is local; latency is high because it is CPU-only LLM inference — the honest
behaviour of the free stack.

```bash
# Bring up the metrics stack (Postgres + Grafana, dashboard auto-provisioned).
docker compose -f monitoring/docker-compose.yml up -d

# Point the app at Postgres and run audits (CLI or Streamlit).
uv pip install -e ".[monitoring]"
export PQC_RAG_PG_DSN=postgresql://pqc:pqc@localhost:5432/pqc_rag
pqc-audit-rag audit examples/vulnerable_sample.py --offline >/dev/null

# Open Grafana → dashboard "PQC Audit RAG".
open http://localhost:3000        # anonymous viewing; admin login is admin/admin
```

Monitoring is **best-effort**: with no `PQC_RAG_PG_DSN` (the default free stack)
every call is a no-op and feedback falls back to a local JSONL file — an audit
never fails because the metrics store is down. Cost is $0 for local Ollama models
and priced per-token for hosted OpenAI-compatible models (`calc_cost`).

## Evaluation criteria map (LLM Zoomcamp)

This section is filled in as each phase lands, so reviewers can find the
relevant code quickly.

| Criterion | Where | Status |
|---|---|---|
| Problem description | this README | ✅ |
| Retrieval flow (KB + LLM) | `retrieval.py`, `synthesis.py`, `pipeline.py` | ✅ |
| Retrieval evaluation | `evaluation/evaluate_retrieval.py`, `RESULTS.md` (4 methods) | ✅ |
| LLM evaluation | `evaluation/evaluate_llm.py`, `LLM_RESULTS.md` (3 prompts, judge) | ✅ |
| Interface | `app/streamlit_app.py` (Streamlit UI) | ✅ |
| Ingestion pipeline | `knowledge_base/ingest.py` (LanceDB) + `ingestion/dlt_pipeline.py` (dlt→DuckDB) | ✅ (automated) |
| Monitoring | `monitoring.py` (Postgres) + Grafana dashboard (`monitoring/`, 7 charts) + user feedback | ✅ |
| Containerization | `docker-compose.yml` — app + Postgres + Grafana + Ollama; `Dockerfile`, `Makefile` | ✅ |
| Reproducibility | this README, `Dockerfile` base image, `docker compose up` | ✅ |
| Best practices: hybrid search + re-ranking | `search.py`, `evaluation/RESULTS.md` | ✅ |
| Best practices: query rewriting | `search.py` (heuristic + LLM), `RESULTS.md` | ✅ |
| Cloud deployment (bonus) | live demo on Streamlit Cloud (<https://pqc-audit-rag.streamlit.app>); `deploy/` guide + configs | ✅ |

## Roadmap

0. ✅ Repo scaffold + packaging.
1. ✅ RAG core (scan → group → retrieve → synthesize → report) + public corpus.
2. ✅ Automated ingestion pipeline (chunking + embeddings + persistent LanceDB;
   plus a dlt→DuckDB pipeline, course-aligned).
3. ✅ Retrieval evaluation (dense vs text vs hybrid/RRF vs re-ranking; Hit
   Rate/MRR over a 45-chunk corpus, 269 LLM-generated questions). Winner
   (hybrid + rerank) is the default.
4. ✅ LLM evaluation (3 prompt styles compared with an LLM-as-judge) + query
   rewriting best practice.
5. ✅ Streamlit UI + user feedback.
6. ✅ Monitoring (Postgres + Grafana, 7 charts) — see below.
7. ✅ Containerization: `docker compose up` runs app + Postgres + Grafana + Ollama;
   `Dockerfile`, `Makefile` for reproducibility.
8. ✅ Cloud deployment (bonus): **live on Streamlit Community Cloud**
   (<https://pqc-audit-rag.streamlit.app>), using a hosted LLM (Groq, free). See
   [`deploy/`](deploy/README.md) for the guide and other options.

## Continuous integration & security

GitHub Actions run on every push and pull request (see `.github/workflows/`):

| Workflow | What it does |
|---|---|
| **CI** (`ci.yml`) | Ruff lint + format check; `pytest` on Python 3.10 / 3.11 / 3.12; build the sdist + wheel and `twine check` them. |
| **Security** (`security.yml`) | Bandit static analysis; `pip-audit` dependency-vulnerability scan; **CycloneDX SBOM** generation (uploaded as an artifact); gitleaks secret scan. |
| **CodeQL** (`codeql.yml`) | GitHub CodeQL (`security-extended`) for Python. |
| **Dependency review** (`dependency-review.yml`) | Flags vulnerable / disallowed-license dependencies added in a PR. |
| **Dependabot** (`dependabot.yml`) | Weekly `pip` + `github-actions` update PRs. |

Lint/format config lives in `pyproject.toml` (`[tool.ruff]`); the corpus is
allowlisted for secret scanning in `.gitleaks.toml` (crypto algorithm names such
as `sntrup761x25519-sha512` read as high-entropy secrets but are documentation).

## License

MIT. Built on the MIT-licensed `pqc-audit` engine.
