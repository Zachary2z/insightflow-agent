from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from threading import Lock
from typing import Any, Callable

from observability.context import correlation_scope, get_correlation_context


class AnalysisSubmissionClosed(RuntimeError):
    pass


class AnalysisExecutor:
    """Own the background executor and its explicit shutdown contract."""

    def __init__(self, *, max_workers: int = 2):
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="insightflow-analysis",
        )
        self._lock = Lock()
        self._accepting = True
        self._shutdown_called = False

    @property
    def accepting(self) -> bool:
        with self._lock:
            return self._accepting

    @property
    def shutdown_called(self) -> bool:
        with self._lock:
            return self._shutdown_called

    def submit(self, function: Callable[..., Any], /, *args: Any, **kwargs: Any) -> Future[Any]:
        captured_context = get_correlation_context()

        def run_with_context() -> Any:
            with correlation_scope(**captured_context):
                return function(*args, **kwargs)

        with self._lock:
            if not self._accepting:
                raise AnalysisSubmissionClosed("Background analysis is shutting down")
            return self._executor.submit(run_with_context)

    def shutdown(self) -> None:
        with self._lock:
            if self._shutdown_called:
                return
            self._accepting = False
            self._shutdown_called = True
        self._executor.shutdown(wait=True, cancel_futures=True)
