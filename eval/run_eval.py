from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from time import perf_counter
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from graph.workflow import run_workflow
from agents.action_executor import run_action_executor_agent
from agents.action_planner import run_action_planner_agent
from agents.risk_assessor import run_risk_assessor_agent
from llm_ops.provider import MockLLMProvider
from tools.approval_tool import record_approval

DEFAULT_CASES_PATH = ROOT / "eval" / "test_questions.json"
DEFAULT_REPORT_PATH = ROOT / "eval" / "report.md"
DEFAULT_TRACE_DIR = ROOT / "logs" / "traces" / "eval"
DEFAULT_DB_PATH = ROOT / "data" / "ecommerce.db"
ARTIFACT_HYGIENE_NOTE = (
    "Do not commit generated eval reports, trace files, action DBs, or chart/workbook outputs. "
    "Default generated paths include eval/report.md, logs/traces/eval, data/action_ops.db, "
    "reports/charts/*, and reports/markdown/*."
)


def load_cases(path: str | Path = DEFAULT_CASES_PATH) -> list[dict[str, Any]]:
    with Path(path).open("r", encoding="utf-8") as file:
        cases = json.load(file)
    if not isinstance(cases, list):
        raise ValueError("Eval cases file must contain a list.")
    return cases


def _trace_nodes(result: dict[str, Any]) -> list[str]:
    return [event.get("node", "") for event in result.get("trace", [])]


def _contains_all(text: str, snippets: list[str]) -> list[str]:
    return [snippet for snippet in snippets if snippet not in text]


def _collect_source_records(result: dict[str, Any]) -> list[dict[str, Any]]:
    records = []
    for key in (
        "question_understanding",
        "clarification_result",
        "sql_planning",
        "analysis_plan",
        "llm_sql_enhancement",
        "claim_typing_result",
        "visualization_decision",
        "action_plan",
        "action_draft_result",
    ):
        value = result.get(key)
        if isinstance(value, dict):
            records.append(value)
    records.extend(event for event in result.get("trace", []) if isinstance(event, dict))
    return records


def _any_flag(result: dict[str, Any], flag: str) -> bool:
    return any(bool(record.get(flag)) for record in _collect_source_records(result))


def _collect_messages(result: dict[str, Any], key: str) -> list[str]:
    messages = []
    for record in _collect_source_records(result):
        value = str(record.get(key, "") or "").strip()
        if value:
            messages.append(value)
    return messages


def _visualization_tool_id(result: dict[str, Any]) -> str:
    return (
        result.get("visualization_delivery_result", {}).get("delivery_tool_id")
        or result.get("visualization_decision", {}).get("delivery_tool_id")
        or result.get("visualization_trace", {}).get("delivery_tool_id")
        or ""
    )


def _visualization_artifact(result: dict[str, Any]) -> dict[str, str]:
    delivery = result.get("visualization_delivery_result", {})
    path = str(delivery.get("artifact_path") or delivery.get("chart_path") or "")
    url = str(delivery.get("artifact_url") or "")
    if url.startswith("mock://powerbi/"):
        artifact_type = "mock_external_bi_url"
    elif path.endswith(".xlsx"):
        artifact_type = "xlsx"
    elif path.endswith(".png"):
        artifact_type = "png"
    elif path:
        artifact_type = Path(path).suffix.lstrip(".") or "local_file"
    else:
        artifact_type = ""
    return {"type": artifact_type, "path": path, "url": url}


def _action_delivery_tool_ids(result: dict[str, Any]) -> list[str]:
    ids = []
    for delivery in result.get("action_execution_result", {}).get("delivery_results", []):
        tool_id = delivery.get("delivery_tool_id")
        if tool_id:
            ids.append(str(tool_id))
    for action in result.get("created_actions", []):
        tool_id = action.get("delivery_tool_id")
        if tool_id:
            ids.append(str(tool_id))
    return sorted(set(ids))


def _tool_call_count(result: dict[str, Any]) -> int:
    return sum(1 for event in result.get("trace", []) if event.get("tool_name"))


def _provider_from_case(case: dict[str, Any], key: str) -> MockLLMProvider | None:
    if key not in case:
        return None
    return MockLLMProvider(case[key])


