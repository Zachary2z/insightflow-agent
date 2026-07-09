import json
from pathlib import Path

from workspaces.export_package import ExportPackage


class FakeRunner:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.calls = []

    def run(self, command, *, input_text=None, timeout_seconds=60):
        self.calls.append(
            {
                "command": list(command),
                "input_text": input_text,
                "timeout_seconds": timeout_seconds,
            }
        )
        if self.error:
            raise self.error
        return self.result


class QueueRunner:
    def __init__(self, results):
        self.results = list(results)
        self.calls = []

    def run(self, command, *, input_text=None, timeout_seconds=60):
        self.calls.append(
            {
                "command": list(command),
                "input_text": input_text,
                "timeout_seconds": timeout_seconds,
            }
        )
        if not self.results:
            raise AssertionError("unexpected command call")
        return self.results.pop(0)


def _report_package(**overrides):
    data = {
        "package_id": "export_report_1",
        "workspace_id": "ws_1",
        "source_type": "report",
        "source_id": "report_1",
        "title": "经营复盘报告",
        "generated_at": "2026-07-08T00:00:00+00:00",
        "business_content_summary": "私域社群收入领先。",
        "sections": [
            {
                "section_id": "overview",
                "title": "经营概览",
                "body": "私域社群收入为 18.0 万。",
                "evidence_refs": ["fact_revenue"],
            }
        ],
        "action_recommendations": ["继续复盘投放效率。"],
        "data_boundaries": ["当前缺少利润字段。"],
    }
    data.update(overrides)
    return ExportPackage(**data)


def _success_create_result(document_id="doccn123", url="https://example.feishu.cn/docx/doccn123", elapsed_ms=12):
    from workspaces.feishu_publisher import CommandExecutionResult

    return CommandExecutionResult(
        exit_code=0,
        stdout=json.dumps(
            {
                "ok": True,
                "data": {
                    "document": {
                        "document_id": document_id,
                        "url": url,
                    }
                },
            }
        ),
        stderr="",
        elapsed_ms=elapsed_ms,
        command_name="lark-cli",
    )


def _success_media_result(elapsed_ms=5):
    from workspaces.feishu_publisher import CommandExecutionResult

    return CommandExecutionResult(
        exit_code=0,
        stdout=json.dumps({"ok": True, "data": {"document_id": "doccn123", "block_id": "blk_1", "file_token": "file_1"}}),
        stderr="",
        elapsed_ms=elapsed_ms,
        command_name="lark-cli",
    )


class FakeSheetPublisher:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def publish_sheet(self, package):
        self.calls.append(package)
        return self.result


def test_cli_feishu_publisher_builds_official_document_create_command_with_content(monkeypatch):
    from workspaces.feishu_publisher import CliFeishuPublisher, CommandExecutionResult

    monkeypatch.setenv("LARK_CLI_BIN", "lark-test")
    success_json = {
        "ok": True,
        "data": {
            "document": {
                "document_id": "doccn123",
                "url": "https://example.feishu.cn/docx/doccn123",
            }
        },
    }
    runner = FakeRunner(
        CommandExecutionResult(
            exit_code=0,
            stdout=json.dumps(success_json),
            stderr="",
            elapsed_ms=12,
            command_name="lark-test",
        )
    )

    result = CliFeishuPublisher(runner=runner).publish_report(_report_package())

    assert result.status == "published"
    assert runner.calls[0]["command"][:-1] == [
        "lark-test",
        "docs",
        "+create",
        "--doc-format",
        "markdown",
        "--title",
        "经营复盘报告",
        "--content",
    ]
    content = runner.calls[0]["command"][-1]
    assert runner.calls[0]["input_text"] is None
    assert "# 经营复盘报告" not in content
    assert "时间范围：" not in content
    assert "## 经营概览" in content
    assert "继续复盘投放效率" in content


