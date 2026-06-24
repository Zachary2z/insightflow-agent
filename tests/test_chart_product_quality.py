from __future__ import annotations

import warnings
from pathlib import Path


def test_render_chart_supports_chinese_labels_units_value_labels_and_business_annotation(tmp_path):
    from visualization.chart_renderer import render_chart

    execution_result = {
        "success": True,
        "columns": ["渠道", "收入"],
        "rows": [["付费搜索", 128000.0], ["自然流量", 86000.0], ["邮件", 43000.0]],
        "row_count": 3,
    }
    chart_spec = {
        "chart_type": "ranked_bar",
        "title": "各渠道收入表现",
        "x": "渠道",
        "y": "收入",
        "y_secondary": "",
        "series": "",
        "required_columns": ["渠道", "收入"],
        "explanation_basis": ["supported_findings"],
        "unit": "元",
        "value_label": True,
        "business_annotation": "付费搜索贡献最高，建议优先复核预算效率。",
        "run_id": "run_chinese_chart",
    }

    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        result = render_chart(execution_result, chart_spec, output_dir=tmp_path)

    assert result["success"] is True
    assert Path(result["chart_path"]).is_file()
    assert result["chart_spec"]["unit"] == "元"
    assert result["chart_spec"]["value_label"] is True
    assert result["chart_spec"]["business_annotation"] == "付费搜索贡献最高，建议优先复核预算效率。"
    glyph_warnings = [warning for warning in captured if "Glyph" in str(warning.message)]
    assert glyph_warnings == []
