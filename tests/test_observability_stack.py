from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import yaml
from prometheus_client.parser import text_string_to_metric_families

from observability.metrics import create_metrics


ROOT = Path(__file__).resolve().parents[1]
COMPOSE = yaml.safe_load((ROOT / "compose.yaml").read_text(encoding="utf-8"))
OBSERVABILITY = ROOT / "observability"
REGISTERED_METRICS = {
    "insightflow_http_requests_total", "insightflow_http_request_duration_seconds_bucket",
    "insightflow_http_requests_in_progress", "insightflow_runs_total",
    "insightflow_run_duration_seconds_bucket", "insightflow_node_executions_total",
    "insightflow_node_duration_seconds_bucket", "insightflow_clarifications_total",
    "insightflow_retries_total", "insightflow_llm_requests_total",
    "insightflow_llm_duration_seconds_bucket", "insightflow_llm_tokens_total",
    "insightflow_llm_fallbacks_total", "insightflow_sql_validations_total",
    "insightflow_sql_executions_total", "insightflow_sql_duration_seconds_bucket",
    "insightflow_evidence_validations_total", "insightflow_evidence_tasks_total",
    "insightflow_chart_generations_total", "insightflow_report_generations_total",
    "insightflow_document_exports_total", "insightflow_external_publishes_total",
    "insightflow_external_publish_duration_seconds_bucket", "insightflow_runtime_storage_usage_ratio",
    "up",
}
RECORDING_RULES = {
    "insightflow:http_requests:rate5m", "insightflow:http_5xx_ratio:rate5m",
    "insightflow:http_p95_latency_seconds:rate5m", "insightflow:llm_error_ratio:rate10m",
    "insightflow:sql_execution_error_ratio:rate10m", "insightflow:evidence_failure_ratio:rate10m",
    "insightflow:external_publish_failure_ratio:rate10m",
}


def _mount_sources(service: dict) -> set[str]:
    return {mount.get("source") if isinstance(mount, dict) else mount.split(":", 1)[0] for mount in service.get("volumes", [])}


def _dashboard_files() -> list[Path]:
    return sorted((OBSERVABILITY / "grafana" / "dashboards").glob("*.json"))


def test_base_compose_selects_only_product_services_and_profile_selects_four():
    base = subprocess.check_output(["docker", "compose", "config", "--services"], cwd=ROOT, text=True).split()
    profiled = subprocess.check_output(["docker", "compose", "--profile", "observability", "config", "--services"], cwd=ROOT, text=True).split()
    assert set(base) == {"backend", "frontend"}
    assert set(profiled) == {"backend", "frontend", "prometheus", "grafana"}


def test_profile_security_ports_images_resources_and_volume_boundaries():
    services = COMPOSE["services"]
    for name in ("prometheus", "grafana"):
        service = services[name]
        assert service["profiles"] == ["observability"]
        assert service["ports"][0].startswith("127.0.0.1:")
        assert "latest" not in service["image"]
        assert service["mem_limit"] and service["cpus"]
        assert "container_name" not in service and service.get("privileged") is not True
        serialized = json.dumps(service["volumes"])
        assert "/var/run/docker.sock" not in serialized and "/Users/" not in serialized and ".env" not in serialized
    assert _mount_sources(services["prometheus"]) & {"workspace-data", "report-data", "trace-data"} == set()
    assert _mount_sources(services["grafana"]) & {"workspace-data", "report-data", "trace-data"} == set()
    assert _mount_sources(services["prometheus"]) >= {"prometheus-data"}
    assert _mount_sources(services["grafana"]) >= {"grafana-data"}


def test_grafana_password_has_no_default_and_base_compose_can_parse_without_it():
    grafana = COMPOSE["services"]["grafana"]
    assert grafana["environment"]["GF_SECURITY_ADMIN_PASSWORD"] == "${GRAFANA_ADMIN_PASSWORD:-}"
    assert grafana["environment"]["GF_AUTH_ANONYMOUS_ENABLED"] == "false"
    assert grafana["environment"]["GF_USERS_ALLOW_SIGN_UP"] == "false"
    env_example = (ROOT / ".env.example").read_text(encoding="utf-8")
    assert re.search(r"(?m)^GRAFANA_ADMIN_PASSWORD=$", env_example)
    subprocess.run(["docker", "compose", "--env-file", "/dev/null", "config", "--quiet"], cwd=ROOT, check=True)


def test_prometheus_config_and_rules_are_yaml_and_use_only_internal_targets():
    config = yaml.safe_load((OBSERVABILITY / "prometheus" / "prometheus.yml").read_text(encoding="utf-8"))
    assert config["global"] == {"scrape_interval": "15s", "evaluation_interval": "30s"}
    targets = [target for scrape in config["scrape_configs"] for static in scrape["static_configs"] for target in static["targets"]]
    assert "backend:8000" in targets and "127.0.0.1:9090" in targets
    assert all(not re.match(r"https?://", target) for target in targets)
    for path in (OBSERVABILITY / "alerts").glob("*.yml"):
        assert isinstance(yaml.safe_load(path.read_text(encoding="utf-8")), dict)


