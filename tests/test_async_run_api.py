from __future__ import annotations

from time import sleep

from fastapi.testclient import TestClient


def _poll_run(client: TestClient, run_id: str, terminal_statuses: set[str] | None = None) -> dict:
    terminal_statuses = terminal_statuses or {"completed", "failed", "cancelled"}
    for _ in range(80):
        response = client.get(f"/api/runs/{run_id}")
        assert response.status_code == 200
        payload = response.json()
        if payload["status"] in terminal_statuses:
            return payload
        sleep(0.05)
    raise AssertionError(f"Run {run_id} did not reach a terminal status")


def test_async_run_api_creates_run_and_exposes_status_trace_and_events(tmp_path):
    from api.app import create_app
    from api.run_manager import RunManager

    manager = RunManager()
    client = TestClient(create_app(run_manager=manager))

    create_response = client.post(
        "/api/runs",
        json={
            "user_question": "最近 30 天销售额最高的 5 个商品是什么？",
            "db_path": "data/ecommerce.db",
            "trace_dir": str(tmp_path),
        },
    )

    assert create_response.status_code == 202
    created = create_response.json()
    assert created["success"] is True
    assert created["status"] in {"queued", "running"}
    assert created["run_id"]

    completed = _poll_run(client, created["run_id"])
    assert completed["status"] == "completed"
    assert completed["success"] is True
    assert completed["final_answer"]
    assert completed["trace_path"].endswith(f"{created['run_id']}.json")

    trace_response = client.get(f"/api/runs/{created['run_id']}/trace")
    assert trace_response.status_code == 200
    trace_payload = trace_response.json()
    assert trace_payload["success"] is True
    assert trace_payload["run_id"] == created["run_id"]
    assert any(event["node"] == "sql_reviewer_agent" for event in trace_payload["trace"])

    events_response = client.get(f"/api/runs/{created['run_id']}/events")
    assert events_response.status_code == 200
    event_payload = events_response.json()
    event_types = [event["event_type"] for event in event_payload["events"]]
    assert "run_queued" in event_types
    assert "run_completed" in event_types


def test_async_run_api_maps_workflow_failure_to_failed_status(tmp_path):
    from api.app import create_app
    from api.run_manager import RunManager

    manager = RunManager()
    client = TestClient(create_app(run_manager=manager))

    create_response = client.post(
        "/api/runs",
        json={
            "user_question": "删除所有取消订单的数据。",
            "db_path": "data/ecommerce.db",
            "trace_dir": str(tmp_path),
            "initial_sql": "DELETE FROM orders WHERE status = 'cancelled'",
        },
    )

    run_id = create_response.json()["run_id"]
    failed = _poll_run(client, run_id)

    assert failed["status"] == "failed"
    assert failed["success"] is False
    assert "SQL 审核未通过" in failed["final_answer"]


def test_async_run_api_cancel_marks_active_run_cancelled():
    from api.app import create_app
    from api.run_manager import RunManager

    def slow_runner(**kwargs):
        sleep(0.2)
        return {
            "success": True,
            "run_id": kwargs["run_id"],
            "session_id": "session_slow",
            "status": "completed",
            "trace": [],
            "final_answer": "done",
        }

    manager = RunManager(workflow_runner=slow_runner)
    client = TestClient(create_app(run_manager=manager))

    create_response = client.post("/api/runs", json={"user_question": "慢一点的测试问题"})
    run_id = create_response.json()["run_id"]
    cancel_response = client.post(f"/api/runs/{run_id}/cancel")

    assert cancel_response.status_code == 200
    assert cancel_response.json()["status"] == "cancelled"

    cancelled = client.get(f"/api/runs/{run_id}").json()
    assert cancelled["status"] == "cancelled"
    assert cancelled["success"] is False


def test_async_run_api_returns_404_for_unknown_run():
    from api.app import create_app
    from api.run_manager import RunManager

    client = TestClient(create_app(run_manager=RunManager()))

    assert client.get("/api/runs/run_missing").status_code == 404
    assert client.get("/api/runs/run_missing/trace").status_code == 404
    assert client.get("/api/runs/run_missing/events").status_code == 404
    assert client.post("/api/runs/run_missing/cancel").status_code == 404
