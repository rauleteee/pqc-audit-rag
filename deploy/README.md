# Cloud deployment

The full local stack (Ollama + Postgres + Grafana + app) is heavy for a free tier.
For the cloud we deploy **the app** and use a **hosted LLM** (Groq has a free tier)
instead of local Ollama. Monitoring (Postgres + Grafana) is optional in the cloud —
without `PQC_RAG_PG_DSN` it's a no-op, and feedback falls back to JSONL.

## Recommended: Hugging Face Spaces (Docker)

Reuses the repo's `Dockerfile` (it already handles the src-layout install and bakes
the ONNX embedding model), so the Space builds with no extra work.

1. Create a **new Space** → SDK **Docker** → **Blank**.
2. Put this repo's contents in the Space (link the GitHub repo, or push a copy).
3. Set the Space's `README.md` to the front-matter in
   [`huggingface/README.md`](huggingface/README.md) (declares `app_port: 8501`).
4. In **Settings → Variables and secrets**, add (so the UI defaults to Groq):
   - `OPENAI_BASE_URL = https://api.groq.com/openai/v1`
   - `OPENAI_API_KEY = <your Groq key>`  *(secret)* — from <https://console.groq.com/keys>
   - `PQC_RAG_LLM = llama-3.3-70b-versatile`
5. The Space builds and serves the Streamlit UI. Users can also switch provider or
   use **Offline** mode in the sidebar.

> The web UI only scans the bundled `examples/` in a hosted deploy (path traversal
> is blocked by design — see `SECURITY.md`).
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
