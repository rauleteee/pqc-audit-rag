# Using the PQC Audit RAG web UI

A step-by-step guide to the Streamlit app: scan a Python project for
quantum-vulnerable cryptography and read a cited, per-finding post-quantum
migration plan.

For install/setup see the [README Quickstart](../README.md#quickstart). This guide
assumes the app is already running.

---

## 1. Launch the app

```bash
# from the repo root, with the venv active
streamlit run app/streamlit_app.py        # opens http://localhost:8501
```

To also record each run for the Grafana dashboard, start it with a Postgres DSN
(optional — see [Monitoring](#7-monitoring-optional)):

```bash
export PQC_RAG_PG_DSN=postgresql://pqc:pqc@localhost:5432/pqc_rag
streamlit run app/streamlit_app.py
```

---

## 2. The sidebar, control by control

Everything you configure lives in the left sidebar; the report renders on the
right after you click **Run audit**.

| Control | What it does |
|---|---|
| **Example project** | Pick one of the bundled sample projects, or `Custom path…` to scan any file/folder on disk. A one-line description shows what each example contains. |
| **Project path** *(Custom only)* | The file or directory to scan (e.g. `examples/vulnerable_sample.py` or `~/code/myapp`). |
| **Synthesis** | `LLM` calls a model to write the guidance; `Offline (deterministic)` writes it from templates — instant, no model needed (great for a quick preview). |
| **LLM provider** | `Local Ollama` (free, on-device), `Groq` / `OpenRouter` / `OpenAI` (hosted APIs), or `Custom` (any OpenAI-compatible endpoint). Picking one fills the Base URL + a default model. |
| **Base URL** | The OpenAI-compatible endpoint (usually ends in `/v1`). Prefilled from the provider; edit it for a custom gateway. |
| **LLM model** | The model name the endpoint serves (e.g. `llama3.2:3b`, `llama-3.3-70b-versatile`, `gpt-4o-mini`). |
| **API key** | Needed for hosted providers. **Masked** (dots) and kept only in the browser session — never written to disk, DB or logs. Leave blank for local Ollama. |
| **Advanced — TLS** | For internal / self-signed endpoints: give a **CA bundle path** (secure) or tick **Disable TLS certificate verification** (trusted internal endpoints only). |
| **Retrieval method** | `rerank` (default, best in evaluation) / `hybrid` / `dense` / `text`. |
| **Retrieved passages (top-k)** | How many knowledge-base chunks to feed the model per exposure (default 4). |
| **Max output tokens** | Length cap for the LLM answer. Higher = fuller steps but slower; too low truncates the guidance. |
| **Run audit** | Runs the pipeline and renders the report. |

---

## 3. Run an audit (local, free)

1. **Synthesis** → `LLM`
2. **LLM provider** → `Local Ollama (free, on-device)`
3. Leave **Base URL** (`http://localhost:11434/v1`) and set **LLM model** to one
   you've pulled (e.g. `llama3.2:3b` for speed).
4. Click **Run audit**.

> On CPU this takes a few seconds per finding — the progress panel shows each
> step. For an instant preview with no model, use **Offline** mode.

![The UI with the local Ollama provider — verdict, severity chips and a cited RSA-2048 recommendation](../images/streamlit_ui.png)

---

## 4. Read the report

- **Verdict banner** — the one-line headline (e.g. *quantum-critical cryptography
  in use — migration needed*).
- **Severity chips** — counts of `CRITICAL` (broken by Shor), `MEDIUM` (weakened
  by Grover), `INFO` (already post-quantum), and the total.
- **Per-exposure cards** — one per distinct exposure: the algorithm, its usage,
  and the suggested **migration target** (e.g. `RSA-2048 — key generation →
  ML-KEM / ML-DSA`), followed by the LLM's **summary** and concrete **steps**.
- **Sources** — the knowledge-base passages each recommendation is grounded in
  (NIST FIPS 203/204/205, CNSA 2.0, etc.), so the guidance is auditable.

---

## 5. Give feedback

Under the report, **👍 Helpful** / **👎 Not useful** records your rating (to
Postgres if monitoring is on, otherwise a local JSONL file). It feeds the
feedback chart in Grafana.

---

## 6. Use a hosted provider (faster)

Hosted APIs are far faster than CPU inference. Example with **Groq** (free, no
card):

1. Get a key at <https://console.groq.com/keys>.
2. **LLM provider** → `Groq (free hosted API)` (fills Base URL + model).
3. Paste your key into **API key**.
4. **Run audit** — synthesis now takes seconds.

The same flow works for **OpenAI** (priced — the Grafana **cost** panel then shows
real spend) and **OpenRouter**.

![The UI with the Groq hosted provider — masked API key and a detailed ML-KEM / ML-DSA migration plan](../images/streamlit_groq.png)

### Internal / self-signed company endpoint

If your gateway uses a private CA you'll get a `Connection error` (TLS
verification fails). Open **Advanced — TLS** and either:

- paste your company **CA bundle path** (keeps verification on — preferred), or
- tick **Disable TLS certificate verification** (only for a trusted internal
  endpoint).

---

## 7. Monitoring (optional)

If you launched the app with `PQC_RAG_PG_DSN` set and the stack up
(`docker compose -f monitoring/docker-compose.yml up -d`), every audit and every
👍/👎 lands in Postgres and shows on the Grafana dashboard at
<http://localhost:3000> (dashboard **PQC Audit RAG**). See the
[Monitoring section of the README](../README.md#monitoring-postgres--grafana).

---

## 8. Troubleshooting

| Symptom | Cause & fix |
|---|---|
| **`Connection error`** with a hosted URL | TLS against a private CA. Use **Advanced — TLS** → CA bundle path, or disable verification. |
| **`Connection error`** with local Ollama | Ollama isn't running / model not pulled. `ollama pull llama3.2:3b`, or switch to **Offline**. |
| **401 / authentication error** | Missing or wrong **API key** for the hosted provider. |
| **Empty or raw-JSON guidance** | Very short **Max output tokens** truncated the reply — raise the slider. The parser salvages truncated JSON, but more tokens give complete steps. |
| **Very slow** | CPU LLM inference. Use a smaller model (`llama3.2:3b`), lower **Max output tokens**, a hosted provider, or **Offline** mode. |
| **Model not found** | The **LLM model** name doesn't match one the endpoint serves. Check the provider's model list. |
