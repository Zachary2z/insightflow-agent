from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any, Literal

from workspaces.analysis_contracts import AnalysisTask, AnalysisRoute, WorkbenchToolCall


EvidenceTaskPurpose = Literal["core_fact", "explanation_support", "trend_or_anomaly_support"]
EvidenceTaskStatus = Literal["planned", "needs_clarification", "skipped", "failed", "executed"]
EvidenceTaskPlanStatus = Literal["planned", "needs_clarification", "limited"]


ONE_SQL_TASK_POLICY = {
    "max_sql_statements": 1,
    "allowed_statement_type": "readonly_select",
    "review_before_execution": True,
    "parallel_review_and_execution_allowed": False,
    "execution_sequence": ["sql_candidate", "sql_review", "approved_sql_execution"],
}


@dataclass
class EvidenceTask:
    task_id: str
    question: str
    purpose: EvidenceTaskPurpose
    metrics: list[str] = field(default_factory=list)
    dimensions: list[str] = field(default_factory=list)
    time_policy: str = ""
    priority: int = 1
    max_rows: int = 20
    status: EvidenceTaskStatus = "planned"
    data_limits: list[str] = field(default_factory=list)
    sql_policy: dict[str, Any] = field(default_factory=lambda: dict(ONE_SQL_TASK_POLICY))

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["sql_policy"] = dict(self.sql_policy or ONE_SQL_TASK_POLICY)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EvidenceTask":
        purpose = str(data.get("purpose") or "core_fact")
        if purpose not in _PURPOSES:
            purpose = "core_fact"
        status = str(data.get("status") or "planned")
        if status not in _STATUSES:
            status = "planned"
        return cls(
            task_id=str(data.get("task_id") or ""),
            question=str(data.get("question") or ""),
            purpose=purpose,  # type: ignore[arg-type]
            metrics=_str_list(data.get("metrics")),
            dimensions=_str_list(data.get("dimensions")),
            time_policy=str(data.get("time_policy") or ""),
            priority=int(data.get("priority") or 1),
            max_rows=int(data.get("max_rows") or 20),
            status=status,  # type: ignore[arg-type]
            data_limits=_str_list(data.get("data_limits")),
            sql_policy=_sql_policy(data.get("sql_policy")),
        )


@dataclass
class EvidenceTaskResult:
    task_id: str
    status: EvidenceTaskStatus = "planned"
    rows: list[dict[str, Any]] = field(default_factory=list)
    columns: list[str] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)
    data_limits: list[str] = field(default_factory=list)
    tool_calls: list[WorkbenchToolCall] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["tool_calls"] = [call.to_dict() for call in self.tool_calls]
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EvidenceTaskResult":
        status = str(data.get("status") or "planned")
        if status not in _STATUSES:
            status = "planned"
        return cls(
            task_id=str(data.get("task_id") or ""),
            status=status,  # type: ignore[arg-type]
            rows=_dict_list(data.get("rows")),
            columns=_str_list(data.get("columns")),
            evidence_refs=_str_list(data.get("evidence_refs")),
            data_limits=_str_list(data.get("data_limits")),
            tool_calls=[
                WorkbenchToolCall.from_dict(call)
                for call in data.get("tool_calls", [])
                if isinstance(call, dict)
            ],
        )