def test_cli_feishu_publisher_markdown_uses_feishu_title_and_business_metadata():
    from workspaces.feishu_publisher import CliFeishuPublisher

    runner = FakeRunner(_success_create_result())
    package = _report_package(
        title="最近90天经营复盘报告",
        document={
            "title": "最近90天经营复盘报告",
            "time_range": "最近90天",
            "data_sources": ["orders", "customers_客户资料", "marketing_spend"],
            "opening_summary": "收入结构继续由私域社群拉动。",
            "sections": [
                {
                    "section_id": "overview",
                    "title": "经营概览",
                    "body": "核心收入来源保持稳定。",
                    "evidence_refs": ["fact_revenue"],
                }
            ],
        },
    )

    CliFeishuPublisher(runner=runner, cli_binary="lark-cli").publish_report(package)

    command = runner.calls[0]["command"]
    content = command[-1]
    assert command[command.index("--title") + 1] == "最近90天经营复盘报告"
    assert not content.startswith("# 最近90天经营复盘报告")
    assert "# 最近90天经营复盘报告" not in content
    assert "时间范围：最近90天" in content
    assert "数据来源：订单、客户、营销投放" in content
    assert "customers_客户资料" not in content


def test_cli_feishu_publisher_markdown_includes_evidence_tables():
    from workspaces.feishu_publisher import CliFeishuPublisher

    runner = FakeRunner(_success_create_result())
    package = _report_package(
        evidence_tables=[
            {
                "table_id": "table_channel_revenue",
                "title": "渠道收入证据表",
                "description": "来自已生成报告证据。",
                "source_chapter_id": "overview",
                "columns": ["渠道", "收入"],
                "rows": [{"渠道": "私域社群", "收入": "180000"}, {"渠道": "直播间", "收入": "90000"}],
            }
        ]
    )

    result = CliFeishuPublisher(runner=runner, cli_binary="lark-cli").publish_report(package)

    assert result.status == "published"
    content = runner.calls[0]["command"][-1]
    assert "**证据表：渠道收入证据表**" in content
    assert "### 证据表" not in content
    assert "来自已生成报告证据。" in content
    assert "| 渠道 | 收入 |" in content
    assert "| --- | --- |" in content
    assert "| 私域社群 | 180000 |" in content
    assert "SELECT" not in content
    assert "raw_rows" not in content


def test_cli_feishu_publisher_includes_companion_sheet_link_section_when_available():
    from workspaces.feishu_publisher import CliFeishuPublisher
    from workspaces.feishu_sheet_publisher import SheetPublishResult

    runner = FakeRunner(_success_create_result())
    sheet_publisher = FakeSheetPublisher(
        SheetPublishResult(
            status="published",
            title="经营复盘报告 - 可编辑数据",
            url="https://example.feishu.cn/sheets/shtcn123",
            spreadsheet_token="shtcn123",
            written_table_count=1,
            native_chart_count=1,
        )
    )
    package = _report_package(
        evidence_tables=[
            {
                "table_id": "table_channel_revenue",
                "title": "渠道收入证据表",
                "columns": ["渠道", "收入"],
                "rows": [{"渠道": "私域社群", "收入": "180000"}],
            }
        ]
    )

    result = CliFeishuPublisher(
        runner=runner,
        cli_binary="lark-cli",
        sheet_publisher=sheet_publisher,
    ).publish_report(package)

    content = runner.calls[0]["command"][-1]
    append_command = runner.calls[1]["command"]
    assert result.status == "published"
    assert result.sheet_url == "https://example.feishu.cn/sheets/shtcn123"
    assert result.written_table_count == 1
    assert result.native_chart_count == 1
    assert result.sheet_warnings == []
    assert "## 可编辑数据和图表" not in content
    assert append_command[:8] == [
        "lark-cli",
        "docs",
        "+update",
        "--doc",
        "doccn123",
        "--command",
        "append",
        "--doc-format",
    ]
    assert append_command[8:10] == ["markdown", "--content"]
    assert "## 可编辑数据和图表" in append_command[10]
    assert "可编辑数据表和图表：https://example.feishu.cn/sheets/shtcn123" in append_command[10]
    assert content.count("| 渠道 | 收入 |") == 1
    assert sheet_publisher.calls


def test_cli_feishu_publisher_keeps_doc_success_when_companion_sheet_fails():
    from workspaces.feishu_publisher import CliFeishuPublisher
    from workspaces.feishu_sheet_publisher import SheetPublishResult

    runner = FakeRunner(_success_create_result())
    sheet_publisher = FakeSheetPublisher(
        SheetPublishResult(
            status="failed",
            title="经营复盘报告 - 可编辑数据",
            warnings=["飞书表格创建失败，已保留飞书文档发布。"],
        )
    )

    result = CliFeishuPublisher(
        runner=runner,
        cli_binary="lark-cli",
        sheet_publisher=sheet_publisher,
    ).publish_report(_report_package())

    content = runner.calls[0]["command"][-1]
    assert result.status == "warning"
    assert result.url == "https://example.feishu.cn/docx/doccn123"
    assert result.sheet_url is None
    assert result.sheet_warnings == ["飞书表格创建失败，已保留飞书文档发布。"]
    assert result.warnings == []
    assert len(runner.calls) == 1
    assert "## 可编辑数据和图表" not in content


