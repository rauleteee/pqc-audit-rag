# Configuration & tuning

## Hosted LLM instead of local Ollama

The synthesizer talks to any OpenAI-compatible endpoint. In the UI use the
sidebar **LLM provider** selector (see the [UI guide](ui-guide.md)); on the CLI:

```bash
pqc-audit-rag audit examples/vulnerable_sample.py \
  --provider groq --api-key "$GROQ_API_KEY" --md          # free key: console.groq.com
pqc-audit-rag audit examples/vulnerable_sample.py \
  --provider openai --model gpt-4o-mini --api-key "$OPENAI_API_KEY" --md
```

Private-CA / self-signed gateway (`Connection error`): `--ca-bundle ca.pem`,
`--insecure`, or `PQC_RAG_LLM_VERIFY=false|/path/ca.pem`.

## Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `OPENAI_BASE_URL` | `http://localhost:11434/v1` | LLM endpoint |
| `OPENAI_API_KEY` | `ollama` | LLM key |
| `PQC_RAG_LLM` | `llama3.1` | model name |
| `PQC_RAG_MAX_TOKENS` | `700` | max output tokens |
| `PQC_RAG_LLM_VERIFY` | `true` | `true` / `false` / CA-bundle path |
| `PQC_RAG_RETRIEVAL` | `rerank` | `dense` / `text` / `hybrid` / `rerank` |
| `PQC_RAG_PROMPT` | `concise` | `concise` / `detailed` / `checklist` |
| `PQC_RAG_TOPK` | | passages per exposure |
| `PQC_RAG_PG_DSN` | unset | Postgres DSN for monitoring (unset = off) |
| `PQC_RAG_KAFKA_BOOTSTRAP` | unset | Kafka `host:port` (unset = API runs jobs in-process) |
| `PQC_RAG_KAFKA_TOPIC` | `audit.requested` | job topic |
| `PQC_RAG_API_OFFLINE` | | `1` = API skips the LLM |

## Why is it slow?

Local CPU inference: one LLM call per exposure, sequential. Scan and retrieval
take milliseconds. Speed up with a GPU, a smaller model
(`PQC_RAG_LLM=llama3.2:3b PQC_RAG_MAX_TOKENS=280`), a hosted provider, or
**Offline mode** (no LLM, instant).
