from pathlib import Path


def test_save_report_writes_markdown_file(tmp_path):
    from tools.report_tool import save_report

    result = save_report(
        run_id="run_report_test",
        report_content="# InsightFlow Report\n\nTrace path: logs/traces/run_report_test.json",
        output_dir=tmp_path,
    )

    report_path = Path(result["report_path"])
    assert result["success"] is True
    assert report_path.exists()
    assert report_path.name == "run_report_test_report.md"
    assert "InsightFlow Report" in report_path.read_text(encoding="utf-8")
    assert result["trace_event"]["tool_name"] == "save_report"
    assert result["trace_event"]["status"] == "success"


def test_save_report_sanitizes_run_id(tmp_path):
    from tools.report_tool import save_report

    result = save_report(
        run_id="../unsafe run",
        report_content="# Safe Report",
        output_dir=tmp_path,
    )

    report_path = Path(result["report_path"])
    assert result["success"] is True
    assert report_path.parent == tmp_path
    assert report_path.name == "unsafe_run_report.md"


def test_save_report_returns_error_for_empty_content(tmp_path):
    from tools.report_tool import save_report

    result = save_report(run_id="run_empty", report_content="", output_dir=tmp_path)

    assert result["success"] is False
    assert result["report_path"] == ""
    assert "report_content is required" in result["error"]
    assert result["trace_event"]["status"] == "error"
    assert result["trace_event"]["error_type"] == "report_save_error"
