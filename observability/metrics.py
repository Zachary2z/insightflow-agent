from __future__ import annotations

import os
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from typing import Any, Iterator, Mapping

from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, Counter, Gauge, Histogram, generate_latest


HTTP_DURATION_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
RUN_DURATION_BUCKETS = (0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0)
OPERATION_DURATION_BUCKETS = (0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0)

LABEL_ALLOWLISTS: Mapping[str, frozenset[str]] = {
    "method": frozenset({"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS", "CONNECT", "TRACE"}),
    "status_class": frozenset({"1xx", "2xx", "3xx", "4xx", "5xx", "unknown"}),
    "route": frozenset({"fast", "standard", "deep", "clarification", "unknown"}),
    "status": frozenset({"success", "error", "timeout", "fallback", "failed", "rejected", "skipped", "degraded", "clarification", "warning", "unknown"}),
    "node": frozenset({"question_understanding", "clarification", "evidence_agent", "fast_fact", "business_answer", "visualization_agent", "fail", "early_response", "save_trace", "other"}),
    "reason_category": frozenset({"missing_context", "ambiguous_request", "validation", "provider_error", "schema_error", "timeout", "unsupported", "not_required", "other", "unknown"}),
    "operation": frozenset({"analysis", "analysis_follow_up", "question_understanding", "clarification", "sql_planning", "sql_candidate", "business_answer", "visualization", "report_composer", "provider_request", "sql_validation", "sql_execution", "evidence_validation", "evidence_task", "report_generation", "document_export", "external_publish", "other"}),
    "error_type": frozenset({"none", "validation", "provider", "schema", "timeout", "connection", "not_found", "permission", "execution", "unknown", "other"}),
    "provider": frozenset({"local", "mock", "deepseek", "openai", "other"}),
    "token_type": frozenset({"input", "output", "total"}),
    "risk_level": frozenset({"low", "medium", "high", "unknown"}),
    "chart_type": frozenset({"bar", "line", "table", "kpi", "other"}),
    "format": frozenset({"docx", "other"}),
    "platform": frozenset({"feishu", "other"}),
}

_FALLBACKS = {"node": "other", "operation": "other", "provider": "other", "chart_type": "other", "format": "other", "platform": "other", "reason_category": "other", "error_type": "other"}


def normalize_label(kind: str, value: Any) -> str:
    """Collapse an untrusted value into the finite vocabulary for one label kind."""
    allowed = LABEL_ALLOWLISTS.get(kind)
    if allowed is None:
        return "unknown"
    if type(value) is not str:
        return _FALLBACKS.get(kind, "unknown")
    candidate = value.strip()
    if kind == "method":
        candidate = candidate.upper()
    else:
        candidate = candidate.lower()
    return candidate if candidate in allowed else _FALLBACKS.get(kind, "unknown")


def normalize_analysis_route(value: Any) -> str:
    if type(value) is dict:
        value = value.get("route")
    if type(value) is not str:
        return "unknown"
    return {"fast_fact": "fast", "fast": "fast", "standard_analysis": "standard", "standard": "standard", "deep_judgment": "deep", "deep": "deep", "clarification": "clarification"}.get(value.lower(), "unknown")


def normalize_error_type(value: Any) -> str:
    text = value.lower() if type(value) is str else ""
    if not text:
        return "none"
    for marker, category in (("timeout", "timeout"), ("schema", "schema"), ("valid", "validation"), ("provider", "provider"), ("connect", "connection"), ("not_found", "not_found"), ("permission", "permission"), ("sql", "execution"), ("execut", "execution")):
        if marker in text:
            return category
    return normalize_label("error_type", text)


def normalize_reason(value: Any) -> str:
    text = value.lower() if type(value) is str else ""
    for marker, category in (("timeout", "timeout"), ("schema", "schema_error"), ("provider", "provider_error"), ("valid", "validation"), ("ambig", "ambiguous_request"), ("missing", "missing_context"), ("unsupported", "unsupported"), ("not_required", "not_required")):
        if marker in text:
            return category
    return normalize_label("reason_category", text)


