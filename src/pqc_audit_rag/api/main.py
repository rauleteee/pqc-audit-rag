from fastapi import FastAPI

from pqc_audit_rag.version import __version__

app = FastAPI(title="PQC Audit RAG API", version=__version__)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
