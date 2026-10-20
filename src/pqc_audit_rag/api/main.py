import os
from contextlib import asynccontextmanager

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request

from pqc_audit_rag.api.runner import run_job
from pqc_audit_rag.api.schemas import AuditJob, AuditRequest
from pqc_audit_rag.api.store import InMemoryJobStore
from pqc_audit_rag.config import settings
from pqc_audit_rag.search import make_retriever
from pqc_audit_rag.synthesis import FakeSynthesizer, LLMSynthesizer
from pqc_audit_rag.version import __version__


def _default_synthesizer_factory():
    offline = os.environ.get("PQC_RAG_API_OFFLINE", "").lower()
    if offline in ("1", "true", "yes"):
        return FakeSynthesizer
    return LLMSynthesizer


def create_app(*, store=None, retriever=None, synthesizer_factory=None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.store = store if store is not None else InMemoryJobStore()
        app.state.retriever = (
            retriever
            if retriever is not None
            else make_retriever(settings.retrieval_method)
        )
        app.state.synthesizer_factory = (
            synthesizer_factory
            if synthesizer_factory is not None
            else _default_synthesizer_factory()
        )
        yield

    app = FastAPI(title="PQC Audit RAG API", version=__version__, lifespan=lifespan)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/audits", response_model=AuditJob, status_code=202)
    def create_audit(
        body: AuditRequest,
        background_tasks: BackgroundTasks,
        request: Request,
    ):
        state = request.app.state
        job = state.store.create(body.repo_url)
        background_tasks.add_task(
            run_job,
            job.id,
            state.store,
            retriever=state.retriever,
            synthesizer_factory=state.synthesizer_factory,
        )
        return job

    @app.get("/audits/{job_id}", response_model=AuditJob)
    def get_audit(job_id: str, request: Request):
        job = request.app.state.store.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Audit not found")
        return job

    return app


app = create_app()
