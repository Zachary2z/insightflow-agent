from __future__ import annotations

import json
import threading
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.app import create_app
from api.health import (
    ReadinessChecker,
    ReadinessPaths,
    check_storage_directory,
)
from api.lifecycle import AnalysisExecutor, AnalysisSubmissionClosed
from workspaces.store import WorkspaceStore


def _paths(tmp_path: Path) -> ReadinessPaths:
    return ReadinessPaths(
        workspace_root=tmp_path / "workspaces",
        report_root=tmp_path / "reports",
        trace_root=tmp_path / "logs" / "traces",
    )


def _app(tmp_path: Path, *, checker: ReadinessChecker | None = None):
    return create_app(
        workspace_store=WorkspaceStore(tmp_path / "workspaces"),
        readiness_checker=checker or ReadinessChecker(_paths(tmp_path)),
    )


def test_liveness_returns_strict_minimal_contract(tmp_path):
    with TestClient(_app(tmp_path)) as client:
        response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "insightflow-api"}


def test_liveness_succeeds_without_optional_provider_configuration(tmp_path, monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("INSIGHTFLOW_PRODUCT_LIVE_MODE", "0")

    with TestClient(_app(tmp_path)) as client:
        response = client.get("/health/live")

    assert response.status_code == 200


def test_readiness_succeeds_for_empty_keyless_workspace_without_lark_cli(tmp_path, monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("LARK_CLI_BIN", raising=False)
    monkeypatch.setenv("PATH", "")
    paths = _paths(tmp_path)

    with TestClient(_app(tmp_path, checker=ReadinessChecker(paths))) as client:
        response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "service": "insightflow-api",
        "checks": {
            "workspace_storage": "ok",
            "report_storage": "ok",
            "trace_storage": "ok",
            "configuration": "ok",
        },
    }
    assert list(paths.workspace_root.iterdir()) == []


def test_readiness_succeeds_for_existing_writable_runtime_directories(tmp_path):
    paths = _paths(tmp_path)
    for directory in (paths.workspace_root, paths.report_root, paths.trace_root):
        directory.mkdir(parents=True, exist_ok=True)

    result = ReadinessChecker(paths).check()

    assert result.status == "ready"
    assert set(result.checks.model_dump().values()) == {"ok"}


@pytest.mark.parametrize(
    ("failed_path", "failed_check"),
    [
        ("workspace_root", "workspace_storage"),
        ("report_root", "report_storage"),
        ("trace_root", "trace_storage"),
    ],
)
def test_required_storage_failure_returns_503(tmp_path, failed_path, failed_check):
    paths = _paths(tmp_path)

    def controlled_storage_check(path: Path):
        return "error" if path == getattr(paths, failed_path) else "ok"

    checker = ReadinessChecker(paths, storage_check=controlled_storage_check)
    with TestClient(_app(tmp_path, checker=checker)) as client:
        response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"
    assert response.json()["checks"][failed_check] == "error"


def test_failed_readiness_exposes_only_controlled_statuses(tmp_path, monkeypatch, caplog):
    secret = "health-secret-do-not-leak"
    monkeypatch.setenv("DEEPSEEK_API_KEY", secret)
    monkeypatch.setenv("OPENAI_API_KEY", secret)
    sensitive_path = tmp_path / secret / "user-workspace"
    paths = ReadinessPaths(
        workspace_root=sensitive_path,
        report_root=tmp_path / "reports",
        trace_root=tmp_path / "logs" / "traces",
    )

    def failing_storage_check(path: Path):
        if path == sensitive_path:
            raise OSError(
                f"{secret} /Users/private/project /app/workspaces/customer SQL SELECT Prompt "
                "DEEPSEEK_API_KEY=secret provider-response"
            )
        return "ok"

    checker = ReadinessChecker(paths, storage_check=failing_storage_check)
    with TestClient(_app(tmp_path, checker=checker)) as client:
        response = client.get("/health/ready")

    body = response.text
    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "service": "insightflow-api",
        "checks": {
            "workspace_storage": "error",
            "report_storage": "ok",
            "trace_storage": "ok",
            "configuration": "ok",
        },
    }
    for forbidden in (
        secret,
        "/Users/",
        "/app/workspaces/",
        "OSError",
        "SQL",
        "SELECT",
        "Prompt",
        "DEEPSEEK_API_KEY",
        "provider-response",
    ):
        assert forbidden not in body
    assert secret not in caplog.text


def test_storage_probe_is_removed_after_success(tmp_path):
    directory = tmp_path / "runtime"

    assert check_storage_directory(directory) == "ok"
    assert list(directory.iterdir()) == []


