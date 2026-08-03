# Streamlit app image for PQC Audit RAG.
FROM python:3.12-slim

WORKDIR /app
ENV PIP_NO_CACHE_DIR=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Install the package first (better layer caching). src is needed for the
# dynamic version read at install time.
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --upgrade pip && \
    pip install -e ".[app,local-embed,vector,llm,monitoring]"

# Bake the local ONNX embedding model into the image (offline at runtime).
RUN python -m pqc_audit_rag.knowledge_base.download_model

COPY app ./app
COPY examples ./examples

EXPOSE 8501
HEALTHCHECK --interval=15s --timeout=5s --retries=10 \
  CMD python -c "import urllib.request;urllib.request.urlopen('http://localhost:8501/_stcore/health')" || exit 1

CMD ["streamlit", "run", "app/streamlit_app.py", \
     "--server.address=0.0.0.0", "--server.port=8501", \
     "--server.headless=true", "--browser.gatherUsageStats=false"]
