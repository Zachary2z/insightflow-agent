from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


AnalysisRoute = Literal["clarify", "fast_fact", "standard_analysis", "deep_judgment", "reject"]


@dataclass
class AnalysisTask:
    resolved_question: str
    metrics: list[str] = field(default_factory=list)
    dimensions: list[str] = field(default_factory=list)
    time_range: dict[str, Any] = field(default_factory=dict)
    filters: list[str] = field(default_factory=list)
    decision_goal: str = ""
    missing_slots: list[str] = field(default_factory=list)
    clarification_question: str = ""
    route_hint: str = ""
    business_lens: dict[str, Any] = field(default_factory=dict)
    evidence_task_plan: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AnalysisTask":
        return cls(
            resolved_question=str(data.get("resolved_question") or ""),
            metrics=_str_list(data.get("metrics")),
            dimensions=_str_list(data.get("dimensions")),
            time_range=_dict(data.get("time_range")),
            filters=_str_list(data.get("filters")),
            decision_goal=str(data.get("decision_goal") or ""),
            missing_slots=_str_list(data.get("missing_slots")),
            clarification_question=str(data.get("clarification_question") or ""),
            route_hint=str(data.get("route_hint") or ""),
            business_lens=_dict(data.get("business_lens")),
            evidence_task_plan=_dict(data.get("evidence_task_plan")),
        )


@dataclass
class CoordinatorDecision:
    route: AnalysisRoute
    required_agents: list[str] = field(default_factory=list)
    reason: str = ""
    user_language: str = "zh"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CoordinatorDecision":
        route = str(data.get("route") or "standard_analysis")
        if route not in _ROUTES:
            route = "standard_analysis"
        return cls(
            route=route,  # type: ignore[arg-type]
            required_agents=_str_list(data.get("required_agents")),
            reason=str(data.get("reason") or ""),
            user_language=str(data.get("user_language") or "zh"),
        )


@dataclass
class WorkbenchToolCall:
    tool_name: str
    purpose: str = ""
    input_summary: str = ""
    output_summary: str = ""
    status: str = "completed"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WorkbenchToolCall":
        return cls(
            tool_name=str(data.get("tool_name") or ""),
            purpose=str(data.get("purpose") or ""),
            input_summary=str(data.get("input_summary") or ""),
            output_summary=str(data.get("output_summary") or ""),
            status=str(data.get("status") or "completed"),
        )


@dataclass
class QuestionEvidencePack:
    task: AnalysisTask
    sql: str = ""
    rows: list[dict[str, Any]] = field(default_factory=list)
    columns: list[str] = field(default_factory=list)
    metrics: list[str] = field(default_factory=list)
    chart_candidates: list[dict[str, Any]] = field(default_factory=list)
    tool_calls: list[WorkbenchToolCall] = field(default_factory=list)
    data_limits: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["task"] = self.task.to_dict()
        data["tool_calls"] = [call.to_dict() for call in self.tool_calls]
        return data

    def to_result_evidence(self) -> dict[str, Any]:
        return {
            "columns": list(self.columns),
            "rows": [dict(row) for row in self.rows],
            "metrics": list(self.metrics),
            "chart_candidates": [dict(candidate) for candidate in self.chart_candidates],
            "data_limits": list(self.data_limits),
            "tool_calls": [call.to_dict() for call in self.tool_calls],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "QuestionEvidencePack":
        raw_task = data.get("task") if isinstance(data.get("task"), dict) else {}
        return cls(
            task=AnalysisTask.from_dict(raw_task),
            sql=str(data.get("sql") or ""),
            rows=_dict_list(data.get("rows")),
            columns=_str_list(data.get("columns")),
            metrics=_str_list(data.get("metrics")),
            chart_candidates=_dict_list(data.get("chart_candidates")),
            tool_calls=[
                WorkbenchToolCall.from_dict(call)
                for call in data.get("tool_calls", [])
                if isinstance(call, dict)
            ],
            data_limits=_str_list(data.get("data_limits")),
        )


@dataclass
class AuditResult:
    supported_facts: list[str] = field(default_factory=list)
    reasonable_inferences: list[str] = field(default_factory=list)
    unsupported_claims: list[str] = field(default_factory=list)
    data_limits: list[str] = field(default_factory=list)
    confidence: str = "medium"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AuditResult":
        return cls(
            supported_facts=_str_list(data.get("supported_facts")),
            reasonable_inferences=_str_list(data.get("reasonable_inferences")),
            unsupported_claims=_str_list(data.get("unsupported_claims")),
            data_limits=_str_list(data.get("data_limits")),
            confidence=str(data.get("confidence") or "medium"),
        )


def _str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def _dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _dict_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [dict(item) for item in value if isinstance(item, dict)]


_ROUTES = {"clarify", "fast_fact", "standard_analysis", "deep_judgment", "reject"}


__all__ = [
    "AnalysisRoute",
    "AnalysisTask",
    "AuditResult",
    "CoordinatorDecision",
    "QuestionEvidencePack",
    "WorkbenchToolCall",
]
