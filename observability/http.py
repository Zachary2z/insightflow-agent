from __future__ import annotations

from time import perf_counter
from typing import Any

from observability.context import get_correlation_context
from observability.logging import EventEmitter, emit_observability_event, safely_emit
from observability.metrics import InsightFlowMetrics, safe_metrics_scope, safely_get_metrics
from observability.redaction import classify_error
from starlette.routing import Match


def normalized_route(scope: dict[str, Any]) -> str:
    route = scope.get("route")
    template = getattr(route, "path", None)
    return template if type(template) is str and template.startswith("/") else "unmatched"


def resolved_route_template(scope: dict[str, Any]) -> str:
    """Resolve only a registered route template; the raw path never becomes a label."""
    app = scope.get("app")
    for route in getattr(app, "routes", ()):
        try:
            match, child_scope = route.matches(scope)
        except BaseException:
            continue
        if match is Match.FULL:
            template = getattr(route, "path", None) or child_scope.get("path")
            return template if isinstance(template, str) and template.startswith("/") else "unknown"
    return "unmatched"


def status_class(status_code: int) -> str:
    return f"{status_code // 100}xx"


def completion_status(status_code: int) -> str:
    if 200 <= status_code < 400:
        return "success"
    if 400 <= status_code < 500:
        return "rejected"
    if status_code >= 500:
        return "error"
    return "completed"


class HttpObservabilityMiddleware:
    def __init__(self, app, event_emitter: EventEmitter = emit_observability_event, metrics: InsightFlowMetrics | None = None):
        self.app = app
        self.event_emitter = event_emitter
        self.metrics = safely_get_metrics(metrics)

    async def __call__(self, scope, receive, send) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        started_at = perf_counter()
        method = str(scope.get("method") or "").upper()
        route_template = resolved_route_template(scope)
        try:
            if self.metrics is not None:
                self.metrics.register_http_routes([route_template])
        except BaseException:
            pass
        record_metrics = route_template != "/metrics"
        gauge_started = False
        if record_metrics:
            try:
                gauge_started = bool(self.metrics and self.metrics.record_http_started(method, route_template))
            except BaseException:
                gauge_started = False
        request_id = get_correlation_context().get("request_id")
        safely_emit(
            self.event_emitter,
            "http_request_started",
            request_id=request_id,
            http_method=method,
            status="started",
        )
        response_started = False
        response_status = 500
        error_type: str | None = None

        async def capture_status(message):
            nonlocal response_started, response_status
            if message.get("type") == "http.response.start":
                response_started = True
                response_status = int(message.get("status", 500))
            await send(message)

        try:
            with safe_metrics_scope(self.metrics):
                await self.app(scope, receive, capture_status)
        except BaseException as exc:
            error_type = classify_error(type(exc))
            if not response_started:
                response_status = 500
            raise
        finally:
            elapsed_seconds = max(0.0, perf_counter() - started_at)
            if record_metrics:
                try:
                    if self.metrics is not None:
                        self.metrics.record_http_completed(method, route_template, response_status, elapsed_seconds)
                except BaseException:
                    pass
                if gauge_started:
                    try:
                        if self.metrics is not None:
                            self.metrics.record_http_finished(method, route_template)
                    except BaseException:
                        pass
            completion_fields: dict[str, object] = {
                "request_id": request_id,
                "http_method": method,
                "route": normalized_route(scope),
                "status": "error" if error_type is not None else completion_status(response_status),
                "status_code": response_status,
                "status_class": status_class(response_status),
                "latency_ms": max(0, int(elapsed_seconds * 1000)),
            }
            if error_type is not None:
                completion_fields["error_type"] = error_type
            safely_emit(
                self.event_emitter,
                "http_request_completed",
                **completion_fields,
            )
