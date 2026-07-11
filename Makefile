.DEFAULT_GOAL := help

.PHONY: help build up down restart ps logs compose-check test-backend test-frontend build-frontend test smoke

help: ## Show the available operations commands without changing resources
	@awk 'BEGIN {FS = ":.*## "; printf "InsightFlow operations commands:\n"} /^[a-zA-Z0-9_-]+:.*## / {printf "  %-16s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

build: ## Build backend and frontend images with the normal BuildKit cache
	docker compose build

up: ## Start the Compose services in the background
	docker compose up -d

down: ## Stop services while preserving persistent volumes
	docker compose down

restart: ## Gracefully restart the Compose services
	docker compose restart

ps: ## Show Compose service status
	docker compose ps

logs: ## Follow backend and frontend logs
	docker compose logs -f backend frontend

compose-check: ## Validate Compose with an empty environment file
	docker compose --env-file /dev/null config -q

test-backend: ## Run the backend pytest suite
	python3 -m pytest

test-frontend: ## Run the frontend Vitest suite
	npm --prefix frontend test

build-frontend: ## Build the frontend production bundle
	npm --prefix frontend run build

test: test-backend test-frontend build-frontend ## Run backend and frontend verification

smoke: ## Run the isolated no-key Docker smoke acceptance
	bash scripts/docker_smoke_test.sh