@dataclass
class EvidenceTaskPlan:
    route: AnalysisRoute
    tasks: list[EvidenceTask] = field(default_factory=list)
    max_evidence_tasks: int = 4
    max_parallel_evidence_tasks: int = 3
    status: EvidenceTaskPlanStatus = "planned"
    planner_source: str = "deterministic_business_lens"
    needs_clarification: str = ""
    data_limits: list[str] = field(default_factory=list)
    safety_policy: dict[str, Any] = field(default_factory=lambda: dict(ONE_SQL_TASK_POLICY))

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["tasks"] = [task.to_dict() for task in self.tasks]
        data["safety_policy"] = dict(self.safety_policy or ONE_SQL_TASK_POLICY)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EvidenceTaskPlan":
        route = str(data.get("route") or "standard_analysis")
        if route not in _PLAN_ROUTES:
            route = "standard_analysis"
        status = str(data.get("status") or "planned")
        if status not in _PLAN_STATUSES:
            status = "planned"
        return cls(
            route=route,  # type: ignore[arg-type]
            tasks=[
                EvidenceTask.from_dict(item)
                for item in data.get("tasks", [])
                if isinstance(item, dict)
            ],
            max_evidence_tasks=int(data.get("max_evidence_tasks") or 4),
            max_parallel_evidence_tasks=int(data.get("max_parallel_evidence_tasks") or 3),
            status=status,  # type: ignore[arg-type]
            planner_source=str(data.get("planner_source") or "deterministic_business_lens"),
            needs_clarification=str(data.get("needs_clarification") or ""),
            data_limits=_str_list(data.get("data_limits")),
            safety_policy=_sql_policy(data.get("safety_policy")),
        )


def plan_evidence_tasks(
    task: AnalysisTask | dict[str, Any],
    *,
    route: str,
    max_evidence_tasks: int = 4,
    max_parallel_evidence_tasks: int = 3,
) -> EvidenceTaskPlan:
    analysis_task = task if isinstance(task, AnalysisTask) else AnalysisTask.from_dict(task or {})
    route_name = _route(route)
    lens = analysis_task.business_lens if isinstance(analysis_task.business_lens, dict) else {}
    data_limits = _unique_text([*analysis_task.business_lens.get("data_limits", [])]) if lens else []
    clarification = str(lens.get("clarification_question") or analysis_task.clarification_question or "").strip()

    if route_name == "clarify" or analysis_task.missing_slots or lens.get("needs_clarification"):
        return EvidenceTaskPlan(
            route=route_name,
            tasks=[],
            max_evidence_tasks=max_evidence_tasks,
            max_parallel_evidence_tasks=max_parallel_evidence_tasks,
            status="needs_clarification",
            needs_clarification=clarification or "问题缺少可安全规划证据任务的关键信息。",
            data_limits=data_limits,
        )
    if route_name == "reject":
        return EvidenceTaskPlan(
            route=route_name,
            tasks=[],
            max_evidence_tasks=max_evidence_tasks,
            max_parallel_evidence_tasks=max_parallel_evidence_tasks,
            status="limited",
            data_limits=data_limits or ["请求在 SQL 生成前被拒绝，未规划证据任务。"],
        )

    metrics = _metrics(analysis_task)
    dimensions = _dimensions(analysis_task)
    if not metrics:
        return EvidenceTaskPlan(
            route=route_name,
            tasks=[],
            max_evidence_tasks=max_evidence_tasks,
            max_parallel_evidence_tasks=max_parallel_evidence_tasks,
            status="needs_clarification",
            needs_clarification=clarification or "请补充要分析的指标口径。",
            data_limits=data_limits or ["当前问题没有足够明确的业务指标，未规划证据任务。"],
        )

    if route_name == "fast_fact":
        return EvidenceTaskPlan(
            route="fast_fact",
            tasks=[
                _task(
                    question=analysis_task.resolved_question,
                    purpose="core_fact",
                    metrics=[metrics[0]["label"]],
                    dimensions=dimensions,
                    time_policy=_time_policy(analysis_task),
                    priority=1,
                    max_rows=_max_rows(analysis_task, purpose="core_fact"),
                )
            ],
            max_evidence_tasks=max_evidence_tasks,
            max_parallel_evidence_tasks=max_parallel_evidence_tasks,
        )

    planned: list[EvidenceTask] = []
    for metric in metrics:
        planned.append(
            _task(
                question=_metric_question(analysis_task, metric["label"], dimensions),
                purpose="core_fact",
                metrics=[metric["label"]],
                dimensions=dimensions,
                time_policy=_time_policy(analysis_task, metric),
                priority=1,
                max_rows=_max_rows(analysis_task, purpose="core_fact"),
            )
        )

    if _should_add_efficiency_task(metrics):
        planned.append(
            _task(
                question=_efficiency_question(analysis_task, metrics, dimensions),
                purpose="explanation_support",
                metrics=_efficiency_metric_labels(metrics),
                dimensions=dimensions,
                time_policy=_time_policy(analysis_task),
                priority=2,
                max_rows=20,
            )
        )

    if _should_add_helper_task(analysis_task, route_name) and len(planned) < max_evidence_tasks:
        planned.append(
            _task(
                question=_helper_question(analysis_task, dimensions),
                purpose="trend_or_anomaly_support",
                metrics=[metrics[0]["label"]],
                dimensions=dimensions,
                time_policy=_time_policy(analysis_task, metrics[0]),
                priority=3,
                max_rows=30,
            )
        )

    capped = sorted(planned, key=lambda item: (item.priority, item.task_id))[:max_evidence_tasks]
    limits = list(data_limits)
    if len(planned) > len(capped):
        limits.append(f"证据任务已按优先级限制为最多 {max_evidence_tasks} 个，较低优先级辅助证据留待后续补充。")
    return EvidenceTaskPlan(
        route=route_name,
        tasks=capped,
        max_evidence_tasks=max_evidence_tasks,
        max_parallel_evidence_tasks=max_parallel_evidence_tasks,
        status="limited" if limits else "planned",
        data_limits=_unique_text(limits),
    )


