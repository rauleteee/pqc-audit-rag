# PQC Audit RAG — common tasks. `make help` lists them.
.DEFAULT_GOAL := help
COMPOSE := docker compose
PY := .venv/bin/python

.PHONY: help
help: ## Show this help
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | \
		awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

## --- Local dev ---
.PHONY: venv
venv: ## Create the venv and install all extras (uv)
	uv venv --python 3.12
	VIRTUAL_ENV=.venv uv pip install -e ".[dev,app,local-embed,vector,llm,monitoring,ingest]"

.PHONY: model
model: ## Download the local ONNX embedding model
	$(PY) -m pqc_audit_rag.knowledge_base.download_model

.PHONY: test
test: ## Run the test suite (offline)
	$(PY) -m pytest -q

.PHONY: lint
lint: ## Ruff lint + format check
	uvx ruff check .
	uvx ruff format --check .

.PHONY: fmt
fmt: ## Apply ruff autofix + format
	uvx ruff check --fix .
	uvx ruff format .

.PHONY: security
security: ## Bandit + pip-audit + SBOM (local)
	uvx bandit -r src -ll
	uvx pip-audit
	uvx --from cyclonedx-bom cyclonedx-py environment .venv -o sbom.cdx.json --output-format JSON

.PHONY: ui
ui: ## Run the Streamlit UI locally
	$(PY) -m streamlit run app/streamlit_app.py

.PHONY: lock
lock: ## Regenerate the uv lockfile
	uv lock

## --- Docker (full stack) ---
.PHONY: up
up: ## Build + start the whole stack (app, postgres, grafana, ollama)
	$(COMPOSE) up -d --build

.PHONY: down
down: ## Stop the stack (keep volumes)
	$(COMPOSE) down

.PHONY: clean
clean: ## Stop the stack and remove volumes (deletes data)
	$(COMPOSE) down -v

.PHONY: logs
logs: ## Tail stack logs
	$(COMPOSE) logs -f

.PHONY: ps
ps: ## Show stack status
	$(COMPOSE) ps

.PHONY: monitoring
monitoring: ## Start only the monitoring stack (postgres + grafana)
	$(COMPOSE) -f monitoring/docker-compose.yml up -d
