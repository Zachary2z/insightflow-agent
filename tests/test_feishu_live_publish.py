import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest

from workspaces.export_package import ExportPackage
from workspaces.feishu_publisher import CliFeishuPublisher


_PNG_1X1 = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc```\x00\x00"
    b"\x00\x04\x00\x01\xf6\x178U\x00\x00\x00\x00IEND\xaeB`\x82"
)


pytestmark = pytest.mark.skipif(
    os.getenv("INSIGHTFLOW_FEISHU_LIVE") != "1" or not os.getenv("LARK_CLI_BIN"),
    reason="Set INSIGHTFLOW_FEISHU_LIVE=1 and LARK_CLI_BIN=lark-cli to run the real Feishu publish test.",
)


def test_live_feishu_publish_minimal_report_with_png_chart(tmp_path):
    cli_binary = os.environ["LARK_CLI_BIN"]
    if shutil.which(cli_binary) is None:
        pytest.skip(f"LARK_CLI_BIN is not available on PATH: {cli_binary}")

    chart_path = tmp_path / "exports" / "charts" / "p36_live_chart.png"
    chart_path.parent.mkdir(parents=True, exist_ok=True)
    chart_path.write_bytes(_PNG_1X1)
    package = ExportPackage(
        package_id="export_report_p36_live",
        workspace_id="p36_live_workspace",
        source_type="report",
        source_id="p36_live_report",
        title="InsightFlow P36 飞书发布验证报告",
        generated_at="2026-07-08T00:00:00+00:00",
        document={
            "title": "InsightFlow P36 飞书发布验证报告",
            "time_range": "验证数据",
            "data_sources": ["live_test"],
            "opening_summary": "这是一份用于验证报告中心真实发布到飞书文档的中文摘要。",
            "sections": [
                {
                    "section_id": "summary",
                    "title": "中文正文验证",
                    "body": "飞书发布链路应保留报告中心正文，并尝试插入本地 PNG 图表。",
                    "chart_refs": ["p36_live_chart"],
                    "evidence_refs": ["p36_live_evidence"],
                }
            ],
            "action_recommendations": ["验证完成后不要把真实链接或文档 ID 写入仓库。"],
            "data_boundaries": ["这是最小 live verification 包，不包含真实业务数据。"],
        },
        business_content_summary="这是一份用于验证报告中心真实发布到飞书文档的中文摘要。",
        sections=[
            {
                "section_id": "summary",
                "title": "中文正文验证",
                "body": "飞书发布链路应保留报告中心正文，并尝试插入本地 PNG 图表。",
                "chart_refs": ["p36_live_chart"],
                "evidence_refs": ["p36_live_evidence"],
            }
        ],
        action_recommendations=["验证完成后不要把真实链接或文档 ID 写入仓库。"],
        data_boundaries=["这是最小 live verification 包，不包含真实业务数据。"],
        chart_artifacts=[
            {
                "artifact_id": "p36_live_chart",
                "title": "P36 Live PNG 图表",
                "renderer": "image",
                "chart_type": "png",
                "image_path": "exports/charts/p36_live_chart.png",
                "path": "exports/charts/p36_live_chart.png",
                "rendering_status": "rendered",
                "source": "report_center",
                "evidence_refs": ["p36_live_evidence"],
            }
        ],
        static_assets=[
            {
                "asset_id": "p36_live_chart",
                "asset_type": "chart_image",
                "title": "P36 Live PNG 图表",
                "path": "exports/charts/p36_live_chart.png",
                "format": "png",
                "source": "report_center",
                "rendering_status": "rendered",
            }
        ],
        evidence_refs=["p36_live_evidence"],
        evidence_summary={"fact_count": 1, "refs": ["p36_live_evidence"]},
    )

    result = CliFeishuPublisher(
        cli_binary=cli_binary,
        workspace_root=tmp_path,
        timeout_seconds=90,
    ).publish_report(package)
    safe = result.to_safe_dict()
    insert_attempted = any(call.get("operation") == "insert_chart_image" for call in safe.get("tool_calls", []))
    fetch_checked = False

    if safe.get("document_id"):
        fetch = subprocess.run(
            [cli_binary, "docs", "+fetch", "--doc", str(safe["document_id"]), "--doc-format", "markdown"],
            text=True,
            capture_output=True,
            timeout=60,
            check=False,
        )
        if fetch.returncode == 0 and fetch.stdout:
            fetch_checked = True
            assert "InsightFlow P36 飞书发布验证报告" in fetch.stdout or "中文正文验证" in fetch.stdout

    print(
        "FEISHU_LIVE_SAFE_SUMMARY "
        + json.dumps(
            {
                "status": safe.get("status"),
                "url_present": bool(safe.get("url")),
                "document_id_present": bool(safe.get("document_id")),
                "insert_attempted": insert_attempted,
                "inserted_chart_count": safe.get("inserted_chart_count", 0),
                "failed_chart_count": safe.get("failed_chart_count", 0),
                "warning_count": len(safe.get("warnings", [])),
                "fetch_checked": fetch_checked,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )

    assert safe["status"] in {"published", "warning"}
    assert safe.get("url")
    assert safe.get("document_id")
    assert insert_attempted
    if safe.get("failed_chart_count", 0) == 0:
        assert safe.get("inserted_chart_count", 0) >= 1
