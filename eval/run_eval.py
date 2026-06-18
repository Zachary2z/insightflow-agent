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

DEFAULT_CASES_PATH = ROOT / "eval" / "test_questions.json"
DEFAULT_REPORT_PATH = ROOT / "eval" / "report.md"
DEFAULT_TRACE_DIR = ROOT / "logs" / "traces" / "eval"
DEFAULT_DB_PATH = ROOT / "data" / "ecommerce.db"


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
    )
    failures = _expectation_failures(case, result)
    latency_ms = int((perf_counter() - started_at) * 1000)

    return {
        "case_id": case["id"],
        "question": case["question"],
        "category": case.get("category", "unknown"),
        "passed": not failures,
        "failures": failures,
        "status": result.get("status"),
        "review_approved": result.get("review_result", {}).get("approved"),
        "execution_success": result.get("execution_result", {}).get("success"),
        "retry_count": result.get("retry_count", 0),
        "trace_path": result.get("trace_path", ""),
        "tool_call_count": len(result.get("trace", [])),
        "latency_ms": latency_ms,
        "failure_type": _failure_type(result, failures),
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
        "average_tool_calls": round(
            sum(result["tool_call_count"] for result in case_results) / total if total else 0,
            2,
        ),
        "average_latency_ms": round(sum(result["latency_ms"] for result in case_results) / total if total else 0, 2),
        "failure_type_distribution": dict(Counter(result["failure_type"] for result in case_results)),
        "report_path": str(report_path),
        "case_results": case_results,
    }


def _markdown_report(summary: dict[str, Any]) -> str:
    lines = [
        "# InsightFlow Agent P0 Eval Report",
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
        f"- Average tool calls: {summary['average_tool_calls']}",
        f"- Average latency ms: {summary['average_latency_ms']}",
        "",
        "## Failure Type Distribution",
        "",
    ]
    for failure_type, count in summary["failure_type_distribution"].items():
        lines.append(f"- {failure_type}: {count}")

    lines.extend(["", "## Case Results", "", "| Case | Category | Passed | Status | Trace | Failures |", "|---|---|---:|---|---|---|"])
    for result in summary["case_results"]:
        failures = "; ".join(result["failures"]) if result["failures"] else ""
        lines.append(
            f"| {result['case_id']} | {result['category']} | {result['passed']} | {result['status']} | {result['trace_path']} | {failures} |"
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