def test_storage_probe_never_overwrites_an_existing_file(tmp_path):
    directory = tmp_path / "runtime"
    directory.mkdir()
    existing = directory / ".insightflow-health-collision"
    existing.write_text("user-content-must-remain", encoding="utf-8")

    status = check_storage_directory(
        directory,
        probe_name_factory=lambda: existing.name,
    )

    assert status == "error"
    assert existing.read_text(encoding="utf-8") == "user-content-must-remain"


def test_readiness_does_not_read_existing_workspace_content(tmp_path, monkeypatch):
    paths = _paths(tmp_path)
    paths.workspace_root.mkdir(parents=True)
    existing = paths.workspace_root / "workspace.json"
    existing.write_text("health-secret-do-not-leak", encoding="utf-8")
    original_read_text = Path.read_text

    def guarded_read_text(path: Path, *args, **kwargs):
        if path == existing:
            raise AssertionError("readiness read existing workspace data")
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", guarded_read_text)

    result = ReadinessChecker(paths).check()

    assert result.status == "ready"
    assert original_read_text(existing, encoding="utf-8") == "health-secret-do-not-leak"


def test_unexpected_individual_check_exception_is_safely_converted(tmp_path):
    paths = _paths(tmp_path)

    def unexpected(path: Path):
        if path == paths.report_root:
            raise RuntimeError("internal path and secret must not escape")
        return "ok"

    result = ReadinessChecker(paths, storage_check=unexpected).check()

    assert result.status == "not_ready"
    assert result.checks.report_storage == "error"
    assert result.checks.workspace_storage == "ok"
    assert result.checks.trace_storage == "ok"


def test_invalid_configuration_structure_is_not_ready(tmp_path):
    paths = _paths(tmp_path)
    result = ReadinessChecker(
        paths,
        storage_check=lambda _path: "ok",
        configuration_check=lambda _paths: "error",
    ).check()

    assert result.status == "not_ready"
    assert result.checks.configuration == "error"


def test_testclient_lifespan_shuts_down_analysis_executor(tmp_path):
    executor = AnalysisExecutor(max_workers=1)
    app = create_app(
        workspace_store=WorkspaceStore(tmp_path / "workspaces"),
        readiness_checker=ReadinessChecker(_paths(tmp_path)),
        analysis_executor=executor,
    )

    with TestClient(app):
        assert executor.submit(lambda: "completed").result(timeout=1) == "completed"
        assert executor.accepting is True

    assert executor.shutdown_called is True
    assert executor.accepting is False
    with pytest.raises(AnalysisSubmissionClosed):
        executor.submit(lambda: None)


def test_executor_shutdown_cancels_queued_task_and_finishes_running_task():
    executor = AnalysisExecutor(max_workers=1)
    running_started = threading.Event()
    release_running = threading.Event()
    shutdown_finished = threading.Event()

    def running_task():
        running_started.set()
        assert release_running.wait(timeout=2)
        return "completed"

    running = executor.submit(running_task)
    assert running_started.wait(timeout=1)
    queued = executor.submit(lambda: "must-not-run")

    def shut_down():
        executor.shutdown()
        shutdown_finished.set()

    shutdown_thread = threading.Thread(target=shut_down)
    shutdown_thread.start()
    assert not shutdown_finished.wait(timeout=0.05)
    assert executor.accepting is False
    release_running.set()
    assert shutdown_finished.wait(timeout=1)
    shutdown_thread.join(timeout=1)

    assert running.result(timeout=1) == "completed"
    assert queued.cancelled() is True


def test_repeated_app_lifespans_do_not_leave_analysis_threads(tmp_path):
    before = {thread.ident for thread in threading.enumerate() if thread.name.startswith("insightflow-analysis")}

    for index in range(5):
        executor = AnalysisExecutor(max_workers=1)
        app = create_app(
            workspace_store=WorkspaceStore(tmp_path / f"workspaces-{index}"),
            readiness_checker=ReadinessChecker(_paths(tmp_path / str(index))),
            analysis_executor=executor,
        )
        with TestClient(app):
            assert executor.submit(lambda: True).result(timeout=1) is True

    after = {thread.ident for thread in threading.enumerate() if thread.name.startswith("insightflow-analysis")}
    assert after == before


def test_workspace_api_remains_available_with_lifespan(tmp_path):
    with TestClient(_app(tmp_path)) as client:
        created = client.post("/api/workspaces", json={"name": "Health Regression"})
        listed = client.get("/api/workspaces")

    assert created.status_code == 200
    assert listed.status_code == 200
    assert listed.json()["workspaces"][0]["workspace_id"] == created.json()["workspace_id"]
    assert json.loads((tmp_path / "workspaces" / created.json()["workspace_id"] / "workspace.json").read_text())