def _run_action_eval_if_requested(
    case: dict[str, Any],
    result: dict[str, Any],
    trace_dir: str | Path,
) -> dict[str, Any]:
    if "action_provider_output" not in case:
        return result

    action_db_path = Path(trace_dir) / f"{case['id']}_action_ops.db"
    action_db_path.parent.mkdir(parents=True, exist_ok=True)
    state = {**result, "action_db_path": action_db_path}
    state = run_action_planner_agent(
        state,
        action_db_path=action_db_path,
        action_draft_provider=MockLLMProvider(case["action_provider_output"]),
    )
    state = run_risk_assessor_agent(state)
    if case.get("approve_actions", False):
        approval = record_approval(
            action_db_path,
            {
                "run_id": state.get("run_id", case["id"]),
                "approval_status": "approved",
                "approved_by": "eval_runner",
                "reason": "Approved P9 eval mock action delivery.",
            },
        )
        state["approval_status"] = approval["approval_status"]
        state["approval_record"] = approval
    return run_action_executor_agent(state)


def _expectation_failures(case: dict[str, Any], result: dict[str, Any]) -> list[str]:
    expectations = case.get("expectations", {})
    failures: list[str] = []

    if "status" in expectations and result.get("status") != expectations["status"]:
        failures.append(f"status expected {expectations['status']} got {result.get('status')}")

    review_approved = result.get("review_result", {}).get("approved")
    if "review_approved" in expectations and review_approved != expectations["review_approved"]:
        failures.append(f"review_approved expected {expectations['review_approved']} got {review_approved}")

    execution_success = result.get("execution_result", {}).get("success")
    if "execution_success" in expectations and execution_success != expectations["execution_success"]:
        failures.append(f"execution_success expected {expectations['execution_success']} got {execution_success}")

    if "retry_count" in expectations and result.get("retry_count") != expectations["retry_count"]:
        failures.append(f"retry_count expected {expectations['retry_count']} got {result.get('retry_count')}")

    if "scenario_type" in expectations and result.get("scenario_type") != expectations["scenario_type"]:
        failures.append(f"scenario_type expected {expectations['scenario_type']} got {result.get('scenario_type')}")

    if "provider_called" in expectations and _any_flag(result, "provider_called") != expectations["provider_called"]:
        failures.append(f"provider_called expected {expectations['provider_called']}")

    if "fallback_used" in expectations and _any_flag(result, "fallback_used") != expectations["fallback_used"]:
        failures.append(f"fallback_used expected {expectations['fallback_used']}")

    if "visualization_delivery_tool_id" in expectations:
        actual_tool = _visualization_tool_id(result)
        if actual_tool != expectations["visualization_delivery_tool_id"]:
            failures.append(f"visualization_delivery_tool_id expected {expectations['visualization_delivery_tool_id']} got {actual_tool}")

    if "visualization_external_tool_called" in expectations:
        actual_called = bool(result.get("visualization_delivery_result", {}).get("external_tool_called"))
        if actual_called != expectations["visualization_external_tool_called"]:
            failures.append(f"visualization_external_tool_called expected {expectations['visualization_external_tool_called']} got {actual_called}")

    for expected_tool in expectations.get("action_delivery_tool_ids", []):
        if expected_tool not in _action_delivery_tool_ids(result):
            failures.append(f"action delivery missing tool: {expected_tool}")

    if "action_requires_approval" in expectations:
        actual_approval = bool(result.get("risk_assessment", {}).get("requires_approval"))
        if actual_approval != expectations["action_requires_approval"]:
            failures.append(f"action_requires_approval expected {expectations['action_requires_approval']} got {actual_approval}")

    if "evidence_success" in expectations:
        actual_evidence = result.get("evidence_result", {}).get("success")
        if actual_evidence != expectations["evidence_success"]:
            failures.append(f"evidence_success expected {expectations['evidence_success']} got {actual_evidence}")

    if "unsafe_blocked" in expectations:
        actual_unsafe = result.get("status") == "failed" and result.get("execution_result", {}) in ({}, None)
        if actual_unsafe != expectations["unsafe_blocked"]:
            failures.append(f"unsafe_blocked expected {expectations['unsafe_blocked']} got {actual_unsafe}")

    artifact = _visualization_artifact(result)
    if "visualization_artifact_type" in expectations and artifact["type"] != expectations["visualization_artifact_type"]:
        failures.append(f"visualization_artifact_type expected {expectations['visualization_artifact_type']} got {artifact['type']}")

    if "artifact_url_prefix" in expectations and not artifact["url"].startswith(expectations["artifact_url_prefix"]):
        failures.append(f"artifact_url prefix expected {expectations['artifact_url_prefix']} got {artifact['url']}")

    for snippet in expectations.get("validation_error_contains", []):
        if not any(snippet in message for message in _collect_messages(result, "validation_error")):
            failures.append(f"validation_error missing snippet: {snippet}")

    for snippet in expectations.get("provider_error_contains", []):
        if not any(snippet in message for message in _collect_messages(result, "provider_error")):
            failures.append(f"provider_error missing snippet: {snippet}")

    sql_text = result.get("generated_sql", "")
    missing_sql = _contains_all(sql_text, expectations.get("sql_contains", []))
    if missing_sql:
        failures.append(f"generated_sql missing snippets: {missing_sql}")

    fixed_sql = result.get("fixed_sql", "")
    missing_fixed = _contains_all(fixed_sql, expectations.get("fixed_sql_contains", []))
    if missing_fixed:
        failures.append(f"fixed_sql missing snippets: {missing_fixed}")

    nodes = _trace_nodes(result)
    for expected_node in expectations.get("trace_nodes", []):
        if expected_node not in nodes:
            failures.append(f"trace missing node: {expected_node}")
    for absent_node in expectations.get("trace_nodes_absent", []):
        if absent_node in nodes:
            failures.append(f"trace should not include node: {absent_node}")

    if not result.get("trace_path"):
        failures.append("trace_path missing")

    return failures


