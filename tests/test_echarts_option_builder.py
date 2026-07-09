from __future__ import annotations

from typing import Any


def _execution_result(columns: list[str], rows: list[Any]) -> dict[str, Any]:
    return {"success": True, "columns": columns, "rows": rows, "row_count": len(rows)}


def _assert_no_function_string(value: Any) -> None:
    if isinstance(value, dict):
        for child in value.values():
            _assert_no_function_string(child)
        return
    if isinstance(value, list):
        for child in value:
            _assert_no_function_string(child)
        return
    if isinstance(value, str):
        assert "function" not in value.lower()
        assert "=>" not in value


def test_ranked_bar_option_uses_execution_rows_for_axis_and_series():
    from visualization.echarts_option_builder import build_echarts_option

    result = build_echarts_option(
        {
            "chart_type": "ranked_bar",
            "title": "渠道收入对比",
            "x": "channel",
            "y": "revenue",
            "unit": "元",
        },
        _execution_result(
            ["channel", "revenue"],
            [["私域社群", 180000], ["搜索广告", 120000]],
        ),
    )

    option = result["echarts_option"]
    assert result["success"] is True
    assert option["xAxis"]["data"] == ["私域社群", "搜索广告"]
    assert option["series"][0]["data"] == [180000.0, 120000.0]
    assert option["series"][0]["type"] == "bar"
    assert result["data_row_count"] == 2
    assert result["rendered_row_count"] == 2


def test_line_option_uses_category_axis_and_numeric_series():
    from visualization.echarts_option_builder import build_echarts_option

    result = build_echarts_option(
        {
            "chart_type": "line",
            "title": "销售额趋势",
            "x": "date",
            "y": "sales_amount",
        },
        _execution_result(
            ["date", "sales_amount"],
            [["2026-06-01", 1000], ["2026-06-02", 1300]],
        ),
    )

    option = result["echarts_option"]
    assert result["success"] is True
    assert option["xAxis"]["type"] == "category"
    assert option["xAxis"]["data"] == ["2026-06-01", "2026-06-02"]
    assert option["series"] == [{"name": "sales_amount", "type": "line", "data": [1000.0, 1300.0]}]


def test_grouped_bar_aligns_multiple_series_by_category():
    from visualization.echarts_option_builder import build_echarts_option

    result = build_echarts_option(
        {
            "chart_type": "grouped_bar",
            "title": "渠道指标对比",
            "x": "channel",
            "series": "metric_name",
            "y": "metric_value",
        },
        _execution_result(
            ["channel", "metric_name", "metric_value"],
            [
                ["私域社群", "收入", 180000],
                ["私域社群", "花费", 30000],
                ["搜索广告", "收入", 120000],
            ],
        ),
    )

    option = result["echarts_option"]
    series_by_name = {series["name"]: series for series in option["series"]}
    assert result["success"] is True
    assert option["xAxis"]["data"] == ["私域社群", "搜索广告"]
    assert set(series_by_name) == {"收入", "花费"}
    assert series_by_name["收入"]["data"] == [180000.0, 120000.0]
    assert series_by_name["花费"]["data"] == [30000.0, None]


def test_grouped_bar_uses_business_title_legend_axis_and_unit():
    from visualization.echarts_option_builder import build_echarts_option

    result = build_echarts_option(
        {
            "chart_type": "grouped_bar",
            "title": "最近90天渠道收入与投放花费对比",
            "x": "渠道",
            "series": "指标",
            "y": "金额",
            "unit": "元",
        },
        _execution_result(
            ["渠道", "指标", "金额"],
            [
                ["私域社群", "收入", 180000],
                ["私域社群", "投放花费", 30000],
                ["搜索广告", "收入", 120000],
                ["搜索广告", "投放花费", 80000],
            ],
        ),
    )

    option = result["echarts_option"]
    assert result["success"] is True
    assert option["title"]["text"] == "最近90天渠道收入与投放花费对比"
    assert option["legend"]["data"] == ["收入", "投放花费"]
    assert option["xAxis"]["name"] == "渠道"
    assert option["yAxis"]["name"] == "金额 (元)"
    assert "数值" not in str(option)


def test_grouped_bar_rejects_incompatible_metric_units_from_metadata():
    from visualization.echarts_option_builder import build_echarts_option

    result = build_echarts_option(
        {
            "chart_type": "grouped_bar",
            "title": "渠道收入与 ROI 对比",
            "x": "渠道",
            "series": "指标",
            "y": "指标值",
            "metric_units": {"收入": "元", "ROI": "%"},
        },
        _execution_result(
            ["渠道", "指标", "指标值"],
            [["私域社群", "收入", 180000], ["私域社群", "ROI", 6.0]],
        ),
    )

    assert result["success"] is False
    assert "incompatible metric units" in result["validation_error"]
    assert "echarts_option" not in result