def test_cli_feishu_publisher_places_evidence_tables_and_chart_anchors_near_sections():
    from workspaces.feishu_publisher import CliFeishuPublisher

    runner = FakeRunner(_success_create_result())
    package = _report_package(
        sections=[
            {
                "section_id": "revenue",
                "title": "收入结构",
                "body": "私域社群收入领先。",
                "chart_refs": ["chart_revenue"],
            },
            {
                "section_id": "trend",
                "title": "趋势变化",
                "body": "收入趋势保持稳定。",
                "chart_refs": ["chart_trend"],
            },
        ],
        evidence_tables=[
            {
                "table_id": "table_revenue",
                "title": "收入结构",
                "source_chapter_id": "revenue",
                "columns": ["渠道", "收入"],
                "rows": [{"渠道": "私域社群", "收入": "180000"}],
            }
        ],
        chart_artifacts=[
            {"artifact_id": "chart_revenue", "title": "收入结构图表", "source_chapter_id": "revenue"},
            {"artifact_id": "chart_trend", "title": "趋势变化图表", "source_chapter_id": "trend"},
        ],
    )

    CliFeishuPublisher(runner=runner, cli_binary="lark-cli").publish_report(package)

    content = runner.calls[0]["command"][-1]
    revenue_section = content.index("## 收入结构")
    evidence_label = content.index("**证据表：收入结构**")
    revenue_anchor = content.index("**图表：收入结构图表**")
    trend_section = content.index("## 趋势变化")
    trend_anchor = content.index("**图表：趋势变化图表**")
    assert revenue_section < evidence_label < revenue_anchor < trend_section < trend_anchor
    assert "下图展示收入结构图表，请结合正文和证据表解读。" in content
    assert "图表将在此处插入。" not in content
    assert "## 图表" not in content


def test_cli_feishu_publisher_matches_section_chart_refs_against_artifact_chart_ids():
    from workspaces.feishu_publisher import CliFeishuPublisher

    runner = FakeRunner(_success_create_result())
    package = _report_package(
        sections=[
            {
                "section_id": "revenue_structure",
                "title": "收入结构",
                "body": "微信私域收入领先。",
                "chart_refs": ["revenue_structure_chart"],
            },
            {
                "section_id": "trend_changes",
                "title": "趋势变化",
                "body": "5 月收入最高。",
                "chart_refs": ["trend_changes_chart"],
            },
        ],
        chart_artifacts=[
            {
                "artifact_id": "artifact_chart_revenue_structure_chart",
                "chart_ids": ["revenue_structure_chart"],
                "title": "收入结构图表",
            },
            {
                "artifact_id": "artifact_chart_trend_changes_chart",
                "chart_ids": ["trend_changes_chart"],
                "title": "趋势变化图表",
            },
        ],
    )

    CliFeishuPublisher(runner=runner, cli_binary="lark-cli").publish_report(package)

    content = runner.calls[0]["command"][-1]
    revenue_section = content.index("## 收入结构")
    revenue_anchor = content.index("**图表：收入结构图表**")
    trend_section = content.index("## 趋势变化")
    trend_anchor = content.index("**图表：趋势变化图表**")
    assert revenue_section < revenue_anchor < trend_section < trend_anchor
    assert "下图展示趋势变化图表，请结合正文和证据表解读。" in content
    assert "图表将在此处插入。" not in content
    assert "## 图表说明" not in content


def test_cli_feishu_publisher_markdown_escapes_table_pipes_and_newlines():
    from workspaces.feishu_publisher import CliFeishuPublisher

    runner = FakeRunner(_success_create_result())
    package = _report_package(
        evidence_tables=[
            {
                "table_id": "table_escape",
                "title": "字段转义表",
                "source_chapter_id": "overview",
                "columns": ["渠道|类型", "说明"],
                "rows": [{"渠道|类型": "私域|会员", "说明": "第一行\n第二行"}],
            }
        ]
    )

    CliFeishuPublisher(runner=runner, cli_binary="lark-cli").publish_report(package)

    content = runner.calls[0]["command"][-1]
    assert "| 渠道\\|类型 | 说明 |" in content
    assert "| 私域\\|会员 | 第一行 第二行 |" in content


