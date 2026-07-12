from pathlib import Path
import re

import yaml


ROOT = Path(__file__).resolve().parents[1]
COMPOSE_PATH = ROOT / "compose.yaml"


def _compose() -> dict:
    payload = yaml.safe_load(COMPOSE_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _volume_targets(service: dict) -> dict[str, str]:
    targets: dict[str, str] = {}
    for mount in service.get("volumes", []):
        if isinstance(mount, str):
            source, target, *_ = mount.split(":")
        else:
            source = mount["source"]
            target = mount["target"]
        targets[source] = target
    return targets


def test_compose_parses_and_defines_product_plus_optional_observability_services():
    compose = _compose()

    assert set(compose["services"]) == {"backend", "frontend", "prometheus", "grafana"}
    assert compose["services"]["backend"]["image"] == "insightflow-backend:p37"
    assert compose["services"]["frontend"]["image"] == "insightflow-frontend:p37"
    assert "version" not in compose
    assert compose["services"]["prometheus"]["profiles"] == ["observability"]
    assert compose["services"]["grafana"]["profiles"] == ["observability"]
    assert "profiles" not in compose["services"]["backend"]
    assert "profiles" not in compose["services"]["frontend"]


def test_service_build_and_health_dependency_contract():
    services = _compose()["services"]
    backend = services["backend"]
    frontend = services["frontend"]

    assert backend["build"] == {"context": ".", "dockerfile": "Dockerfile"}
    assert frontend["build"]["context"] == "./frontend"
    assert frontend["build"]["dockerfile"] == "Dockerfile"
    assert frontend["depends_on"]["backend"]["condition"] == "service_healthy"
    assert "healthcheck" not in backend or backend["healthcheck"].get("disable") is not True
    assert "HEALTHCHECK" in (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert frontend["healthcheck"]["test"][:2] == ["CMD", "node"]
    assert "sleep" not in COMPOSE_PATH.read_text(encoding="utf-8").lower()


def test_backend_disables_raw_uvicorn_access_urls_in_container_logs():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert '"--no-access-log"' in dockerfile


def test_backend_trace_sink_and_retention_configuration_is_fixed_and_volume_neutral():
    environment = _compose()["services"]["backend"]["environment"]

    assert environment["INSIGHTFLOW_TRACE_SINKS"] == "${INSIGHTFLOW_TRACE_SINKS:-local}"
    assert environment["INSIGHTFLOW_TRACE_DIR"] == "/app/logs/traces"
    assert environment["INSIGHTFLOW_TRACE_RETENTION_DAYS"] == "${INSIGHTFLOW_TRACE_RETENTION_DAYS:-}"
    assert environment["INSIGHTFLOW_TRACE_RETENTION_MAX_BYTES"] == "${INSIGHTFLOW_TRACE_RETENTION_MAX_BYTES:-}"


def test_business_volumes_are_preserved_and_observability_volumes_are_isolated():
    compose = _compose()
    expected = {
        "workspace-data": "/app/workspaces",
        "report-data": "/app/reports",
        "trace-data": "/app/logs/traces",
    }

    assert set(compose["volumes"]) == set(expected) | {"prometheus-data", "grafana-data"}
    assert _volume_targets(compose["services"]["backend"]) == expected
    assert _volume_targets(compose["services"]["prometheus"])["prometheus-data"] == "/prometheus"
    assert _volume_targets(compose["services"]["grafana"])["grafana-data"] == "/var/lib/grafana"


def test_runtime_security_and_restart_contract():
    compose = _compose()
    for service in compose["services"].values():
        assert service.get("restart") == "unless-stopped"
        assert service.get("init") is True
        assert "container_name" not in service
        assert service.get("privileged") is not True
        assert str(service.get("user", "")).lower() not in {"root", "0", "0:0"}

        mounts = service.get("volumes", [])
        serialized_mounts = "\n".join(str(mount) for mount in mounts)
        assert "/var/run/docker.sock" not in serialized_mounts
        assert ".env" not in serialized_mounts
        assert not re.search(r"(?:^|:)\s*/\s*(?::|$)", serialized_mounts)


def test_ports_network_and_browser_api_defaults_are_safe():
    compose = _compose()
    backend = compose["services"]["backend"]
    frontend = compose["services"]["frontend"]

    assert backend["ports"] == ["127.0.0.1:${BACKEND_HOST_PORT:-8000}:8000"]
    assert frontend["ports"] == ["127.0.0.1:${FRONTEND_HOST_PORT:-3000}:3000"]
    assert compose["services"]["prometheus"]["ports"] == ["127.0.0.1:${PROMETHEUS_HOST_PORT:-9090}:9090"]
    assert compose["services"]["grafana"]["ports"] == ["127.0.0.1:${GRAFANA_HOST_PORT:-3001}:3000"]
    assert set(backend["networks"]) == {"insightflow-network"}
    assert set(frontend["networks"]) == {"insightflow-network"}
    assert compose["networks"]["insightflow-network"]["driver"] == "bridge"
    assert compose["networks"]["insightflow-network"].get("internal") is not True
    assert frontend["build"]["args"] == {
        "NEXT_PUBLIC_API_BASE": "${NEXT_PUBLIC_API_BASE:-http://localhost:8000}"
    }
    assert "backend:8000" not in frontend["build"]["args"]["NEXT_PUBLIC_API_BASE"]


def test_no_secrets_are_hardcoded_or_exposed_as_frontend_build_args():
    compose = _compose()
    text = COMPOSE_PATH.read_text(encoding="utf-8")
    frontend_args = compose["services"]["frontend"]["build"]["args"]

    assert set(frontend_args) == {"NEXT_PUBLIC_API_BASE"}
    for forbidden_arg in ("API_KEY", "TOKEN", "SECRET", "PASSWORD", "LARK"):
        assert all(forbidden_arg not in key.upper() for key in frontend_args)
    assert not re.search(
        r"(?im)^\s*(?:DEEPSEEK_API_KEY|OPENAI_API_KEY)\s*:\s*(?![\"']?\$\{)[^\s]+",
        text,
    )
    assert "LARK_CLI_BIN" not in text
