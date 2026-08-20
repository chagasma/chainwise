BACKEND_DIR := src/backend
FRONTEND_DIR := src/frontend
DOCKER_IMAGE := chainwise-backend:local

.DEFAULT_GOAL := help

.PHONY: help install dev backend frontend lint typecheck test check \
	docker-build docker-run docker-stop db-up db-down up down clean

help: ## Show available commands
	@grep -E '^[a-zA-Z_-]+:.*## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

install: ## Sync the backend virtualenv (uv) with the lockfile
	cd $(BACKEND_DIR) && uv sync

db-up: ## Start the local Postgres (used for LangGraph checkpoints)
	docker compose up -d postgres
	@until docker compose exec -T postgres pg_isready -U chainwise >/dev/null 2>&1; do sleep 1; done

db-down: ## Stop the local Postgres
	docker compose stop postgres

dev: install db-up ## Run backend (and frontend, if present) locally
	@trap 'kill 0' EXIT; \
	( cd $(BACKEND_DIR) && uv run uvicorn chainwise.main:app --reload --port 8000 ) & \
	if [ -f "$(FRONTEND_DIR)/package.json" ]; then \
		( cd $(FRONTEND_DIR) && npm run dev ) & \
	else \
		echo "-- frontend not implemented yet, running backend only --"; \
	fi; \
	wait

backend: install db-up ## Run only the backend, with reload
	cd $(BACKEND_DIR) && uv run uvicorn chainwise.main:app --reload --port 8000

lint: install ## Lint the backend with ruff
	cd $(BACKEND_DIR) && uv run ruff check .

typecheck: install ## Type-check the backend with pyright
	cd $(BACKEND_DIR) && uv run pyright

test: install ## Run backend tests
	cd $(BACKEND_DIR) && uv run pytest -q

check: lint typecheck test ## Run lint + typecheck + test

up: ## Run the full stack (Postgres + backend) via docker compose
	docker compose up --build backend

down: ## Stop the full stack started with `make up`
	docker compose down

docker-build: ## Build the optimized backend Docker image
	docker build -t $(DOCKER_IMAGE) $(BACKEND_DIR)

docker-run: docker-build ## Run the backend container on port 8000
	docker run --rm -p 8000:8000 --name chainwise-backend $(DOCKER_IMAGE)

docker-stop: ## Stop the running backend container
	docker stop chainwise-backend

clean: ## Remove the backend venv and caches
	rm -rf $(BACKEND_DIR)/.venv $(BACKEND_DIR)/.ruff_cache $(BACKEND_DIR)/.pytest_cache
	find $(BACKEND_DIR) -name "__pycache__" -type d -exec rm -rf {} +