def test_scatter_option_uses_numeric_x_y_and_optional_label_dimension():
    from visualization.echarts_option_builder import build_echarts_option

    result = build_echarts_option(
        {
            "chart_type": "scatter",
            "title": "门店销售与满意度",
            "x": "sales_amount",
            "y": "satisfaction_score",
            "label": "store",
        },
        _execution_result(
            ["store", "sales_amount", "satisfaction_score"],
            [["上海旗舰店", 260000, 4.8], ["深圳湾店", 120000, 4.2]],
        ),
    )

    option = result["echarts_option"]
    assert result["success"] is True
    assert option["series"][0]["type"] == "scatter"
    assert option["series"][0]["data"] == [
        {"value": [260000.0, 4.8], "name": "上海旗舰店"},
        {"value": [120000.0, 4.2], "name": "深圳湾店"},
    ]


def test_dual_axis_line_binds_two_numeric_series_to_two_y_axes():
    from visualization.echarts_option_builder import build_echarts_option

    result = build_echarts_option(
        {
            "chart_type": "dual_axis_line",
            "title": "收入与 ROAS 趋势",
            "x": "date",
            "y": "revenue",
            "y_secondary": "roas",
        },
        _execution_result(
            ["date", "revenue", "roas"],
            [["2026-06-01", 1000, 3.2], ["2026-06-02", 1300, 3.8]],
        ),
    )

    option = result["echarts_option"]
    assert result["success"] is True
    assert option["xAxis"]["data"] == ["2026-06-01", "2026-06-02"]
    assert option["yAxis"] == [
        {"type": "value", "name": "revenue"},
        {"type": "value", "name": "roas"},
    ]
    assert option["series"] == [
        {"name": "revenue", "type": "line", "yAxisIndex": 0, "data": [1000.0, 1300.0]},
        {"name": "roas", "type": "line", "yAxisIndex": 1, "data": [3.2, 3.8]},
    ]


def test_missing_required_column_fails_without_option():
    from visualization.echarts_option_builder import build_echarts_option

    result = build_echarts_option(
        {"chart_type": "ranked_bar", "x": "channel", "y": "revenue"},
        _execution_result(["channel", "gmv"], [["私域社群", 180000]]),
    )

    assert result["success"] is False
    assert "revenue" in result["validation_error"]
    assert "echarts_option" not in result


def test_non_numeric_y_fails_without_silent_bad_data():
    from visualization.echarts_option_builder import build_echarts_option

    result = build_echarts_option(
        {"chart_type": "ranked_bar", "x": "channel", "y": "revenue"},
        _execution_result(["channel", "revenue"], [["私域社群", "not-a-number"]]),
    )

    assert result["success"] is False
    assert "numeric" in result["validation_error"].lower()
    assert "echarts_option" not in result


def test_large_row_count_is_truncated_and_records_data_limit():
    from visualization.echarts_option_builder import build_echarts_option

    rows = [[f"渠道{i}", i] for i in range(120)]
    result = build_echarts_option(
        {"chart_type": "ranked_bar", "x": "channel", "y": "revenue"},
        _execution_result(["channel", "revenue"], rows),
        max_rows=50,
    )

    assert result["success"] is True
    assert result["data_row_count"] == 120
    assert result["rendered_row_count"] == 50
    assert result["data_limit"]["truncated"] is True
    assert result["data_limit"]["sampled_row_count"] == 50
    assert len(result["echarts_option"]["xAxis"]["data"]) == 50
    assert result["echarts_option"]["series"][0]["data"][-1] == 49.0


def test_option_does_not_include_javascript_function_strings():
    from visualization.echarts_option_builder import build_echarts_option

    result = build_echarts_option(
        {
            "chart_type": "ranked_bar",
            "title": "function () { return hacked; }",
            "x": "channel",
            "y": "revenue",
            "business_annotation": "() => hacked",
        },
        _execution_result(["channel", "revenue"], [["私域社群", 180000]]),
    )

    assert result["success"] is True
    _assert_no_function_string(result["echarts_option"])


def test_table_chart_type_returns_static_fallback_reason_without_option():
    from visualization.echarts_option_builder import build_echarts_option

    result = build_echarts_option(
        {"chart_type": "table", "title": "明细表", "x": "channel", "y": "revenue"},
        _execution_result(["channel", "revenue"], [["私域社群", 180000]]),
    )

    assert result["success"] is False
    assert result["fallback_reason"] == "table chart uses table/static fallback"
    assert "echarts_option" not in result


def test_sql_or_local_absolute_path_strings_are_not_embedded_in_option():
    from visualization.echarts_option_builder import build_echarts_option

    result = build_echarts_option(
        {
            "chart_type": "ranked_bar",
            "title": "SELECT * FROM orders",
            "x": "channel",
            "y": "revenue",
        },
        _execution_result(["channel", "revenue"], [["/Users/example/workspace/export.csv", 180000]]),
    )

    assert result["success"] is False
    assert "unsafe" in result["validation_error"].lower()
    assert "echarts_option" not in result