def _failure_type(result: dict[str, Any], failures: list[str]) -> str:
    if failures:
        return "expectation_failed"
    if result.get("status") == "completed":
        return "none"
    if result.get("review_result") and not result["review_result"].get("approved"):
        return "review_rejected"
    if result.get("execution_result") and not result["execution_result"].get("success"):
        return "execution_failed"
    return "workflow_failed"


def evaluate_case(
    case: dict[str, Any],
    db_path: str | Path = DEFAULT_DB_PATH,
    trace_dir: str | Path = DEFAULT_TRACE_DIR,
) -> dict[str, Any]:
    started_at = perf_counter()
    result = run_workflow(
        case["question"],
        db_path=db_path,
        trace_dir=trace_dir,
        run_id=case["id"],
        session_id=f"eval_{case['id']}",
        initial_sql=case.get("initial_sql"),
        visualization_agent_provider=_provider_from_case(case, "visualization_provider_output"),
        analysis_planner_provider=_provider_from_case(case, "analysis_provider_output"),
    )
    result = _run_action_eval_if_requested(case, result, trace_dir)
    failures = _expectation_failures(case, result)
    latency_ms = int((perf_counter() - started_at) * 1000)
    visualization_artifact = _visualization_artifact(result)
    validation_errors = _collect_messages(result, "validation_error")
    provider_errors = _collect_messages(result, "provider_error")

    return {
        "case_id": case["id"],
        "question": case["question"],
        "category": case.get("category", "unknown"),
        "business_scenario": case.get("business_scenario", ""),
        "passed": not failures,
        "failures": failures,
        "status": result.get("status"),
        "review_approved": result.get("review_result", {}).get("approved"),
        "execution_success": result.get("execution_result", {}).get("success"),
        "retry_count": result.get("retry_count", 0),
        "trace_path": result.get("trace_path", ""),
        "trace_event_count": len(result.get("trace", [])),
        "tool_call_count": _tool_call_count(result),
        "latency_ms": latency_ms,
        "failure_type": _failure_type(result, failures),
        "provider_called": _any_flag(result, "provider_called"),
        "fallback_used": _any_flag(result, "fallback_used"),
        "visualization_delivery_tool_id": _visualization_tool_id(result),
        "visualization_external_tool_called": bool(result.get("visualization_delivery_result", {}).get("external_tool_called")),
        "visualization_artifact_type": visualization_artifact["type"],
        "visualization_artifact_path": visualization_artifact["path"],
        "visualization_artifact_url": visualization_artifact["url"],
        "action_delivery_tool_ids": _action_delivery_tool_ids(result),
        "action_requires_approval": bool(result.get("risk_assessment", {}).get("requires_approval")),
        "evidence_success": result.get("evidence_result", {}).get("success"),
        "unsupported_claim_rate": result.get("evidence_result", {}).get("unsupported_claim_rate", 0.0),
        "validation_errors": validation_errors,
        "provider_errors": provider_errors,
        "unsafe_blocked": result.get("status") == "failed" and result.get("execution_result", {}) in ({}, None),
    }


