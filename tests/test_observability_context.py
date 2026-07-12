from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor

import pytest

from observability.context import (
    bind_correlation_context,
    correlation_scope,
    get_correlation_context,
    reset_correlation_context,
)


def test_default_context_is_empty():
    assert get_correlation_context() == {}


def test_bind_and_reset_request_id():
    token = bind_correlation_context(request_id="req_contract")
    assert get_correlation_context() == {"request_id": "req_contract"}
    reset_correlation_context(token)
    assert get_correlation_context() == {}


def test_nested_scope_restores_parent_and_partial_ids():
    with correlation_scope(request_id="req_parent", workspace_id="workspace_1"):
        with correlation_scope(run_id="run_1", report_id="report_1"):
            assert get_correlation_context() == {
                "request_id": "req_parent",
                "workspace_id": "workspace_1",
                "run_id": "run_1",
                "report_id": "report_1",
            }
        assert get_correlation_context() == {
            "request_id": "req_parent",
            "workspace_id": "workspace_1",
        }
    assert get_correlation_context() == {}


def test_scope_restores_context_after_exception():
    with pytest.raises(RuntimeError):
        with correlation_scope(request_id="req_error"):
            raise RuntimeError("synthetic")
    assert get_correlation_context() == {}


def test_empty_values_are_not_added():
    with correlation_scope(request_id="req_empty", run_id=None, report_id=""):
        assert get_correlation_context() == {"request_id": "req_empty"}


@pytest.mark.parametrize(
    "invalid",
    ["has space", "../path", "SELECT", "<html>", "line\nbreak", "x" * 65],
)
def test_invalid_or_overlong_ids_are_rejected(invalid):
    with pytest.raises(ValueError):
        bind_correlation_context(request_id=invalid)
    assert get_correlation_context() == {}


def test_asyncio_tasks_do_not_leak_context():
    async def worker(request_id: str) -> str:
        with correlation_scope(request_id=request_id):
            await asyncio.sleep(0)
            return get_correlation_context()["request_id"]

    async def run_workers() -> list[str]:
        return await asyncio.gather(worker("req_one"), worker("req_two"))

    assert asyncio.run(run_workers()) == ["req_one", "req_two"]
    assert get_correlation_context() == {}


def test_threads_start_with_independent_contexts():
    def worker(request_id: str) -> tuple[str, dict]:
        before = get_correlation_context()
        with correlation_scope(request_id=request_id):
            current = get_correlation_context()["request_id"]
        return current, before

    with correlation_scope(request_id="req_parent"):
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(worker, ["req_thread_a", "req_thread_b"]))
        assert get_correlation_context()["request_id"] == "req_parent"
    assert results == [("req_thread_a", {}), ("req_thread_b", {})]
    assert get_correlation_context() == {}