def normalize_provider(provider: Any, model: Any = None) -> str:
    try:
        type_name = type(provider).__name__ if provider is not None else ""
        safe_model = model if provider is None and type(model) is str else ""
        text = " ".join(item for item in (type_name, safe_model) if item).lower()
    except BaseException:
        return "other"
    for name in ("deepseek", "openai", "mock", "local"):
        if name in text:
            return name
    return "other"


def normalize_operation(value: Any) -> str:
    text = value.lower() if type(value) is str else ""
    aliases = {"visualization_agent": "visualization", "llm_provider": "provider_request", "analysis_followup": "analysis_follow_up"}
    return normalize_label("operation", aliases.get(text, text))


def normalize_chart_type(value: Any) -> str:
    text = value.lower() if type(value) is str else ""
    if "bar" in text:
        return "bar"
    if "line" in text or "scatter" in text:
        return "line"
    if "table" in text:
        return "table"
    if "kpi" in text or "metric" in text:
        return "kpi"
    return "other"


class InsightFlowMetrics:
    """Owns every collector and isolates all recording failures from business code."""

    content_type = CONTENT_TYPE_LATEST

    def __init__(self, registry: CollectorRegistry | None = None, storage_path: Path | str | None = None):
        self.registry = registry or CollectorRegistry(auto_describe=True)
        self._storage_path = Path(storage_path or os.getenv("INSIGHTFLOW_TRACE_DIR", "logs/traces"))
        self._http_routes: set[str] = {"unmatched", "unknown"}
        self.http_requests = Counter("insightflow_http_requests_total", "HTTP requests completed.", ("method", "route", "status_class"), registry=self.registry)
        self.http_duration = Histogram("insightflow_http_request_duration_seconds", "HTTP request duration in seconds.", ("method", "route"), buckets=HTTP_DURATION_BUCKETS, registry=self.registry)
        self.http_in_progress = Gauge("insightflow_http_requests_in_progress", "HTTP requests currently in progress.", ("method", "route"), registry=self.registry)
        self.runs = Counter("insightflow_runs_total", "Analysis workflow runs.", ("route", "status"), registry=self.registry)
        self.run_duration = Histogram("insightflow_run_duration_seconds", "Analysis workflow duration in seconds.", ("route", "status"), buckets=RUN_DURATION_BUCKETS, registry=self.registry)
        self.node_executions = Counter("insightflow_node_executions_total", "Workflow node executions.", ("node", "status"), registry=self.registry)
        self.node_duration = Histogram("insightflow_node_duration_seconds", "Workflow node duration in seconds.", ("node", "status"), buckets=OPERATION_DURATION_BUCKETS, registry=self.registry)
        self.clarifications = Counter("insightflow_clarifications_total", "Clarification outcomes.", ("reason_category",), registry=self.registry)
        self.retries = Counter("insightflow_retries_total", "Bounded retry attempts.", ("operation", "error_type"), registry=self.registry)
        self.llm_requests = Counter("insightflow_llm_requests_total", "LLM provider requests.", ("provider", "operation", "status"), registry=self.registry)
        self.llm_duration = Histogram("insightflow_llm_duration_seconds", "LLM request duration in seconds.", ("provider", "operation", "status"), buckets=OPERATION_DURATION_BUCKETS, registry=self.registry)
        self.llm_tokens = Counter("insightflow_llm_tokens_total", "Reported LLM tokens.", ("provider", "operation", "token_type"), registry=self.registry)
        self.llm_fallbacks = Counter("insightflow_llm_fallbacks_total", "LLM fallbacks.", ("operation", "reason_category"), registry=self.registry)
        self.sql_validations = Counter("insightflow_sql_validations_total", "SQL validation outcomes.", ("status", "risk_level"), registry=self.registry)
        self.sql_executions = Counter("insightflow_sql_executions_total", "SQL execution outcomes.", ("status", "error_type"), registry=self.registry)
        self.sql_duration = Histogram("insightflow_sql_duration_seconds", "SQL execution duration in seconds.", ("status",), buckets=OPERATION_DURATION_BUCKETS, registry=self.registry)
        self.evidence_validations = Counter("insightflow_evidence_validations_total", "Evidence validation outcomes.", ("status", "reason_category"), registry=self.registry)
        self.evidence_tasks = Counter("insightflow_evidence_tasks_total", "Evidence task outcomes.", ("status", "route"), registry=self.registry)
        self.chart_generations = Counter("insightflow_chart_generations_total", "Chart generation outcomes.", ("chart_type", "status"), registry=self.registry)
        self.report_generations = Counter("insightflow_report_generations_total", "Report generation outcomes.", ("status",), registry=self.registry)
        self.document_exports = Counter("insightflow_document_exports_total", "Document export outcomes.", ("format", "status"), registry=self.registry)
        self.external_publishes = Counter("insightflow_external_publishes_total", "External publish outcomes.", ("platform", "status"), registry=self.registry)
        self.external_publish_duration = Histogram("insightflow_external_publish_duration_seconds", "External publish duration in seconds.", ("platform", "status"), buckets=RUN_DURATION_BUCKETS, registry=self.registry)
        self.runtime_storage_usage_ratio = Gauge(
            "insightflow_runtime_storage_usage_ratio",
            "Aggregate filesystem usage ratio for the configured trace storage mount.",
            registry=self.registry,
        )

    @staticmethod
    def _safe(callable_: Any, *args: Any, **kwargs: Any) -> bool:
        try:
            callable_(*args, **kwargs)
            return True
        except BaseException:
            return False

    def inc(self, metric: Any, labels: Mapping[str, Any] | None = None, amount: float = 1.0) -> None:
        try:
            if type(amount) not in {int, float} or amount < 0:
                return
            normalized = {name: normalize_label(name, value) for name, value in (labels or {}).items()}
            child = metric.labels(**normalized) if normalized else metric
            self._safe(child.inc, amount)
        except BaseException:
            return

    def observe(self, metric: Any, seconds: Any, labels: Mapping[str, Any] | None = None) -> None:
        try:
            if type(seconds) not in {int, float}:
                return
            normalized = {name: normalize_label(name, value) for name, value in (labels or {}).items()}
            value = max(0.0, seconds)
            child = metric.labels(**normalized) if normalized else metric
            self._safe(child.observe, value)
        except BaseException:
            return

    def gauge_inc(self, metric: Any, labels: Mapping[str, Any]) -> bool:
        try:
            normalized = {name: normalize_label(name, value) if name != "route" else (value if type(value) is str else "unknown") for name, value in labels.items()}
            return self._safe(metric.labels(**normalized).inc)
        except BaseException:
            return False

    def gauge_dec(self, metric: Any, labels: Mapping[str, Any]) -> bool:
        try:
            normalized = {name: normalize_label(name, value) if name != "route" else (value if type(value) is str else "unknown") for name, value in labels.items()}
            return self._safe(metric.labels(**normalized).dec)
        except BaseException:
            return False

    def exposition(self) -> bytes:
        self._update_runtime_storage_usage()
        return generate_latest(self.registry)

    def _update_runtime_storage_usage(self) -> None:
        """Read aggregate filesystem counters only; never scan or label stored content."""
        try:
            stats = os.statvfs(self._storage_path)
            total = stats.f_blocks * stats.f_frsize
            available = stats.f_bavail * stats.f_frsize
            if total <= 0:
                return
            self._safe(self.runtime_storage_usage_ratio.set, min(1.0, max(0.0, (total - available) / total)))
        except BaseException:
            return

    def register_http_routes(self, routes: Any) -> None:
        try:
            self._http_routes.update(
                route for route in routes if type(route) is str and route.startswith("/") and len(route) <= 200
            )
        except BaseException:
            return

    def http_labels(self, method: Any, route: Any) -> dict[str, str]:
        safe_route = route if type(route) is str and route in self._http_routes else "unknown"
        return {"method": normalize_label("method", method), "route": safe_route}

    def record_http_started(self, method: Any, route: Any) -> bool:
        try:
            return self.gauge_inc(self.http_in_progress, self.http_labels(method, route))
        except BaseException:
            return False

    def record_http_completed(self, method: Any, route: Any, status_code: Any, duration_seconds: Any) -> None:
        try:
            labels = self.http_labels(method, route)
            code = status_code if type(status_code) is int else 0
            status = f"{code // 100}xx" if 100 <= code <= 599 else "unknown"
            self._safe(self.http_requests.labels(**labels, status_class=status).inc)
            if type(duration_seconds) in {int, float}:
                self._safe(self.http_duration.labels(**labels).observe, max(0.0, duration_seconds))
        except BaseException:
            return

    def record_http_finished(self, method: Any, route: Any) -> bool:
        try:
            labels = self.http_labels(method, route)
            if self.gauge_dec(self.http_in_progress, labels):
                return True
            normalized = {"method": normalize_label("method", labels["method"]), "route": labels["route"]}
            return self._safe(self.http_in_progress.labels(**normalized).set, 0)
        except BaseException:
            return False


