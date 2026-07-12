.DEFAULT_GOAL := help

.PHONY: help build up down restart ps logs compose-check observability-up observability-down observability-down-v observability-ps observability-logs observability-alert-tests observability-check observability-acceptance test-backend test-frontend build-frontend test smoke

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

observability-up: ## Start Prometheus and Grafana after checking the required local password
	@docker compose --profile observability config --format json | python3 -c 'import json,sys; value=json.load(sys.stdin)["services"]["grafana"]["environment"].get("GF_SECURITY_ADMIN_PASSWORD", ""); sys.exit(0 if value else "Set GRAFANA_ADMIN_PASSWORD in local .env or a deployment secret before observability-up.")'
	docker compose --profile observability up -d

observability-down: ## Stop the full profile while preserving all persistent volumes
	docker compose --profile observability down

observability-down-v: ## DANGER: delete only Prometheus/Grafana data volumes after stopping the profile
	docker compose --profile observability down
	@for volume in "$${COMPOSE_PROJECT_NAME:-insightflow}_prometheus-data" "$${COMPOSE_PROJECT_NAME:-insightflow}_grafana-data"; do \
		if docker volume inspect "$$volume" >/dev/null 2>&1; then docker volume rm "$$volume"; fi; \
	done

observability-ps: ## Show backend, frontend, Prometheus, and Grafana status
	docker compose --profile observability ps

observability-logs: ## Follow Prometheus and Grafana logs
	docker compose --profile observability logs -f prometheus grafana

observability-alert-tests: ## Evaluate all recording/alert rules with deterministic time series
	docker run --rm --entrypoint promtool --volume "$(CURDIR)/observability/alerts:/rules:ro" --volume "$(CURDIR)/observability/tests:/tests:ro" --workdir /rules prom/prometheus:v3.5.0 test rules /tests/rule-tests.yml

observability-check: observability-alert-tests ## Validate Compose, Prometheus config/rules/tests, Grafana provisioning, and dashboards
	docker compose --profile observability config -q
	docker run --rm --entrypoint promtool --volume "$(CURDIR)/observability/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro" --volume "$(CURDIR)/observability/alerts:/etc/prometheus/rules:ro" prom/prometheus:v3.5.0 check config /etc/prometheus/prometheus.yml
	docker run --rm --entrypoint promtool --volume "$(CURDIR)/observability/alerts:/rules:ro" prom/prometheus:v3.5.0 check rules /rules/recording-rules.yml /rules/alert-rules.yml
	python3 -m pytest -q tests/test_observability_stack.py

observability-acceptance: observability-check ## Run safe credential-free P38 failure, redaction, and cardinality acceptance
	python3 -m pytest -q tests/test_p38_failure_injection.py tests/test_observability_redaction.py tests/test_metrics_cardinality.py tests/test_http_observability.py tests/test_http_metrics.py tests/test_tool_metrics.py tests/test_workflow_metrics.py tests/test_trace_logger.py tests/test_trace_dashboard.py tests/test_feishu_publisher.py tests/test_workspace_report_api.py tests/test_workspace_analysis_runner.py::test_chart_generation_failure_does_not_block_business_answer

test-backend: ## Run the backend pytest suite
	python3 -m pytest

test-frontend: ## Run the frontend Vitest suite
	npm --prefix frontend test

build-frontend: ## Build the frontend production bundle
	npm --prefix frontend run build

test: test-backend test-frontend build-frontend ## Run backend and frontend verification

smoke: ## Run the isolated no-key Docker smoke acceptance
	bash scripts/docker_smoke_test.sh