def test_cli_feishu_publisher_markdown_truncates_large_evidence_tables():
    from workspaces.feishu_publisher import CliFeishuPublisher

    runner = FakeRunner(_success_create_result())
    package = _report_package(
        evidence_tables=[
            {
                "table_id": "table_large",
                "title": "大表",
                "source_chapter_id": "overview",
                "columns": ["序号", "收入"],
                "rows": [{"序号": index, "收入": index * 10} for index in range(1, 13)],
            }
        ]
    )

    CliFeishuPublisher(runner=runner, cli_binary="lark-cli").publish_report(package)

    content = runner.calls[0]["command"][-1]
    assert "| 10 | 100 |" in content
    assert "| 11 | 110 |" not in content
    assert "仅展示前 10 行，共 12 行" in content


def test_cli_feishu_publisher_defaults_to_lark_cli_binary(monkeypatch):
    from workspaces.feishu_publisher import CliFeishuPublisher, CommandExecutionResult

    monkeypatch.delenv("LARK_CLI_BIN", raising=False)
    runner = FakeRunner(
        CommandExecutionResult(
            exit_code=0,
            stdout=json.dumps(
                {
                    "ok": True,
                    "data": {
                        "document": {
                            "document_id": "doccn_default",
                            "url": "https://example.feishu.cn/docx/doccn_default",
                        }
                    },
                }
            ),
            stderr="",
            elapsed_ms=3,
            command_name="lark-cli",
        )
    )

    result = CliFeishuPublisher(runner=runner).publish_report(_report_package())

    assert result.status == "published"
    assert runner.calls[0]["command"][0] == "lark-cli"


def test_cli_feishu_publisher_parses_success_json_into_publish_result():
    from workspaces.feishu_publisher import CliFeishuPublisher, CommandExecutionResult

    runner = FakeRunner(
        CommandExecutionResult(
            exit_code=0,
            stdout=json.dumps(
                {
                    "doc_id": "doccn456",
                    "document_url": "https://example.feishu.cn/docx/doccn456",
                    "title": "飞书内标题",
                    "created_at": "2026-07-08T01:02:03+00:00",
                }
            ),
            stderr="",
            elapsed_ms=7,
            command_name="lark",
        )
    )

    result = CliFeishuPublisher(runner=runner, cli_binary="lark").publish_report(_report_package())
    payload = result.to_safe_dict()

    assert payload["platform"] == "feishu"
    assert payload["status"] == "published"
    assert payload["document_id"] == "doccn456"
    assert payload["external_id"] == "doccn456"
    assert payload["url"] == "https://example.feishu.cn/docx/doccn456"
    assert payload["title"] == "飞书内标题"
    assert payload["created_at"] == "2026-07-08T01:02:03+00:00"
    assert payload["tool_calls"] == [
        {
            "operation": "create_document",
            "command_name": "lark",
            "success": True,
            "elapsed_ms": 7,
            "exit_code": 0,
        }
    ]


def test_cli_feishu_publisher_parses_official_nested_success_json():
    from workspaces.feishu_publisher import CliFeishuPublisher, CommandExecutionResult

    runner = FakeRunner(
        CommandExecutionResult(
            exit_code=0,
            stdout=json.dumps(
                {
                    "ok": True,
                    "identity": "user",
                    "data": {
                        "document": {
                            "document_id": "docx_token",
                            "revision_id": 1,
                            "url": "https://example.feishu.cn/docx/docx_token",
                            "new_blocks": [{"block_id": "blkcnXXXX", "block_token": "boardXXXX"}],
                        }
                    },
                }
            ),
            stderr="",
            elapsed_ms=11,
            command_name="lark-cli",
        )
    )

    result = CliFeishuPublisher(runner=runner, cli_binary="lark-cli").publish_report(_report_package())
    payload = result.to_safe_dict()

    assert payload["status"] == "published"
    assert payload["document_id"] == "docx_token"
    assert payload["external_id"] == "docx_token"
    assert payload["url"] == "https://example.feishu.cn/docx/docx_token"
    assert payload["title"] == "经营复盘报告"
    assert payload["tool_calls"] == [
        {
            "operation": "create_document",
            "command_name": "lark-cli",
            "success": True,
            "elapsed_ms": 11,
            "exit_code": 0,
        }
    ]