def _task(
    *,
    question: str,
    purpose: EvidenceTaskPurpose,
    metrics: list[str],
    dimensions: list[str],
    time_policy: str,
    priority: int,
    max_rows: int,
) -> EvidenceTask:
    task_id = _task_id([purpose, *metrics, *dimensions])
    return EvidenceTask(
        task_id=task_id,
        question=question,
        purpose=purpose,
        metrics=_unique_text(metrics),
        dimensions=_unique_text(dimensions),
        time_policy=time_policy,
        priority=priority,
        max_rows=max_rows,
    )


def _metrics(task: AnalysisTask) -> list[dict[str, str]]:
    lens = task.business_lens if isinstance(task.business_lens, dict) else {}
    metrics = [
        {
            "label": str(item.get("label") or "").strip(),
            "role": str(item.get("metric_role") or "").strip(),
            "source_table": str(item.get("source_table") or "").strip(),
            "time_field": str(item.get("time_field") or "").strip(),
        }
        for item in lens.get("metrics") or []
        if isinstance(item, dict) and str(item.get("label") or "").strip()
    ]
    if metrics:
        return _dedupe_metric_dicts(metrics)
    return _dedupe_metric_dicts([{"label": str(item), "role": "", "source_table": "", "time_field": ""} for item in task.metrics])


def _dimensions(task: AnalysisTask) -> list[str]:
    lens = task.business_lens if isinstance(task.business_lens, dict) else {}
    labels = [
        str(item.get("label") or "").strip()
        for item in lens.get("dimensions") or []
        if isinstance(item, dict) and str(item.get("label") or "").strip()
    ]
    return _unique_text(labels or task.dimensions)


def _metric_question(task: AnalysisTask, metric: str, dimensions: list[str]) -> str:
    if dimensions:
        return f"按{'、'.join(dimensions)}统计{metric}。"
    return f"统计{metric}。"


def _efficiency_question(task: AnalysisTask, metrics: list[dict[str, str]], dimensions: list[str]) -> str:
    labels = _efficiency_metric_labels(metrics)
    if dimensions:
        return f"按{'、'.join(dimensions)}比较{'、'.join(labels)}并形成效率辅助证据。"
    return f"比较{'、'.join(labels)}并形成效率辅助证据。"


def _helper_question(task: AnalysisTask, dimensions: list[str]) -> str:
    if dimensions:
        return f"按{'、'.join(dimensions)}补充趋势、异常或图表辅助证据。"
    return "补充趋势、异常或图表辅助证据。"


def _should_add_efficiency_task(metrics: list[dict[str, str]]) -> bool:
    roles = {_role(item) for item in metrics}
    labels = {_compact(item["label"]) for item in metrics}
    if {"revenue", "spend"} <= roles:
        return True
    if {"income", "cost"} <= roles:
        return True
    if roles & {"roi", "roas", "efficiency"}:
        return len(metrics) > 1
    return bool({"收入", "营收", "销售额", "revenue", "income"} & labels and {"投放花费", "成本", "spend", "cost"} & labels)


