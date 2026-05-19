# ============================================================
# SQA Knowledge Base — Makefile (dev cheatsheet)
# ============================================================
# En Windows: requiere `make` (Git Bash o `choco install make`).
# Alternativa: ver `scripts/dev.ps1` con comandos equivalentes.
# ============================================================

.PHONY: help install up down logs dev dev-frontend dev-backend test test-frontend test-backend lint typecheck build clean db-shell

help: ## Lista de comandos disponibles
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

install: ## Instala dependencias del frontend (pnpm) y backend (uv)
	pnpm install
	cd apps/backend && python -m pip install -e ".[dev]"

up: ## Arranca dependencias (Postgres, Azurite, Redis)
	docker compose up -d
	@echo "Postgres: localhost:5432  ·  Azurite: localhost:10000  ·  Redis: localhost:6379"

down: ## Detiene dependencias
	docker compose down

down-clean: ## Detiene y borra volúmenes (DB limpia)
	docker compose down -v

logs: ## Logs de todos los servicios
	docker compose logs -f

dev: up ## Up + frontend + backend (en este shell solo arranca el front; back aparte)
	@echo "→ docker compose up listo. Abrí dos terminales más:"
	@echo "    1) make dev-frontend"
	@echo "    2) make dev-backend"

dev-frontend: ## Arranca Next.js en localhost:3000
	pnpm --filter @sqa/frontend dev

dev-backend: ## Arranca FastAPI en localhost:8000
	cd apps/backend && uvicorn sqa_kb.main:app --reload --port 8000

test: test-frontend test-backend ## Todos los tests

test-frontend:
	pnpm --filter @sqa/frontend test

test-backend:
	cd apps/backend && pytest -q

lint: ## ESLint + ruff
	pnpm --filter @sqa/frontend lint
	cd apps/backend && ruff check .

typecheck: ## TypeScript + mypy (solo domain/ y agent/ en strict)
	pnpm --filter @sqa/frontend typecheck

build: ## Build de producción del frontend
	pnpm --filter @sqa/frontend build

db-shell: ## Abre psql contra la DB local
	docker compose exec postgres psql -U sqa -d sqa_kb

clean: ## Borra artefactos de build
	rm -rf apps/frontend/.next apps/frontend/node_modules
	rm -rf apps/backend/.venv apps/backend/.pytest_cache apps/backend/**/__pycache__
	rm -rf node_modules