MetricsRegistry = InsightFlowMetrics
_PRODUCTION_METRICS = InsightFlowMetrics()
_CURRENT_METRICS: ContextVar[InsightFlowMetrics | None] = ContextVar("insightflow_metrics", default=None)


def get_metrics() -> InsightFlowMetrics:
    return _CURRENT_METRICS.get() or _PRODUCTION_METRICS


def safely_get_metrics(candidate: Any = None) -> InsightFlowMetrics | None:
    """Return a recorder without allowing lookup/property failures into business code."""
    try:
        resolved = candidate if candidate is not None else get_metrics()
        return resolved if resolved is not None else None
    except BaseException:
        return None


def safely_inc(metrics: Any, metric_name: str, labels: Mapping[str, Any], amount: Any = 1.0) -> None:
    try:
        if metrics is None or type(metric_name) is not str:
            return
        metric = getattr(metrics, metric_name)
        metrics.inc(metric, labels, amount)
    except BaseException:
        return


def safely_observe(metrics: Any, metric_name: str, seconds: Any, labels: Mapping[str, Any]) -> None:
    try:
        if metrics is None or type(metric_name) is not str:
            return
        metric = getattr(metrics, metric_name)
        metrics.observe(metric, seconds, labels)
    except BaseException:
        return


@contextmanager
def metrics_scope(metrics: InsightFlowMetrics) -> Iterator[InsightFlowMetrics]:
    token = _CURRENT_METRICS.set(metrics)
    try:
        yield metrics
    finally:
        _CURRENT_METRICS.reset(token)


@contextmanager
def safe_metrics_scope(metrics: Any) -> Iterator[Any]:
    token = None
    try:
        if metrics is not None:
            token = _CURRENT_METRICS.set(metrics)
    except BaseException:
        token = None
    try:
        yield metrics
    finally:
        if token is not None:
            try:
                _CURRENT_METRICS.reset(token)
            except BaseException:
                pass


def create_metrics(registry: CollectorRegistry | None = None, storage_path: Path | str | None = None) -> InsightFlowMetrics:
    return InsightFlowMetrics(registry=registry, storage_path=storage_path)


__all__ = ["CONTENT_TYPE_LATEST", "HTTP_DURATION_BUCKETS", "RUN_DURATION_BUCKETS", "OPERATION_DURATION_BUCKETS", "LABEL_ALLOWLISTS", "InsightFlowMetrics", "MetricsRegistry", "create_metrics", "get_metrics", "metrics_scope", "safe_metrics_scope", "safely_get_metrics", "safely_inc", "safely_observe", "normalize_analysis_route", "normalize_chart_type", "normalize_error_type", "normalize_label", "normalize_operation", "normalize_provider", "normalize_reason"]
