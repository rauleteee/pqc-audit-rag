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
stack** by default (no paid keys); can use any hosted OpenAI-compatible API.

## The problem

Regulators (CNSA 2.0, BSI, ANSSI) push a migration to post-quantum crypto by
2030–2035. You can't migrate what you can't see, and once you see it you still
need per-algorithm guidance. This app closes the loop: **inventory → retrieved
guidance → concrete migration plan**.

## How it works

![Audit flow](images/flow.svg)

## Tech stack

![Tech stack](images/tech-stack.svg)

| Layer | Tech |
|---|---|
| Detection | [`pqc-audit`](https://pypi.org/project/pqc-audit/) (OSS, static AST scan) |
| Retrieval | ONNX MiniLM embeddings · LanceDB · minsearch · hybrid (RRF) + rerank + query rewriting |
| LLM | Ollama (local, free) or any OpenAI-compatible API (Groq, OpenAI, gateways) |
| Interfaces | Streamlit UI · CLI · FastAPI REST API |
| Async | Kafka queue + worker, job state in Postgres |
| Monitoring | Postgres + Grafana (7 charts), 👍/👎 feedback |
| Ops | Docker Compose, GitHub Actions (ruff, pytest, CodeQL, bandit, SBOM) |

## Quickstart

Prerequisites: Python 3.12 ([uv](https://docs.astral.sh/uv/)) and [Ollama](https://ollama.com).

```bash
ollama pull llama3.2:3b                        # or llama3.1 for quality
uv venv --python 3.12 && source .venv/bin/activate
uv pip install -e ".[dev,local-embed,vector,llm]"
python -m pqc_audit_rag.knowledge_base.download_model   # once, ~90 MB

streamlit run app/streamlit_app.py             # UI -> http://localhost:8501
pqc-audit-rag audit ./path/to/project --md     # or the CLI
pytest -q                                      # tests: fully offline
```

**Everything with Docker** (app, API, worker, Kafka, Postgres, Grafana, Ollama):

```bash
docker compose up -d --build     # make up   ·   docker compose down  (make down)
#  UI :8501 · API :8000/docs · Grafana :3000 (admin/admin)
```

![UI](images/streamlit_github_scan.png)

Hosted LLMs, TLS, env vars and speed tips: [docs/configuration.md](docs/configuration.md).
Every UI control: [docs/ui-guide.md](docs/ui-guide.md).

## REST API (sync or async)

```bash
uv pip install -e ".[api]"
PQC_RAG_API_OFFLINE=1 uvicorn pqc_audit_rag.api.main:app
curl -X POST localhost:8000/audits -H "Content-Type: application/json" \
  -d '{"repo_url": "https://github.com/paramiko/paramiko"}'    # -> 202 + job id
curl localhost:8000/audits/<id>                                 # queued|running|done|failed
```

| Endpoint | What it does |
|---|---|
| `POST /audits` | Start an audit of a public repo (`202` + job `id`) |
| `GET /audits/{id}` | Status and report |
| `GET /health` | Liveness |

With `PQC_RAG_KAFKA_BOOTSTRAP` set (the compose default) the API publishes each
job to Kafka and a **worker** runs it, storing status in Postgres (SQL migrations
in `src/pqc_audit_rag/migrations/`). Unset, jobs run in-process — no broker needed.

![Async mode](images/async-mode.svg)

## Evaluation

Reproduce with `python evaluation/evaluate_retrieval.py` / `evaluate_llm.py`
(need Ollama; details in `evaluation/RESULTS.md`, `LLM_RESULTS.md`).

| Retrieval (269 questions, k=4) | Hit Rate | MRR |
|---|---|---|
| dense | 0.822 | 0.686 |
| text | 0.758 | 0.595 |
| hybrid (RRF) | 0.840 | 0.679 |
| **hybrid + rerank (default)** | 0.870 | **0.704** |
| rewrite + rerank | **0.877** | 0.695 |

LLM-as-judge over 3 prompt styles: `concise` wins (faithfulness 5.00, actionability
4.17, overall 4.58) and is the default.

## Monitoring

Every audit (method, prompt, latency, tokens, cost) and every 👍/👎 goes to
Postgres; Grafana shows it. Best-effort: without `PQC_RAG_PG_DSN` it is a no-op.

```bash
docker compose -f monitoring/docker-compose.yml up -d
export PQC_RAG_PG_DSN=postgresql://pqc:pqc@localhost:5432/pqc_rag
```

![Grafana](images/grafana1.png)

## CI & security

GitHub Actions: ruff + pytest (3.10–3.12) + build, Kafka integration test,
bandit, pip-audit, CycloneDX SBOM, gitleaks, CodeQL, dependency review;
Dependabot weekly.

## Project status

Phases 0–8 done (RAG core, ingestion, evaluations, UI, monitoring, Docker, cloud
demo) plus the REST API and the async Kafka worker. Live demo:
<https://pqc-audit-rag.streamlit.app>. Deployment guide: [deploy/](deploy/README.md).

## License

MIT. Built on the MIT-licensed `pqc-audit` engine.
