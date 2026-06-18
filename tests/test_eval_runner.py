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


def test_eval_cases_file_has_20_p0_cases_with_required_fields():
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))

    assert len(cases) == 20
    categories = {case["category"] for case in cases}
    assert {
        "basic_query",
        "sales_ranking",
        "category_stats",
        "city_stats",
        "dangerous_sql_block",
        "metric_guardrail",
        "sql_repair",
    } <= categories
    for case in cases:
        assert {"id", "question", "category", "expectations"} <= set(case)
        assert case["id"].startswith("p0_")
        assert case["question"]


def test_run_eval_cases_returns_summary_and_writes_report(tmp_path):
    runner = _load_runner()

    cases = runner.load_cases(CASES_PATH)
    summary = runner.run_eval_cases(cases, trace_dir=tmp_path / "traces", report_path=tmp_path / "report.md")

    assert summary["total_cases"] == 20
    assert summary["passed_cases"] == 20
    assert summary["failed_cases"] == 0
    assert summary["sql_execution_success_rate"] >= 0.7
    assert summary["dangerous_sql_block_rate"] == 1.0
    assert summary["sql_repair_success_rate"] == 1.0
    assert summary["metric_definition_accuracy"] >= 0.8
    assert summary["average_tool_calls"] > 0
    assert "failure_type_distribution" in summary
    assert Path(summary["report_path"]).is_file()
    assert "InsightFlow Agent P0 Eval Report" in Path(summary["report_path"]).read_text(encoding="utf-8")


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
