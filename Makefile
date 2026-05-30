# Convenience targets. On Windows use `make` via Git Bash/WSL, or run the commands directly.
.PHONY: help db-up db-down backend-install backend-dev migrate test lint frontend-install frontend-dev up down

help:
	@echo "db-up            Start Postgres (pgvector) via docker compose"
	@echo "migrate          Apply Alembic migrations"
	@echo "backend-install  Install backend dev dependencies"
	@echo "backend-dev      Run the FastAPI dev server"
	@echo "test             Run backend tests"
	@echo "lint             Ruff lint the backend"
	@echo "frontend-install Install frontend dependencies"
	@echo "frontend-dev     Run the Next.js dev server"
	@echo "up / down        Start / stop the full docker compose stack"

db-up:
	docker compose up -d postgres

db-down:
	docker compose stop postgres

backend-install:
	cd backend && pip install -r requirements-dev.txt

migrate:
	cd backend && alembic upgrade head

backend-dev:
	cd backend && uvicorn app.main:app --reload

test:
	cd backend && pytest

lint:
	cd backend && ruff check .

frontend-install:
	cd frontend && npm install

frontend-dev:
	cd frontend && npm run dev

up:
	docker compose up --build

down:
	docker compose down
