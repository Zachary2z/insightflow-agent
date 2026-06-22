from __future__ import annotations

from pathlib import Path


def _execution_result(columns: list[str], rows: list[list[object]]) -> dict:
    return {
        "success": True,
        "columns": columns,
        "rows": rows,
        "row_count": len(rows),
    }


def test_chart_validator_rejects_columns_missing_from_execution_result():
    from visualization.chart_validator import validate_chart_spec

    execution_result = _execution_result(["category_name", "gmv"], [["Cameras", 1200.0]])
    result = validate_chart_spec(
        {
            "chart_type": "ranked_bar",
            "title": "Bad chart",
            "x": "category_name",
            "y": "net_gmv",
            "y_secondary": "",
            "series": "",
            "required_columns": ["category_name", "net_gmv"],
            "explanation_basis": ["supported_findings"],
        },
        execution_result,
    )

    assert result["success"] is False
    assert "net_gmv" in result["validation_error"]


def test_chart_renderer_uses_only_real_execution_rows(tmp_path):
    from visualization.chart_renderer import render_chart

    execution_result = _execution_result(
        ["category_name", "gmv"],
        [["Cameras", 1200.0], ["Audio", 900.0]],
    )
    spec = {
        "chart_type": "ranked_bar",
        "title": "Top Categories",
        "x": "category_name",
        "y": "gmv",
        "y_secondary": "",
        "series": "",
        "required_columns": ["category_name", "gmv"],
        "explanation_basis": ["supported_findings"],
        "run_id": "run_visualization_renderer_test",
    }

    result = render_chart(execution_result, spec, output_dir=tmp_path)

    assert result["success"] is True
    assert result["chart_type"] == "ranked_bar"
    assert Path(result["chart_path"]).exists()
    assert result["data_row_count"] == 2
    assert result["rendered_rows"] == execution_result["rows"]
    assert result["fabricated_data"] is False


def test_unsupported_chart_type_falls_back_to_safe_table_or_basic_bar(tmp_path):
    from visualization.chart_renderer import render_chart

    execution_result = _execution_result(["category_name", "gmv"], [["Cameras", 1200.0]])
    result = render_chart(
        execution_result,
        {
            "chart_type": "radar",
            "title": "Unsupported",
            "x": "category_name",
            "y": "gmv",
            "required_columns": ["category_name", "gmv"],
        },
        output_dir=tmp_path,
    )

    assert result["success"] is True
    assert result["fallback_used"] is True
    assert result["fallback_reason"].startswith("Unsupported chart_type")
    assert result["chart_type"] in {"ranked_bar", "table"}
    if result["chart_type"] == "ranked_bar":
        assert Path(result["chart_path"]).exists()
    else:
        assert result["table"]["columns"] == ["category_name", "gmv"]
        assert result["table"]["rows"] == [["Cameras", 1200.0]]
