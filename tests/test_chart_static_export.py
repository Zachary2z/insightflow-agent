from pathlib import Path


def test_static_export_reuses_legacy_png_svg_asset_paths(tmp_path):
    from workspaces.chart_static_export import export_chart_static_asset

    asset = export_chart_static_asset(
        {
            "artifact_id": "legacy_chart",
            "title": "旧 PNG 图表",
            "path": "runs/run_1/charts/legacy.png",
            "url": "/api/workspaces/ws_1/artifacts/runs/run_1/charts/legacy.png",
            "rendering_status": "rendered",
            "source": "analysis_workbench",
        },
        workspace_root=tmp_path,
    )

    assert asset["success"] is True
    assert asset["asset"]["path"] == "runs/run_1/charts/legacy.png"
    assert asset["asset"]["url"].endswith("/runs/run_1/charts/legacy.png")
    assert asset["asset"]["format"] == "png"
    assert asset["warnings"] == []


def test_static_export_reuses_echarts_image_fallback(tmp_path):
    from workspaces.chart_static_export import export_chart_static_asset

    asset = export_chart_static_asset(
        {
            "artifact_id": "echarts_with_image",
            "title": "渠道收入",
            "renderer": "echarts",
            "echarts_option": {"xAxis": {"data": ["私域"]}, "series": [{"type": "bar", "data": [180000]}]},
            "image_path": "reports/report_1/artifacts/channel.svg",
            "image_url": "/api/workspaces/ws_1/artifacts/reports/report_1/artifacts/channel.svg",
            "source": "report_center",
        },
        workspace_root=tmp_path,
    )

    assert asset["success"] is True
    assert asset["asset"]["path"].endswith("channel.svg")
    assert asset["asset"]["format"] == "svg"
    assert asset["asset"]["generated"] is False


def test_static_export_generates_svg_from_echarts_option(tmp_path):
    from workspaces.chart_static_export import export_chart_static_asset

    asset = export_chart_static_asset(
        {
            "artifact_id": "chart_option_only",
            "title": "渠道收入对比",
            "renderer": "echarts",
            "chart_type": "ranked_bar",
            "echarts_option": {
                "xAxis": {"type": "category", "data": ["私域社群", "直播间"]},
                "yAxis": {"type": "value"},
                "series": [{"name": "收入", "type": "bar", "data": [180000.0, 90000.0]}],
            },
            "evidence_refs": ["question_evidence_pack"],
            "source": "analysis_workbench",
        },
        workspace_root=tmp_path,
        output_dir="exports/charts",
    )

    assert asset["success"] is True
    assert asset["asset"]["path"] == "exports/charts/chart_option_only.svg"
    assert asset["asset"]["format"] == "svg"
    assert asset["asset"]["generated"] is True
    svg = (tmp_path / asset["asset"]["path"]).read_text(encoding="utf-8")
    assert "<svg" in svg
    assert "渠道收入对比" in svg
    assert "180,000" in svg
    assert "/tmp/" not in str(asset)


def test_static_export_reuses_existing_png_for_feishu_target(tmp_path):
    from workspaces.chart_static_export import export_chart_static_asset

    chart_file = tmp_path / "reports/report_1/artifacts/channel.png"
    chart_file.parent.mkdir(parents=True)
    chart_file.write_bytes(b"png")

    asset = export_chart_static_asset(
        {
            "artifact_id": "png_ready",
            "title": "渠道收入",
            "image_path": "reports/report_1/artifacts/channel.png",
            "image_url": "/api/workspaces/ws_1/artifacts/reports/report_1/artifacts/channel.png",
            "source": "report_center",
        },
        workspace_root=tmp_path,
        target_format="png",
    )

    assert asset["success"] is True
    assert asset["asset"]["path"] == "reports/report_1/artifacts/channel.png"
    assert asset["asset"]["format"] == "png"
    assert asset["asset"]["generated"] is False