def test_cli_feishu_publisher_inserts_png_chart_after_document_create(tmp_path):
    from workspaces.feishu_publisher import CliFeishuPublisher

    chart_file = tmp_path / "exports/charts/channel.png"
    chart_file.parent.mkdir(parents=True)
    chart_file.write_bytes(b"png")
    runner = QueueRunner([_success_create_result(document_id="doccn_wiki", url="https://example.feishu.cn/wiki/wiki_token"), _success_media_result()])
    package = _report_package(
        static_assets=[
            {
                "asset_id": "chart_channel",
                "asset_type": "chart_image",
                "title": "渠道收入对比",
                "path": "exports/charts/channel.png",
                "format": "png",
                "source": "report_center",
                "rendering_status": "rendered",
            }
        ]
    )

    result = CliFeishuPublisher(
        runner=runner,
        cli_binary="lark-cli",
        workspace_root=tmp_path,
        cli_working_dir=tmp_path,
    ).publish_report(package)

    assert result.status == "published"
    assert result.url == "https://example.feishu.cn/wiki/wiki_token"
    assert result.document_id == "doccn_wiki"
    assert result.inserted_chart_count == 1
    assert result.failed_chart_count == 0
    assert runner.calls[1]["command"] == [
        "lark-cli",
        "docs",
        "+media-insert",
        "--doc",
        "doccn_wiki",
        "--file",
        "exports/charts/channel.png",
        "--type",
        "image",
        "--selection-with-ellipsis",
        "图表：渠道收入对比",
        "--align",
        "center",
        "--caption",
        "渠道收入对比",
        "--width",
        "800",
    ]
    assert runner.calls[1]["input_text"] is None
    assert result.to_safe_dict()["tool_calls"] == [
        {"operation": "create_document", "command_name": "lark-cli", "success": True, "elapsed_ms": 12, "exit_code": 0},
        {"operation": "insert_chart_image", "command_name": "lark-cli", "success": True, "elapsed_ms": 5, "exit_code": 0},
    ]


def test_cli_feishu_publisher_inserts_multiple_png_charts_and_counts(tmp_path):
    from workspaces.feishu_publisher import CliFeishuPublisher

    first = tmp_path / "exports/charts/channel.png"
    second = tmp_path / "exports/charts/revenue.jpg"
    first.parent.mkdir(parents=True)
    first.write_bytes(b"png")
    second.write_bytes(b"jpg")
    runner = QueueRunner([_success_create_result(), _success_media_result(elapsed_ms=3), _success_media_result(elapsed_ms=4)])
    package = _report_package(
        static_assets=[
            {"asset_id": "chart_1", "asset_type": "chart_image", "title": "渠道收入", "path": "exports/charts/channel.png", "format": "png"},
            {"asset_id": "chart_2", "asset_type": "chart_image", "title": "收入趋势", "path": "exports/charts/revenue.jpg", "format": "jpg"},
        ]
    )

    result = CliFeishuPublisher(
        runner=runner,
        cli_binary="lark-cli",
        workspace_root=tmp_path,
        cli_working_dir=tmp_path,
    ).publish_report(package)

    assert result.status == "published"
    assert result.inserted_chart_count == 2
    assert result.failed_chart_count == 0
    assert [call["command"][2] for call in runner.calls] == ["+create", "+media-insert", "+media-insert"]
    for call, anchor in zip(runner.calls[1:], ["图表：渠道收入", "图表：收入趋势"], strict=True):
        assert "--selection-with-ellipsis" in call["command"]
        assert call["command"][call["command"].index("--selection-with-ellipsis") + 1] == anchor


def test_cli_feishu_publisher_keeps_document_url_and_warns_when_chart_insert_fails(tmp_path):
    from workspaces.feishu_publisher import CliFeishuPublisher, CommandExecutionResult

    chart_file = tmp_path / "exports/charts/channel.png"
    chart_file.parent.mkdir(parents=True)
    chart_file.write_bytes(b"png")
    runner = QueueRunner(
        [
            _success_create_result(),
            CommandExecutionResult(
                exit_code=3,
                stdout="raw stdout token=secret",
                stderr="media failed /Users/me/chart.png token=secret",
                elapsed_ms=10,
                command_name="lark-cli",
            ),
        ]
    )
    package = _report_package(
        static_assets=[
            {"asset_id": "chart_1", "asset_type": "chart_image", "title": "渠道收入", "path": "exports/charts/channel.png", "format": "png"},
        ]
    )

    result = CliFeishuPublisher(
        runner=runner,
        cli_binary="lark-cli",
        workspace_root=tmp_path,
        cli_working_dir=tmp_path,
    ).publish_report(package)
    payload_text = json.dumps(result.to_safe_dict(), ensure_ascii=False)

    assert result.status == "warning"
    assert result.url == "https://example.feishu.cn/docx/doccn123"
    assert result.document_id == "doccn123"
    assert result.inserted_chart_count == 0
    assert result.failed_chart_count == 1
    assert result.warnings == ["图表「渠道收入」未能插入到对应章节，请在飞书文档中手动调整。"]
    assert "stdout" not in payload_text
    assert "stderr" not in payload_text
    assert "/Users/" not in payload_text
    assert "token" not in payload_text.lower()


