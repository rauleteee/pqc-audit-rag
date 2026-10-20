from collections.abc import Callable
from contextlib import asynccontextmanager

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request

from pqc_audit_rag.api.runner import default_synthesizer_factory, run_job
from pqc_audit_rag.api.schemas import AuditJob, AuditRequest, JobStatus
from pqc_audit_rag.api.store import InMemoryJobStore, JobStore
from pqc_audit_rag.config import settings
from pqc_audit_rag.errors import PublishError
from pqc_audit_rag.search import make_retriever
from pqc_audit_rag.version import __version__


def _default_store() -> JobStore:
    if not settings.kafka_bootstrap:
        return InMemoryJobStore()
    if not settings.pg_dsn:
        raise RuntimeError(
            "PQC_RAG_KAFKA_BOOTSTRAP needs PQC_RAG_PG_DSN: the worker shares "
            "job state with the API through Postgres"
        )
    from pqc_audit_rag.api.pg_store import PostgresJobStore
    from pqc_audit_rag.migrate import migrate

    migrate(settings.pg_dsn)
    return PostgresJobStore(settings.pg_dsn)


def _default_publisher() -> Callable[[str], None] | None:
    if not settings.kafka_bootstrap:
        return None
    from pqc_audit_rag.messaging import ensure_topic, make_producer, publish_job

    ensure_topic(settings.kafka_bootstrap, settings.kafka_topic)
    producer = make_producer(settings.kafka_bootstrap)

    def publish(job_id: str) -> None:
        publish_job(producer, settings.kafka_topic, job_id)

    return publish


def create_app(
    *, store=None, retriever=None, synthesizer_factory=None, publisher=None
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.store = store if store is not None else _default_store()
        app.state.publisher = (
            publisher if publisher is not None else _default_publisher()
        )
        app.state.retriever = (
            retriever
            if retriever is not None
            else make_retriever(settings.retrieval_method)
        )
        app.state.synthesizer_factory = (
            synthesizer_factory
            if synthesizer_factory is not None
            else default_synthesizer_factory()
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
        if state.publisher is None:
            background_tasks.add_task(
                run_job,
                job.id,
                state.store,
                retriever=state.retriever,
                synthesizer_factory=state.synthesizer_factory,
            )
        else:
            try:
                state.publisher(job.id)
            except PublishError as exc:
                state.store.update(
                    job.id,
                    status=JobStatus.failed,
                    error=f"Could not enqueue job: {exc}",
                )
                raise HTTPException(
                    status_code=503, detail="Job queue unavailable"
                ) from exc
        return job

    @app.get("/audits/{job_id}", response_model=AuditJob)
    def get_audit(job_id: str, request: Request):
        job = request.app.state.store.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Audit not found")
        return job

    return app


app = create_app()
