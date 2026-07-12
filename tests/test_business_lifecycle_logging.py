from __future__ import annotations

import json

from fastapi.testclient import TestClient

from api.app import create_app
from observability.context import correlation_scope, get_correlation_context
from workspaces import analysis_runner
from workspaces.analysis_runner import execute_workspace_analysis_job
from workspaces.store import WorkspaceStore


def test_background_workflow_emits_safe_started_and_completed_with_context(tmp_path, monkeypatch):
    events: list[dict] = []

    def collect(event, **fields):
        events.append({"event": event, **fields})

    monkeypatch.setattr(
        analysis_runner,
        "run_workspace_analysis",
        lambda **_kwargs: {"status": "completed", "business_answer": "private prompt"},
    )
    with correlation_scope(request_id="req_workflow"):
        result = execute_workspace_analysis_job(
            WorkspaceStore(tmp_path / "workspaces"),
            "workspace_safe",
            "run_safe",
            "private prompt",
            event_emitter=collect,
        )

    assert result["status"] == "completed"
    assert [event["event"] for event in events] == ["workflow_run_started", "workflow_run_completed"]
    assert events[0]["request_id"] == "req_workflow"
    assert events[0]["workspace_id"] == "workspace_safe"
    assert events[0]["run_id"] == "run_safe"
    assert events[1]["status"] == "success"
    assert events[1]["latency_ms"] >= 0
    assert "private prompt" not in json.dumps(events)
    assert get_correlation_context() == {}


def test_workflow_emitter_failure_does_not_change_result(tmp_path, monkeypatch):
    monkeypatch.setattr(analysis_runner, "run_workspace_analysis", lambda **_kwargs: {"status": "completed"})

    def fail(*_args, **_kwargs):
        raise OSError("Bearer synthetic-token-do-not-leak")

    result = execute_workspace_analysis_job(
        WorkspaceStore(tmp_path / "workspaces"),
        "workspace_safe",
        "run_safe",
        "question",
        event_emitter=fail,
    )
    assert result == {"status": "completed"}


def test_report_generation_event_contains_ids_not_report_content(tmp_path):
    events: list[dict] = []
    store = WorkspaceStore(tmp_path / "workspaces")

    def collect(event, **fields):
        events.append({"event": event, **fields})

    def fake_report_runner(store, workspace_id, report_type, report_goal, providers=None):
        return {
            "success": True,
            "workspace_id": workspace_id,
            "report_id": "report_safe",
            "report": {"content": "raw rows SELECT * FROM customer /Users/private/project"},
        }

    app = create_app(workspace_store=store, report_runner=fake_report_runner, event_emitter=collect)
    with TestClient(app) as client:
        workspace_id = client.post("/api/workspaces", json={"name": "Lifecycle"}).json()["workspace_id"]
        response = client.post(
            f"/api/workspaces/{workspace_id}/reports",
            headers={"X-Request-ID": "req_report"},
            json={"report_type": "business_review", "report_goal": "private prompt"},
        )

    assert response.status_code == 200
    lifecycle = [event for event in events if event["event"] == "report_generation_completed"]
    assert len(lifecycle) == 1
    assert lifecycle[0]["request_id"] == "req_report"
    assert lifecycle[0]["workspace_id"] == workspace_id
    assert lifecycle[0]["report_id"] == "report_safe"
    serialized = json.dumps(lifecycle)
    for forbidden in ("private prompt", "SELECT", "raw rows", "/Users/private"):
        assert forbidden not in serialized


def test_broken_delivery_metrics_do_not_change_report_api_response(tmp_path):
    class BrokenMetrics:
        def __getattribute__(self, _name):
            raise RuntimeError("metrics unavailable")

    store = WorkspaceStore(tmp_path / "workspaces")

    def fake_report_runner(store, workspace_id, report_type, report_goal, providers=None):
        return {
            "success": True,
            "workspace_id": workspace_id,
            "report_id": "report_safe",
            "report": {"status": "completed", "title": "Safe report"},
        }

    app = create_app(workspace_store=store, report_runner=fake_report_runner, metrics=BrokenMetrics())
    with TestClient(app) as client:
        workspace_id = client.post("/api/workspaces", json={"name": "Metrics isolation"}).json()["workspace_id"]
        response = client.post(
            f"/api/workspaces/{workspace_id}/reports",
            json={"report_type": "business_review", "report_goal": "Goal"},
        )
    assert response.status_code == 200
    assert response.json()["report_id"] == "report_safe"
    assert response.json()["success"] is True
