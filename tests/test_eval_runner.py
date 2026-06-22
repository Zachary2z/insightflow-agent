import importlib.util
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CASES_PATH = ROOT / "eval" / "test_questions.json"
RUNNER_PATH = ROOT / "eval" / "run_eval.py"


def _load_runner():
    spec = importlib.util.spec_from_file_location("insightflow_eval_runner", RUNNER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_eval_cases_file_has_p0_and_realistic_p9_cases_with_required_fields():
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))

    assert len(cases) >= 30
    categories = {case["category"] for case in cases}
    assert {
        "basic_query",
        "sales_ranking",
        "category_stats",
        "city_stats",
        "dangerous_sql_block",
        "metric_guardrail",
        "sql_repair",
        "gmv_decline",
        "category_anomaly",
        "regional_performance",
        "top_bottom_products",
        "refund_risk",
        "business_weekly_report",
        "visualization_delivery",
        "action_suggestion",
        "unsafe_sensitive_rejection",
        "provider_unavailable_fallback",
        "provider_validation_error",
    } <= categories
    assert any(case["id"].startswith("p9_") for case in cases)
    for case in cases:
        assert {"id", "question", "category", "expectations"} <= set(case)
        assert case["id"].startswith(("p0_", "p9_"))
        assert case["question"]
        if case["id"].startswith("p9_"):
            assert case.get("business_scenario")
            assert isinstance(case.get("requires", []), list)


def test_run_eval_cases_returns_p9_summary_metrics_and_writes_report(tmp_path):
    runner = _load_runner()

    cases = runner.load_cases(CASES_PATH)
    summary = runner.run_eval_cases(cases, trace_dir=tmp_path / "traces", report_path=tmp_path / "report.md")

    assert summary["total_cases"] >= 30
    assert summary["passed_cases"] == summary["total_cases"]
    assert summary["failed_cases"] == 0
    assert summary["sql_execution_success_rate"] >= 0.7
    assert summary["dangerous_sql_block_rate"] == 1.0
    assert summary["sql_repair_success_rate"] == 1.0
    assert summary["metric_definition_accuracy"] >= 0.8
    assert summary["average_trace_event_count"] > 0
    assert summary["average_tool_call_count"] > 0
    assert summary["provider_called_cases"] >= 3
    assert summary["fallback_used_cases"] >= 2
    assert summary["visualization_external_tool_called_cases"] >= 2
    assert summary["visualization_delivery_tool_distribution"]["excel_exporter"] >= 1
    assert summary["visualization_delivery_tool_distribution"]["powerbi_publisher_mock"] >= 1
    assert summary["action_delivery_tool_distribution"]["jira_ticket_mock"] >= 1
    assert summary["action_requires_approval_cases"] >= 1
    assert summary["evidence_success_rate"] >= 0.8
    assert "unsupported_claim_rate_average" in summary
    assert summary["validation_error_cases"] >= 1
    assert summary["provider_error_cases"] >= 1
    assert "failure_type_distribution" in summary
    assert "p9_001" in {result["case_id"] for result in summary["case_results"]}
    assert Path(summary["report_path"]).is_file()
    report_text = Path(summary["report_path"]).read_text(encoding="utf-8")
    assert "InsightFlow Agent P9 Eval Report" in report_text
    assert "Provider / Fallback / External Tool Metrics" in report_text


def test_eval_runner_does_not_require_real_api_key(monkeypatch, tmp_path):
    runner = _load_runner()
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("INSIGHTFLOW_USE_PROVIDER_VISUALIZATION_AGENT", raising=False)

    cases = [
        case
        for case in runner.load_cases(CASES_PATH)
        if case["id"] in {"p9_007", "p9_008", "p9_011", "p9_012"}
    ]
    summary = runner.run_eval_cases(cases, trace_dir=tmp_path / "traces", report_path=tmp_path / "report.md")

    assert summary["total_cases"] == 4
    assert summary["failed_cases"] == 0
    assert any(result["provider_called"] for result in summary["case_results"])


def test_visualization_and_action_tool_traces_are_statistically_visible(tmp_path):
    runner = _load_runner()
    cases = [
        case
        for case in runner.load_cases(CASES_PATH)
        if case["id"] in {"p9_007", "p9_008", "p9_009"}
    ]

    summary = runner.run_eval_cases(cases, trace_dir=tmp_path / "traces", report_path=tmp_path / "report.md")

    assert summary["visualization_delivery_tool_distribution"]["excel_exporter"] == 1
    assert summary["visualization_delivery_tool_distribution"]["powerbi_publisher_mock"] == 1
    assert summary["action_delivery_tool_distribution"]["jira_ticket_mock"] == 1
    assert all(result["trace_event_count"] > 0 for result in summary["case_results"])


def test_sensitive_p9_case_is_blocked_before_sql_execution(tmp_path):
    runner = _load_runner()
    case = next(case for case in runner.load_cases(CASES_PATH) if case["id"] == "p9_010")

    result = runner.evaluate_case(case, trace_dir=tmp_path)

    assert result["passed"] is True
    assert result["status"] == "failed"
    assert result["review_approved"] is False
    assert result["execution_success"] is None
    assert result["unsafe_blocked"] is True


def test_evaluate_case_detects_failed_expectation(tmp_path):
    runner = _load_runner()
    case = {
        "id": "p0_fake_failure",
        "question": "最近 30 天销售额最高的 5 个商品是什么？",
        "category": "sales_ranking",
        "expectations": {
            "status": "failed",
            "review_approved": False,
        },
    }

    result = runner.evaluate_case(case, trace_dir=tmp_path)

    assert result["passed"] is False
    assert result["failures"]
    assert result["case_id"] == "p0_fake_failure"


def test_run_eval_script_executes_from_repo_root(tmp_path):
    completed = subprocess.run(
        [
            sys.executable,
            str(RUNNER_PATH),
            "--trace-dir",
            str(tmp_path / "traces"),
            "--report-path",
            str(tmp_path / "report.md"),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert (tmp_path / "report.md").is_file()
