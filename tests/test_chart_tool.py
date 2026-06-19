from pathlib import Path


def _ranking_data():
    return {
        "columns": ["product_name", "gmv"],
        "rows": [["Laptop Pro 14", 511248.56], ["Camera A", 456050.99]],
    }


def _trend_data():
    return {
        "columns": ["month", "gmv"],
        "rows": [["2026-01", 1200.0], ["2026-02", 1800.0], ["2026-03", 1500.0]],
    }


def test_generate_chart_creates_bar_chart_file(tmp_path):
    from tools.chart_tool import generate_chart

    result = generate_chart(
        data=_ranking_data(),
        chart_spec={
            "chart_type": "bar",
            "x": "product_name",
            "y": "gmv",
            "title": "Top Products by GMV",
            "run_id": "run_chart_test",
        },
        output_dir=tmp_path,
    )

    chart_path = Path(result["chart_path"])
    assert result["success"] is True
    assert result["chart_type"] == "bar"
    assert chart_path.exists()
    assert chart_path.suffix == ".png"
    assert chart_path.stat().st_size > 0
    assert result["trace_event"]["tool_name"] == "generate_chart"
    assert result["trace_event"]["status"] == "success"


def test_generate_chart_creates_line_chart_file(tmp_path):
    from tools.chart_tool import generate_chart

    result = generate_chart(
        data=_trend_data(),
        chart_spec={
            "chart_type": "line",
            "x": "month",
            "y": "gmv",
            "title": "Monthly GMV Trend",
            "run_id": "run_chart_test",
        },
        output_dir=tmp_path,
    )

    chart_path = Path(result["chart_path"])
    assert result["success"] is True
    assert result["chart_type"] == "line"
    assert chart_path.exists()
    assert chart_path.stat().st_size > 0


def test_generate_chart_returns_error_for_invalid_input(tmp_path):
    from tools.chart_tool import generate_chart

    result = generate_chart(
        data={"columns": ["product_name"], "rows": [["Laptop Pro 14"]]},
        chart_spec={"chart_type": "scatter", "x": "product_name", "y": "gmv"},
        output_dir=tmp_path,
    )

    assert result["success"] is False
    assert result["chart_path"] == ""
    assert "Unsupported chart_type" in result["error"]
    assert result["trace_event"]["status"] == "error"
    assert result["trace_event"]["error_type"] == "chart_generation_error"