def _rate(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return round(numerator / denominator, 4)


def _summarize(case_results: list[dict[str, Any]], report_path: Path) -> dict[str, Any]:
    total = len(case_results)
    passed = sum(1 for result in case_results if result["passed"])
    execution_cases = [result for result in case_results if result["execution_success"] is not None]
    first_pass_cases = [result for result in execution_cases if result["retry_count"] == 0]
    repair_cases = [result for result in case_results if result["category"] == "sql_repair" and result["retry_count"] > 0]
    dangerous_cases = [result for result in case_results if result["category"] == "dangerous_sql_block"]
    metric_cases = [result for result in case_results if result["category"] == "metric_guardrail"]
    visualization_tools = Counter(
        result["visualization_delivery_tool_id"]
        for result in case_results
        if result.get("visualization_delivery_tool_id")
    )
    action_tools = Counter(
        tool_id
        for result in case_results
        for tool_id in result.get("action_delivery_tool_ids", [])
    )
    evidence_cases = [result for result in case_results if result.get("evidence_success") is not None]

    return {
        "total_cases": total,
        "passed_cases": passed,
        "failed_cases": total - passed,
        "pass_rate": _rate(passed, total),
        "sql_execution_success_rate": _rate(
            sum(1 for result in execution_cases if result["execution_success"] is True),
            len(execution_cases),
        ),
        "sql_first_pass_success_rate": _rate(
            sum(1 for result in first_pass_cases if result["execution_success"] is True),
            len(first_pass_cases),
        ),
        "sql_repair_success_rate": _rate(
            sum(1 for result in repair_cases if result["passed"] and result["execution_success"] is True),
            len(repair_cases),
        ),
        "dangerous_sql_block_rate": _rate(
            sum(1 for result in dangerous_cases if result["passed"] and result["review_approved"] is False),
            len(dangerous_cases),
        ),
        "metric_definition_accuracy": _rate(sum(1 for result in metric_cases if result["passed"]), len(metric_cases)),
        "average_trace_event_count": round(sum(result["trace_event_count"] for result in case_results) / total if total else 0, 2),
        "average_tool_call_count": round(sum(result["tool_call_count"] for result in case_results) / total if total else 0, 2),
        "average_tool_calls": round(sum(result["trace_event_count"] for result in case_results) / total if total else 0, 2),
        "average_latency_ms": round(sum(result["latency_ms"] for result in case_results) / total if total else 0, 2),
        "provider_called_cases": sum(1 for result in case_results if result.get("provider_called")),
        "fallback_used_cases": sum(1 for result in case_results if result.get("fallback_used")),
        "visualization_external_tool_called_cases": sum(
            1 for result in case_results if result.get("visualization_external_tool_called")
        ),
        "visualization_delivery_tool_distribution": dict(visualization_tools),
        "visualization_artifact_type_distribution": dict(
            Counter(result["visualization_artifact_type"] for result in case_results if result.get("visualization_artifact_type"))
        ),
        "action_delivery_tool_distribution": dict(action_tools),
        "action_requires_approval_cases": sum(1 for result in case_results if result.get("action_requires_approval")),
        "evidence_success_rate": _rate(sum(1 for result in evidence_cases if result.get("evidence_success")), len(evidence_cases)),
        "unsupported_claim_rate_average": round(
            sum(float(result.get("unsupported_claim_rate") or 0.0) for result in evidence_cases) / len(evidence_cases)
            if evidence_cases
            else 0.0,
            4,
        ),
        "validation_error_cases": sum(1 for result in case_results if result.get("validation_errors")),
        "provider_error_cases": sum(1 for result in case_results if result.get("provider_errors")),
        "failure_type_distribution": dict(Counter(result["failure_type"] for result in case_results)),
        "artifact_hygiene_note": ARTIFACT_HYGIENE_NOTE,
        "report_path": str(report_path),
        "case_results": case_results,
    }


def _markdown_report(summary: dict[str, Any]) -> str:
    lines = [
        "# InsightFlow Agent P9 Eval Report",
        "",
        "## Summary",
        "",
        f"- Total cases: {summary['total_cases']}",
        f"- Passed cases: {summary['passed_cases']}",
        f"- Failed cases: {summary['failed_cases']}",
        f"- Pass rate: {summary['pass_rate']:.2%}",
        f"- SQL execution success rate: {summary['sql_execution_success_rate']:.2%}",
        f"- SQL first-pass success rate: {summary['sql_first_pass_success_rate']:.2%}",
        f"- SQL repair success rate: {summary['sql_repair_success_rate']:.2%}",
        f"- Dangerous SQL block rate: {summary['dangerous_sql_block_rate']:.2%}",
        f"- Metric definition accuracy: {summary['metric_definition_accuracy']:.2%}",
        f"- Average trace events: {summary['average_trace_event_count']}",
        f"- Average tool calls: {summary['average_tool_call_count']}",
        f"- Average latency ms: {summary['average_latency_ms']}",
        "",
        "## Artifact Hygiene",
        "",
        summary["artifact_hygiene_note"],
        "",
        "## Provider / Fallback / External Tool Metrics",
        "",
        f"- Provider-called cases: {summary['provider_called_cases']}",
        f"- Fallback-used cases: {summary['fallback_used_cases']}",
        f"- Visualization external-tool-called cases: {summary['visualization_external_tool_called_cases']}",
        f"- Action requires-approval cases: {summary['action_requires_approval_cases']}",
        f"- Evidence success rate: {summary['evidence_success_rate']:.2%}",
        f"- Average unsupported claim rate: {summary['unsupported_claim_rate_average']:.2%}",
        f"- Validation-error cases: {summary['validation_error_cases']}",
        f"- Provider-error cases: {summary['provider_error_cases']}",
        "",
        "## Failure Type Distribution",
        "",
    ]
    for failure_type, count in summary["failure_type_distribution"].items():
        lines.append(f"- {failure_type}: {count}")

    lines.extend(
        [
            "",
            "## Case Results",
            "",
            "| Case | Category | Passed | Status | Provider | Fallback | Viz Tool | Action Tools | Trace Events | Failures |",
            "|---|---|---:|---|---:|---:|---|---|---:|---|",
        ]
    )
    for result in summary["case_results"]:
        failures = "; ".join(result["failures"]) if result["failures"] else ""
        lines.append(
            f"| {result['case_id']} | {result['category']} | {result['passed']} | {result['status']} | "
            f"{result['provider_called']} | {result['fallback_used']} | {result['visualization_delivery_tool_id']} | "
            f"{','.join(result['action_delivery_tool_ids'])} | {result['trace_event_count']} | {failures} |"
        )
    lines.append("")
    return "\n".join(lines)


def write_report(summary: dict[str, Any], report_path: str | Path = DEFAULT_REPORT_PATH) -> Path:
    path = Path(report_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_markdown_report(summary), encoding="utf-8")
    return path


def run_eval_cases(
    cases: list[dict[str, Any]],
    db_path: str | Path = DEFAULT_DB_PATH,
    trace_dir: str | Path = DEFAULT_TRACE_DIR,
    report_path: str | Path = DEFAULT_REPORT_PATH,
) -> dict[str, Any]:
    report = Path(report_path)
    results = [evaluate_case(case, db_path=db_path, trace_dir=trace_dir) for case in cases]
    summary = _summarize(results, report)
    write_report(summary, report)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Run InsightFlow Agent P0 eval cases.")
    parser.add_argument("--cases", default=str(DEFAULT_CASES_PATH))
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--trace-dir", default=str(DEFAULT_TRACE_DIR))
    parser.add_argument("--report-path", default=str(DEFAULT_REPORT_PATH))
    args = parser.parse_args()

    cases = load_cases(args.cases)
    summary = run_eval_cases(cases, db_path=args.db_path, trace_dir=args.trace_dir, report_path=args.report_path)
    print(json.dumps({key: value for key, value in summary.items() if key != "case_results"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