def test_cli_feishu_publisher_skips_svg_and_missing_files_with_safe_warnings(tmp_path):
    from workspaces.feishu_publisher import CliFeishuPublisher

    svg = tmp_path / "exports/charts/generated.svg"
    svg.parent.mkdir(parents=True)
    svg.write_text("<svg></svg>", encoding="utf-8")
    runner = QueueRunner([_success_create_result()])
    package = _report_package(
        static_assets=[
            {"asset_id": "chart_svg", "asset_type": "chart_image", "title": "ECharts 静态图", "path": "exports/charts/generated.svg", "format": "svg"},
            {"asset_id": "chart_missing", "asset_type": "chart_image", "title": "缺失图表", "path": "exports/charts/missing.png", "format": "png"},
        ]
    )

    result = CliFeishuPublisher(runner=runner, cli_binary="lark-cli", workspace_root=tmp_path).publish_report(package)
    payload_text = json.dumps(result.to_safe_dict(), ensure_ascii=False)

    assert result.status == "warning"
    assert result.inserted_chart_count == 0
    assert result.failed_chart_count == 2
    assert len(runner.calls) == 1
    assert any("ECharts 静态图" in warning and "PNG/JPEG/GIF" in warning for warning in result.warnings)
    assert any("缺失图表" in warning and "文件不存在" in warning for warning in result.warnings)
    assert str(tmp_path) not in payload_text


def test_cli_feishu_publisher_svg_only_chart_returns_visible_safe_warning(tmp_path):
    from workspaces.feishu_publisher import CliFeishuPublisher

    svg = tmp_path / "exports/charts/revenue.svg"
    svg.parent.mkdir(parents=True)
    svg.write_text("<svg></svg>", encoding="utf-8")
    runner = QueueRunner([_success_create_result()])
    package = _report_package(
        static_assets=[
            {
                "asset_id": "chart_svg",
                "asset_type": "chart_image",
                "title": "收入结构图表",
                "path": "exports/charts/revenue.svg",
                "format": "svg",
            }
        ]
    )

    result = CliFeishuPublisher(runner=runner, cli_binary="lark-cli", workspace_root=tmp_path).publish_report(package)

    assert result.status == "warning"
    assert result.failed_chart_count == 1
    assert result.warnings == ["图表「收入结构图表」当前没有可插入的 PNG/JPEG/GIF 文件，已跳过。"]


def test_cli_feishu_publisher_chart_tool_calls_do_not_leak_sensitive_fields(tmp_path):
    from workspaces.feishu_publisher import CliFeishuPublisher, CommandExecutionResult

    chart_file = tmp_path / "exports/charts/channel.png"
    chart_file.parent.mkdir(parents=True)
    chart_file.write_bytes(b"png")
    runner = QueueRunner(
        [
            _success_create_result(),
            CommandExecutionResult(
                exit_code=2,
                stdout='{"raw_sql":"SELECT * FROM orders","token":"secret"}',
                stderr=f"trace=/Users/me/trace.json path={chart_file} access_token=secret",
                elapsed_ms=8,
                command_name="/Users/me/bin/lark-cli",
            ),
        ]
    )
    package = _report_package(
        static_assets=[
            {"asset_id": "chart_1", "asset_type": "chart_image", "title": "渠道收入", "path": "exports/charts/channel.png", "format": "png"},
        ]
    )

    result = CliFeishuPublisher(
        runner=runner,
        cli_binary="/Users/me/bin/lark-cli",
        workspace_root=tmp_path,
        cli_working_dir=tmp_path,
    ).publish_report(package)
    payload_text = json.dumps(result.to_safe_dict(), ensure_ascii=False)

    assert result.status == "warning"
    assert result.failed_chart_count == 1
    assert "insert_chart_image" in payload_text
    for forbidden in [
        "stdout",
        "stderr",
        "/Users/",
        str(tmp_path),
        "SELECT",
        "raw_sql",
        "trace",
        "token",
        "secret",
        "access_token",
    ]:
        assert forbidden not in payload_text