def _should_add_helper_task(task: AnalysisTask, route: AnalysisRoute) -> bool:
    question = _compact(task.resolved_question)
    if route == "deep_judgment":
        return True
    return any(marker in question for marker in ("趋势", "变化", "异常", "图表", "chart", "trend", "anomaly"))


def _efficiency_metric_labels(metrics: list[dict[str, str]]) -> list[str]:
    labels = []
    for item in metrics:
        if _role(item) in {"revenue", "income", "spend", "cost", "roi", "roas", "efficiency"}:
            labels.append(item["label"])
    return _unique_text(labels or [item["label"] for item in metrics])


def _role(metric: dict[str, str]) -> str:
    role = str(metric.get("role") or "").lower()
    label = _compact(metric.get("label"))
    if role == "revenue_like" or label in {"收入", "营收", "销售额", "revenue", "sales", "gmv"}:
        return "revenue"
    if role == "spend_like" or label in {"投放花费", "投放金额", "投放成本", "成本", "spend", "cost"}:
        return "spend"
    if label in {"income"}:
        return "income"
    if label in {"roi", "roas", "投放效率", "效率"}:
        return label if label in {"roi", "roas"} else "efficiency"
    return role or label


def _time_policy(task: AnalysisTask, metric: dict[str, str] | None = None) -> str:
    lens = task.business_lens if isinstance(task.business_lens, dict) else {}
    note = str(lens.get("time_policy_note") or "").strip()
    if metric and metric.get("time_field"):
        detail = f"{metric['label']}使用 {metric.get('source_table', '')}.{metric['time_field']} 作为业务时间字段。"
        return f"{note} {detail}".strip()
    if note:
        return note
    raw_text = task.time_range.get("raw_text") if isinstance(task.time_range, dict) else ""
    return str(raw_text or "").strip()


def _max_rows(task: AnalysisTask, *, purpose: EvidenceTaskPurpose) -> int:
    if purpose != "core_fact":
        return 20
    if task.dimensions or _dimensions(task):
        return 20
    return 1


def _route(value: str) -> AnalysisRoute:
    text = str(value or "standard_analysis")
    if text == "report":
        text = "deep_judgment"
    if text not in _PLAN_ROUTES:
        text = "standard_analysis"
    return text  # type: ignore[return-value]


def _task_id(parts: list[str]) -> str:
    text = "_".join(_compact(part) for part in parts if _compact(part)) or "evidence_task"
    text = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "_", text).strip("_")
    return text[:80] or "evidence_task"


def _sql_policy(value: Any) -> dict[str, Any]:
    policy = dict(value) if isinstance(value, dict) else {}
    return {**ONE_SQL_TASK_POLICY, **policy}


def _str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def _dict_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [dict(item) for item in value if isinstance(item, dict)]


def _dedupe_metric_dicts(items: list[dict[str, str]]) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    seen = set()
    for item in items:
        label = str(item.get("label") or "").strip()
        key = _compact(label)
        if label and key not in seen:
            seen.add(key)
            result.append({**item, "label": label})
    return result


def _unique_text(items: list[Any]) -> list[str]:
    result: list[str] = []
    seen = set()
    for item in items:
        text = str(item or "").strip()
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return result


def _compact(value: Any) -> str:
    return re.sub(r"[\s_\-（）()。,.，:：]+", "", str(value or "").lower())


_PURPOSES = {"core_fact", "explanation_support", "trend_or_anomaly_support"}
_STATUSES = {"planned", "needs_clarification", "skipped", "failed", "executed"}
_PLAN_STATUSES = {"planned", "needs_clarification", "limited"}
_PLAN_ROUTES = {"clarify", "fast_fact", "standard_analysis", "deep_judgment", "reject"}


__all__ = [
    "EvidenceTask",
    "EvidenceTaskPlan",
    "EvidenceTaskResult",
    "ONE_SQL_TASK_POLICY",
    "plan_evidence_tasks",
]
