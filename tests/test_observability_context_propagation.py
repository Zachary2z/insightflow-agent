from __future__ import annotations

from api.lifecycle import AnalysisExecutor
from observability.context import correlation_scope, get_correlation_context


def test_analysis_executor_propagates_only_safe_context_and_resets_between_jobs():
    executor = AnalysisExecutor(max_workers=1)
    try:
        with correlation_scope(request_id="req_a", workspace_id="workspace_a", run_id="run_a"):
            first = executor.submit(get_correlation_context)
        with correlation_scope(request_id="req_b", workspace_id="workspace_b", run_id="run_b"):
            second = executor.submit(get_correlation_context)
        empty = executor.submit(get_correlation_context)

        assert first.result() == {"request_id": "req_a", "workspace_id": "workspace_a", "run_id": "run_a"}
        assert second.result() == {"request_id": "req_b", "workspace_id": "workspace_b", "run_id": "run_b"}
        assert empty.result() == {}
    finally:
        executor.shutdown()
    assert get_correlation_context() == {}