def test_grafana_provisioning_and_four_repository_dashboards_are_parseable():
    datasource = yaml.safe_load((OBSERVABILITY / "grafana" / "provisioning" / "datasources" / "prometheus.yml").read_text(encoding="utf-8"))["datasources"][0]
    assert datasource["uid"] == "prometheus" and datasource["url"] == "http://prometheus:9090" and datasource["isDefault"] is True
    provider = yaml.safe_load((OBSERVABILITY / "grafana" / "provisioning" / "dashboards" / "insightflow.yml").read_text(encoding="utf-8"))["providers"][0]
    assert provider["folder"] == "InsightFlow Observability" and provider["updateIntervalSeconds"] > 0
    dashboards = [json.loads(path.read_text(encoding="utf-8")) for path in _dashboard_files()]
    assert {item["title"] for item in dashboards} == {"System Health", "Analysis Workflow", "Provider And Tool", "Delivery"}
    for dashboard in dashboards:
        assert dashboard["uid"].startswith("insightflow-")
        for panel in dashboard["panels"]:
            assert panel["datasource"]["uid"] == "prometheus"


def test_dashboard_promql_references_only_registered_or_recorded_metrics_and_no_sensitive_labels():
    expressions = []
    for path in _dashboard_files():
        dashboard = json.loads(path.read_text(encoding="utf-8"))
        expressions.extend(target["expr"] for panel in dashboard["panels"] for target in panel["targets"])
    names = set(re.findall(r"(?<![\w:])(?:insightflow[:_][a-zA-Z0-9_:]+|up)(?![\w:])", "\n".join(expressions)))
    assert names <= REGISTERED_METRICS | RECORDING_RULES
    forbidden_labels = {"request_id", "run_id", "workspace_id", "report_id", "sql", "path", "prompt", "url", "exception"}
    assert not any(re.search(rf"\b{label}\s*=", "\n".join(expressions), re.I) for label in forbidden_labels)


def test_recording_and_alert_rule_contract():
    recording = yaml.safe_load((OBSERVABILITY / "alerts" / "recording-rules.yml").read_text(encoding="utf-8"))
    alerts = yaml.safe_load((OBSERVABILITY / "alerts" / "alert-rules.yml").read_text(encoding="utf-8"))
    assert {rule["record"] for group in recording["groups"] for rule in group["rules"]} == RECORDING_RULES
    rules = [rule for group in alerts["groups"] for rule in group["rules"]]
    assert {rule["alert"] for rule in rules} == {"BackendUnavailable", "HighHttp5xxRate", "HighApiLatency", "HighLlmFailureRate", "HighSqlFailureRate", "HighEvidenceFailureRate", "ExternalPublishFailureBurst", "RuntimeStorageHigh"}
    for rule in rules:
        assert rule["labels"]["severity"] in {"warning", "critical"}
        assert {"summary", "description", "dashboard", "runbook"} <= set(rule["annotations"])


def test_promtool_rule_test_fixture_covers_every_recording_rule_and_alert():
    fixture_path = OBSERVABILITY / "tests" / "rule-tests.yml"
    fixture = yaml.safe_load(fixture_path.read_text(encoding="utf-8"))
    serialized = fixture_path.read_text(encoding="utf-8")
    tested_alerts = {
        item["alertname"]
        for test in fixture["tests"]
        for item in test.get("alert_rule_test", [])
    }
    tested_expressions = {
        item["expr"]
        for test in fixture["tests"]
        for item in test.get("promql_expr_test", [])
    }
    assert tested_alerts == {
        "BackendUnavailable",
        "HighHttp5xxRate",
        "HighApiLatency",
        "HighLlmFailureRate",
        "HighSqlFailureRate",
        "HighEvidenceFailureRate",
        "ExternalPublishFailureBurst",
        "RuntimeStorageHigh",
    }
    assert RECORDING_RULES <= tested_expressions
    assert any(not item.get("exp_alerts") for test in fixture["tests"] for item in test.get("alert_rule_test", []))
    for forbidden in ("request_id", "run_id", "workspace_id", "SELECT ", "Bearer ", "/Users/", "provider_payload"):
        assert forbidden not in serialized


def test_runtime_storage_gauge_is_label_free_and_statvfs_failure_isolated(tmp_path, monkeypatch):
    metrics = create_metrics(storage_path=tmp_path)
    text = metrics.exposition().decode()
    sample = next(sample for family in text_string_to_metric_families(text) for sample in family.samples if sample.name == "insightflow_runtime_storage_usage_ratio")
    assert sample.labels == {} and 0 <= sample.value <= 1
    monkeypatch.setattr("observability.metrics.os.statvfs", lambda _path: (_ for _ in ()).throw(OSError("private-path")))
    assert b"insightflow_runtime_storage_usage_ratio" in metrics.exposition()


def test_every_alert_has_complete_safe_runbook_and_daily_operations():
    alerts = yaml.safe_load((OBSERVABILITY / "alerts" / "alert-rules.yml").read_text(encoding="utf-8"))
    alert_names = [rule["alert"] for group in alerts["groups"] for rule in group["rules"]]
    runbook = (ROOT / "docs" / "operations" / "observability-alerts.md").read_text(encoding="utf-8")
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")

    for index, alert_name in enumerate(alert_names):
        section = runbook.split(f"## {alert_name}\n", 1)[1]
        if index + 1 < len(alert_names):
            section = section.split(f"## {alert_names[index + 1]}\n", 1)[0]
        for required in ("触发条件", "先看 Dashboard", "允许", "禁止", "恢复建议", "升级人工"):
            assert required in section

    for command in (
        "make up",
        "make down",
        "make observability-up",
        "make observability-down",
        "make observability-down-v",
        "make observability-alert-tests",
        "make observability-check",
        "make observability-acceptance",
    ):
        assert command in runbook
        assert command.split()[1] + ":" in makefile
    for prohibition in (
        "真实 Feishu 登录",
        "Token",
        "递归读取 Trace",
        "docker system prune",
        "docker volume prune",
        "业务 Volume",
    ):
        assert prohibition in runbook
