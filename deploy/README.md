# Cloud deployment

The full local stack (Ollama + Postgres + Grafana + app) is heavy for a free tier.
For the cloud we deploy **the app** and use a **hosted LLM** (Groq has a free tier)
instead of local Ollama. Monitoring (Postgres + Grafana) is optional in the cloud —
without `PQC_RAG_PG_DSN` it's a no-op, and feedback falls back to JSONL.

## Recommended (free): Streamlit Community Cloud

No Docker, no card. Uses the repo's `requirements.txt` (`.[app,llm]`) — a
lightweight install (hashing embedder + in-memory store, so no onnxruntime/lancedb).

1. Go to <https://share.streamlit.io> → **Create app** → **From existing repo**.
2. Repo `rauleteee/pqc-audit-rag`, branch `main`, main file `app/streamlit_app.py`.
3. **Advanced settings → Secrets**, add (so the UI defaults to Groq, free):
   ```toml
   OPENAI_BASE_URL = "https://api.groq.com/openai/v1"
   OPENAI_API_KEY  = "<your Groq key>"   # https://console.groq.com/keys
   PQC_RAG_LLM     = "llama-3.3-70b-versatile"
   ```
4. **Deploy**. Users can also switch provider or use **Offline** mode in the sidebar.

## Hugging Face Spaces (Docker) — needs a PRO account

Reuses the repo's `Dockerfile` (handles the src-layout install and bakes the ONNX
model). **Note:** Docker Spaces on `cpu-basic` now require HF **PRO** (free tier is
static-only).

1. Create a **new Space** → SDK **Docker**; put this repo's contents in it.
2. Set the Space `README.md` to [`huggingface/README.md`](huggingface/README.md)
   (declares `app_port: 8501`).
3. In **Settings → Variables and secrets** add the same Groq vars as above.

> In a hosted deploy, visitors scan their own code via **GitHub repo URL** (public,
> shallow-cloned server-side) or by **uploading a `.zip`/`.py`** — the server can't
> see their machine. Scanning an arbitrary server *path* is blocked by design (see
> `SECURITY.md`).
>
> If the platform has a read-only filesystem and 👎/👍 feedback errors, set
> `PQC_RAG_FEEDBACK=/tmp/feedback.jsonl` (a writable path) or configure
> `PQC_RAG_PG_DSN` so feedback goes to Postgres instead.

## Alternatives

- **Streamlit Community Cloud** — free, no Docker. Point it at the repo and
  `app/streamlit_app.py`; add the same Groq secrets under **App → Settings →
  Secrets**. (Installs from `pyproject.toml`.)
- **Render / Railway / Fly.io** — "Deploy from a Dockerfile" using the root
  `Dockerfile`; expose port `8501`; set the same env vars.

## Optional: monitoring in the cloud

To keep the Grafana dashboard in a hosted deploy, use managed services:

- **Postgres:** a free tier (Neon / Supabase). Set `PQC_RAG_PG_DSN` to its DSN as
  a Space secret — audits + feedback then persist.
- **Grafana:** Grafana Cloud (free) with a Postgres data source pointing at the
  same DB; import `monitoring/grafana/dashboards/pqc_rag.json`.