def test_static_export_generates_png_from_echarts_option_for_feishu_target(tmp_path):
    from workspaces.chart_static_export import export_chart_static_asset

    asset = export_chart_static_asset(
        {
            "artifact_id": "chart_option_png",
            "title": "渠道收入对比",
            "renderer": "echarts",
            "chart_type": "ranked_bar",
            "echarts_option": {
                "xAxis": {"type": "category", "data": ["私域社群", "直播间"]},
                "yAxis": {"type": "value"},
                "series": [{"name": "收入", "type": "bar", "data": [180000.0, 90000.0]}],
            },
            "source": "report_center",
        },
        workspace_root=tmp_path,
        output_dir="exports/charts",
        target_format="png",
    )

    assert asset["success"] is True
    assert asset["asset"]["path"] == "exports/charts/chart_option_png.png"
    assert asset["asset"]["format"] == "png"
    assert asset["asset"]["generated"] is True
    assert (tmp_path / asset["asset"]["path"]).read_bytes().startswith(b"\x89PNG")


def test_static_export_leaves_svg_non_primary_for_feishu_insertion(tmp_path):
    from workspaces.chart_static_export import export_chart_static_asset

    svg = tmp_path / "reports/report_1/artifacts/channel.svg"
    svg.parent.mkdir(parents=True)
    svg.write_text("<svg></svg>", encoding="utf-8")

    asset = export_chart_static_asset(
        {
            "artifact_id": "svg_with_option",
            "title": "渠道收入",
            "image_path": "reports/report_1/artifacts/channel.svg",
            "echarts_option": {
                "xAxis": {"data": ["私域"]},
                "series": [{"type": "bar", "name": "收入", "data": [180000]}],
            },
        },
        workspace_root=tmp_path,
        target_format="png",
    )

    assert asset["success"] is True
    assert asset["asset"]["format"] == "png"
    assert asset["asset"]["path"].endswith("svg_with_option.png")


def test_static_export_generated_svg_url_points_to_generated_asset_not_old_payload_url(tmp_path):
    from workspaces.chart_static_export import export_chart_static_asset

    asset = export_chart_static_asset(
        {
            "artifact_id": "chart_option_only",
            "workspace_id": "ws_1",
            "url": "/api/workspaces/ws_1/artifacts/non_image_payload",
            "echarts_option": {
                "xAxis": {"data": ["A"]},
                "series": [{"type": "bar", "data": [1]}],
            },
        },
        workspace_root=tmp_path,
    )

    assert asset["success"] is True
    assert asset["asset"]["path"] == "exports/charts/chart_option_only.svg"
    assert asset["asset"]["url"] == "/api/workspaces/ws_1/artifacts/exports/charts/chart_option_only.svg"
    assert asset["chart_artifact"]["image_url"] == "/api/workspaces/ws_1/artifacts/exports/charts/chart_option_only.svg"


def test_static_export_warns_when_echarts_option_is_insufficient(tmp_path):
    from workspaces.chart_static_export import export_chart_static_asset

    asset = export_chart_static_asset(
        {
            "artifact_id": "chart_missing_data",
            "title": "缺少数据图表",
            "renderer": "echarts",
            "echarts_option": {"series": [{"type": "bar"}]},
        },
        workspace_root=tmp_path,
    )

    assert asset["success"] is False
    assert asset["asset"] == {}
    assert any("缺少" in warning or "无法" in warning for warning in asset["warnings"])


def test_static_export_rejects_absolute_paths_traversal_and_secret_urls(tmp_path):
    from workspaces.chart_static_export import export_chart_static_asset

    asset = export_chart_static_asset(
        {
            "artifact_id": "unsafe_chart",
            "title": "不安全图表",
            "image_path": "/Users/someone/secret/chart.png",
            "path": "../secret/chart.png",
            "image_url": "https://example.com/chart.png?api_key=secret",
            "url": "/api/workspaces/ws_1/artifacts/chart.png?token=secret",
        },
        workspace_root=tmp_path,
    )

    assert asset["success"] is False
    assert asset["asset"] == {}
    assert asset["warnings"]
    assert "/Users/" not in str(asset)
    assert "api_key" not in str(asset)


def test_static_export_refuses_to_generate_without_workspace_or_output_root():
    from workspaces.chart_static_export import export_chart_static_asset

    asset = export_chart_static_asset(
        {
            "artifact_id": "option_only_no_root",
            "title": "无输出根目录",
            "renderer": "echarts",
            "echarts_option": {
                "xAxis": {"data": ["A"]},
                "series": [{"type": "bar", "data": [1]}],
            },
        }
    )

    assert asset["success"] is False
    assert asset["asset"] == {}
    assert any("workspace_root" in warning or "output_dir" in warning for warning in asset["warnings"])
