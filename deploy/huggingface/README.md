---
title: PQC Audit RAG
emoji: 🔐
colorFrom: indigo
colorTo: purple
sdk: docker
app_port: 8501
pinned: false
license: mit
---

# PQC Audit RAG

Scan a Python project for quantum-vulnerable cryptography and get a cited
post-quantum migration plan. Built on the OSS [`pqc-audit`](https://pypi.org/project/pqc-audit/)
engine with a RAG knowledge base.

This Space runs the Streamlit app from the repo's `Dockerfile`. Set an LLM provider
in **Settings → Variables and secrets** (e.g. Groq, free):

- `OPENAI_BASE_URL = https://api.groq.com/openai/v1`
- `OPENAI_API_KEY = <your Groq key>` (secret)
- `PQC_RAG_LLM = llama-3.3-70b-versatile`

Or use **Offline** mode in the sidebar (no LLM needed).

Source & docs: https://github.com/rauleteee/pqc-audit-rag
