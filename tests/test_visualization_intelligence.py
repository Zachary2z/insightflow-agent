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


def test_chart_validator_preserves_product_metadata_fields():
    from visualization.chart_validator import validate_chart_spec

    execution_result = _execution_result(["渠道", "收入"], [["付费搜索", 1200.0]])
    result = validate_chart_spec(
        {
            "chart_type": "ranked_bar",
            "title": "渠道收入",
            "x": "渠道",
            "y": "收入",
            "y_secondary": "",
            "series": "",
            "required_columns": ["渠道", "收入"],
            "explanation_basis": ["supported_findings"],
            "unit": "元",
            "value_label": True,
            "business_annotation": "付费搜索贡献最高。",
        },
        execution_result,
    )

    assert result["success"] is True
    assert result["unit"] == "元"
    assert result["value_label"] is True
    assert result["business_annotation"] == "付费搜索贡献最高。"


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


def test_visualization_fallback_chooses_chart_type_from_task_intent():
    from agents.visualization_agent import decide_visualization

    ranking = decide_visualization(
        "最近90天哪个门店销售额最高？",
        analysis_steps=[],
        execution_result=_execution_result(
            ["门店", "销售额"],
            [["上海旗舰店", 26255.44], ["北京国贸店", 18400.0]],
        ),
        provider=None,
        run_id="run_rank_chart",
    )
    trend = decide_visualization(
        "最近90天销售额趋势如何？",
        analysis_steps=[],
        execution_result=_execution_result(
            ["月份", "销售额"],
            [["2026-04", 12000.0], ["2026-05", 15000.0], ["2026-06", 18000.0]],
        ),
        provider=None,
        run_id="run_trend_chart",
    )
    comparison = decide_visualization(
        "比较各门店销售额和满意度，看看哪个最值得关注。",
        analysis_steps=[],
        execution_result=_execution_result(
            ["门店", "销售额", "满意度"],
            [["上海旗舰店", 26255.44, 4.8], ["北京国贸店", 18400.0, 4.4]],
        ),
        provider=None,
        run_id="run_compare_chart",
    )

    assert ranking["chart_spec"]["chart_type"] == "ranked_bar"
    assert trend["chart_spec"]["chart_type"] == "line"
    assert comparison["chart_spec"]["chart_type"] == "scatter"
    assert comparison["chart_spec"]["x"] == "销售额"
    assert comparison["chart_spec"]["y"] == "满意度"
    assert "门店" not in (comparison["chart_spec"]["x"], comparison["chart_spec"]["y"])
    assert set(comparison["chart_spec"]["required_columns"]) >= {"销售额", "满意度"}
    for decision in (ranking, trend, comparison):
        spec = decision["chart_spec"]
        assert spec["title"]
        assert any("\u4e00" <= char <= "\u9fff" for char in spec["title"])
        assert spec["business_annotation"]


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