def test_cli_feishu_publisher_returns_failed_when_official_json_ok_false():
    from workspaces.feishu_publisher import CliFeishuPublisher, CommandExecutionResult

    runner = FakeRunner(
        CommandExecutionResult(
            exit_code=0,
            stdout=json.dumps(
                {
                    "ok": False,
                    "identity": "user",
                    "error": {
                        "type": "auth",
                        "message": "not logged in token=secret",
                        "hint": "run lark-cli auth login",
                    },
                }
            ),
            stderr="",
            elapsed_ms=6,
            command_name="lark-cli",
        )
    )

    result = CliFeishuPublisher(runner=runner, cli_binary="lark-cli").publish_report(_report_package())
    payload_text = json.dumps(result.to_safe_dict(), ensure_ascii=False)

    assert result.status == "failed"
    assert any("ok=false" in warning for warning in result.warnings)
    assert "token" not in payload_text.lower()
    assert "secret" not in payload_text.lower()


def test_cli_feishu_publisher_warns_when_official_json_has_no_document():
    from workspaces.feishu_publisher import CliFeishuPublisher, CommandExecutionResult

    runner = FakeRunner(
        CommandExecutionResult(
            exit_code=0,
            stdout=json.dumps({"ok": True, "data": {}}),
            stderr="",
            elapsed_ms=8,
            command_name="lark-cli",
        )
    )

    result = CliFeishuPublisher(runner=runner, cli_binary="lark-cli").publish_report(_report_package())

    assert result.status == "warning"
    assert result.document_id is None
    assert result.url is None
    assert any("data.document" in warning for warning in result.warnings)


def test_cli_feishu_publisher_returns_failed_when_cli_runner_raises():
    from workspaces.feishu_publisher import CliFeishuPublisher

    runner = FakeRunner(error=FileNotFoundError("No such file or directory: /Users/me/bin/lark token=secret"))

    result = CliFeishuPublisher(runner=runner, cli_binary="lark").publish_report(_report_package())
    payload = result.to_safe_dict()

    assert payload["status"] == "failed"
    assert payload["url"] is None
    assert any("无法执行飞书 CLI" in warning for warning in payload["warnings"])
    assert "/Users/" not in json.dumps(payload, ensure_ascii=False)
    assert "token" not in json.dumps(payload, ensure_ascii=False).lower()


def test_cli_feishu_publisher_returns_failed_for_non_zero_exit_without_raw_output_leak():
    from workspaces.feishu_publisher import CliFeishuPublisher, CommandExecutionResult

    runner = FakeRunner(
        CommandExecutionResult(
            exit_code=2,
            stdout='{"token":"secret"}',
            stderr="not logged in api_key=secret /Users/me/.lark/config",
            elapsed_ms=9,
            command_name="lark",
        )
    )

    result = CliFeishuPublisher(runner=runner, cli_binary="lark").publish_report(_report_package())
    payload_text = json.dumps(result.to_safe_dict(), ensure_ascii=False)

    assert result.status == "failed"
    assert "飞书 CLI 创建文档失败" in result.warnings[0]
    assert "exit code 2" in result.warnings[0]
    assert "not logged in" in result.warnings[0]
    assert '{"token":"secret"}' not in payload_text
    assert "api_key" not in payload_text
    assert "/Users/" not in payload_text


def test_cli_feishu_publisher_returns_failed_for_non_json_stdout_without_leaking_stdout():
    from workspaces.feishu_publisher import CliFeishuPublisher, CommandExecutionResult

    runner = FakeRunner(
        CommandExecutionResult(
            exit_code=0,
            stdout="created doc at /Users/me/report.md secret=abc",
            stderr="",
            elapsed_ms=5,
            command_name="lark",
        )
    )

    result = CliFeishuPublisher(runner=runner, cli_binary="lark").publish_report(_report_package())
    payload_text = json.dumps(result.to_safe_dict(), ensure_ascii=False)

    assert result.status == "failed"
    assert any("没有返回可解析的 JSON" in warning for warning in result.warnings)
    assert "created doc" not in payload_text
    assert "/Users/" not in payload_text
    assert "secret" not in payload_text.lower()


def test_cli_feishu_publisher_warns_when_success_json_lacks_url_or_document_id():
    from workspaces.feishu_publisher import CliFeishuPublisher, CommandExecutionResult

    runner = FakeRunner(
        CommandExecutionResult(
            exit_code=0,
            stdout=json.dumps({"title": "经营复盘报告"}),
            stderr="",
            elapsed_ms=4,
            command_name="lark",
        )
    )

    result = CliFeishuPublisher(runner=runner, cli_binary="lark").publish_report(_report_package())

    assert result.status == "warning"
    assert result.document_id is None
    assert result.url is None
    assert any("缺少 document_id" in warning for warning in result.warnings)


def test_external_publish_result_safe_serialization_strips_sensitive_fields():
    from workspaces.external_publishing import ExternalPublishResult

    result = ExternalPublishResult(
        platform="feishu",
        status="published",
        title="/Users/me/report.md",
        url="https://example.feishu.cn/docx/doc?token=secret",
        document_id="doccn123",
        external_id="doccn123",
        created_at="2026-07-08T00:00:00+00:00",
        warnings=[
            "raw stdout: SELECT * FROM orders",
            "可展示警告：部分图表未插入。",
        ],
        tool_calls=[
            {
                "operation": "create_document",
                "command_name": "lark",
                "success": True,
                "elapsed_ms": 3,
                "exit_code": 0,
                "stdout": "secret",
                "stderr": "api_key=secret",
                "absolute_path": "/Users/me/report.md",
                "raw_sql": "SELECT * FROM orders",
                "rows": [{"a": 1}],
                "trace_path": "trace.json",
                "prompt": "write report",
            }
        ],
    )

    payload = result.to_safe_dict()
    payload_text = json.dumps(payload, ensure_ascii=False)

    assert payload["title"] == ""
    assert payload["url"] is None
    assert payload["warnings"] == ["可展示警告：部分图表未插入。"]
    assert payload["tool_calls"] == [
        {
            "operation": "create_document",
            "command_name": "lark",
            "success": True,
            "elapsed_ms": 3,
            "exit_code": 0,
        }
    ]
    for forbidden in [
        "/Users/",
        "token",
        "secret",
        "api_key",
        "stdout",
        "stderr",
        "raw_sql",
        "rows",
        "trace",
        "prompt",
        "SELECT",
    ]:
        assert forbidden not in payload_text


def test_cli_feishu_publisher_rejects_analysis_export_package():
    from workspaces.feishu_publisher import CliFeishuPublisher, CommandExecutionResult

    analysis_package = ExportPackage(
        package_id="export_run_1",
        workspace_id="ws_1",
        source_type="analysis",
        source_id="run_1",
        title="分析回答",
        generated_at="2026-07-08T00:00:00+00:00",
        business_content_summary="最近30天私域收入最高。",
        business_answer={"direct_answer": "最近30天私域收入最高。"},
        sections=[],
    )
    runner = FakeRunner(
        CommandExecutionResult(
            exit_code=0,
            stdout=json.dumps({"document_id": "doccn999", "url": "https://example.feishu.cn/docx/doccn999"}),
            stderr="",
            elapsed_ms=1,
            command_name="lark",
        )
    )

    result = CliFeishuPublisher(runner=runner, cli_binary="lark").publish_report(analysis_package)

    assert result.status == "failed"
    assert runner.calls == []
    assert any("只支持 Report Center" in warning for warning in result.warnings)


def test_cli_feishu_publisher_rejects_dict_without_explicit_package_version():
    from workspaces.feishu_publisher import CliFeishuPublisher, CommandExecutionResult

    package = _report_package().to_dict()
    package.pop("package_version")
    runner = FakeRunner(
        CommandExecutionResult(
            exit_code=0,
            stdout=json.dumps(
                {
                    "ok": True,
                    "data": {
                        "document": {
                            "document_id": "doccn999",
                            "url": "https://example.feishu.cn/docx/doccn999",
                        }
                    },
                }
            ),
            stderr="",
            elapsed_ms=1,
            command_name="lark-cli",
        )
    )

    result = CliFeishuPublisher(runner=runner, cli_binary="lark-cli").publish_report(package)

    assert result.status == "failed"
    assert runner.calls == []
    assert any("只支持 Report Center" in warning for warning in result.warnings)
