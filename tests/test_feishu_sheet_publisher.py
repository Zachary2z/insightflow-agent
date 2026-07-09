import json

from workspaces.export_package import ExportPackage


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
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


def _command_result(stdout, *, exit_code=0, stderr="", elapsed_ms=4):
    from workspaces.feishu_publisher import CommandExecutionResult

    return CommandExecutionResult(
        exit_code=exit_code,
        stdout=json.dumps(stdout) if isinstance(stdout, dict) else stdout,
        stderr=stderr,
        elapsed_ms=elapsed_ms,
        command_name="lark-cli",
    )


def _package(**overrides):
    data = {
        "package_id": "export_report_1",
        "workspace_id": "ws_1",
        "source_type": "report",
        "source_id": "report_1",
        "title": "经营复盘报告",
        "generated_at": "2026-07-09T00:00:00+00:00",
        "evidence_tables": [
            {
                "table_id": "table_channel_revenue",
                "title": "渠道收入",
                "source_chapter_id": "overview",
                "columns": ["渠道", "收入"],
                "rows": [
                    {"渠道": "私域社群", "收入": "180000"},
                    {"渠道": "直播间", "收入": "90000"},
                ],
            }
        ],
        "chart_artifacts": [
            {
                "artifact_id": "chart_channel_revenue",
                "chart_id": "chart_channel_revenue",
                "title": "渠道收入图",
                "chart_type": "bar",
                "source_chapter_id": "overview",
                "evidence_refs": ["table_channel_revenue"],
                "echarts_option": {
                    "xAxis": {"type": "category", "data": ["私域社群", "直播间"]},
                    "yAxis": {"type": "value"},
                    "series": [{"type": "bar", "name": "收入", "data": [180000, 90000]}],
                },
            }
        ],
    }
    data.update(overrides)
    return ExportPackage(**data)


def test_cli_feishu_sheet_publisher_creates_workbook_and_writes_evidence_table():
    from workspaces.feishu_sheet_publisher import CliFeishuSheetPublisher

    runner = QueueRunner(
        [
            _command_result(
                {
                    "ok": True,
                    "data": {
                        "spreadsheet": {
                            "spreadsheet_token": "shtcn123",
                            "url": "https://example.feishu.cn/sheets/shtcn123",
                        }
                    },
                }
            ),
            _command_result({"ok": True, "data": {"updated_cells": 6}}),
            _command_result({"ok": True, "data": {"chart_id": "chart_1"}}),
        ]
    )

    result = CliFeishuSheetPublisher(runner=runner, cli_binary="lark-cli").publish_sheet(_package())

    assert result.status == "published"
    assert result.url == "https://example.feishu.cn/sheets/shtcn123"
    assert result.spreadsheet_token == "shtcn123"
    assert result.written_table_count == 1
    assert result.native_chart_count == 1
    assert runner.calls[0]["command"] == [
        "lark-cli",
        "sheets",
        "+workbook-create",
        "--title",
        "经营复盘报告 - 可编辑数据",
    ]
    assert runner.calls[1]["command"][:6] == [
        "lark-cli",
        "sheets",
        "+table-put",
        "--spreadsheet-token",
        "shtcn123",
        "--sheets",
    ]
    payload = json.loads(runner.calls[1]["command"][6])
    assert payload == {
        "sheets": [
            {
                "name": "渠道收入",
                "start_cell": "A1",
                "mode": "replace",
                "allow_overwrite": True,
                "columns": ["渠道", "收入"],
                "data": [["私域社群", "180000"], ["直播间", "90000"]],
            }
        ]
    }


def test_cli_feishu_sheet_publisher_creates_native_chart_for_safe_bar_mapping():
    from workspaces.feishu_sheet_publisher import CliFeishuSheetPublisher

    runner = QueueRunner(
        [
            _command_result(
                {
                    "ok": True,
                    "data": {
                        "spreadsheet": {
                            "spreadsheet_token": "shtcn123",
                            "url": "https://example.feishu.cn/sheets/shtcn123",
                        }
                    },
                }
            ),
            _command_result({"ok": True, "data": {"updated_cells": 6}}),
            _command_result({"ok": True, "data": {"chart_id": "native_chart_1"}}),
        ]
    )

    result = CliFeishuSheetPublisher(runner=runner, cli_binary="lark-cli").publish_sheet(_package())

    chart_command = runner.calls[2]["command"]
    assert result.native_chart_count == 1
    assert chart_command[:6] == [
        "lark-cli",
        "sheets",
        "+chart-create",
        "--spreadsheet-token",
        "shtcn123",
        "--sheet-name",
    ]
    assert chart_command[6] == "渠道收入"
    assert chart_command[7] == "--properties"
    properties = json.loads(chart_command[8])
    assert properties["snapshot"]["data"]["refs"] == [{"value": "渠道收入!A1:B3"}]
    assert properties["snapshot"]["data"]["dim1"]["serie"]["index"] == 1
    assert properties["snapshot"]["data"]["dim2"]["series"] == [{"index": 2, "aggregateType": "sum"}]
    assert properties["snapshot"]["plotArea"]["plot"]["type"] == "column"
    assert properties["position"]["row"] == 5


def test_cli_feishu_sheet_publisher_skips_unclear_chart_with_safe_warning():
    from workspaces.feishu_sheet_publisher import CliFeishuSheetPublisher

    runner = QueueRunner(
        [
            _command_result(
                {
                    "ok": True,
                    "data": {
                        "spreadsheet": {
                            "spreadsheet_token": "shtcn123",
                            "url": "https://example.feishu.cn/sheets/shtcn123",
                        }
                    },
                }
            ),
            _command_result({"ok": True, "data": {"updated_cells": 6}}),
        ]
    )
    package = _package(
        chart_artifacts=[
            {
                "artifact_id": "chart_unclear",
                "title": "不清晰图表",
                "chart_type": "pie",
                "echarts_option": {"series": [{"type": "pie", "data": [{"name": "A", "value": 1}]}]},
            }
        ]
    )

    result = CliFeishuSheetPublisher(runner=runner, cli_binary="lark-cli").publish_sheet(package)

    assert result.status == "warning"
    assert result.native_chart_count == 0
    assert len(runner.calls) == 2
    assert result.warnings == ["图表「不清晰图表」无法安全映射为飞书原生图表，已跳过。"]
    assert "SELECT" not in json.dumps(result.to_safe_dict(), ensure_ascii=False)


def test_cli_feishu_sheet_publisher_failure_warning_is_sanitized():
    from workspaces.feishu_sheet_publisher import CliFeishuSheetPublisher

    runner = QueueRunner(
        [
            _command_result(
                {
                    "ok": True,
                    "data": {
                        "spreadsheet": {
                            "spreadsheet_token": "shtcn123",
                            "url": "https://example.feishu.cn/sheets/shtcn123?token=secret",
                        }
                    },
                }
            ),
            _command_result(
                "",
                exit_code=2,
                stderr="stdout token=secret SELECT * FROM orders trace_path=/Users/me/trace.json provider_metadata prompt",
            ),
        ]
    )

    result = CliFeishuSheetPublisher(runner=runner, cli_binary="lark-cli").publish_sheet(_package())
    payload = result.to_safe_dict()
    payload_text = json.dumps(payload, ensure_ascii=False)

    assert result.status == "warning"
    assert payload["url"] is None
    assert payload["warnings"] == ["飞书表格「渠道收入」写入失败，已跳过。"]
    for forbidden in [
        "stdout",
        "stderr",
        "token=secret",
        "secret",
        "SELECT",
        "/Users/",
        "trace",
        "provider_metadata",
        "prompt",
    ]:
        assert forbidden not in payload_text


def test_sheet_publish_result_safe_serialization_strips_sensitive_fields():
    from workspaces.feishu_sheet_publisher import SheetPublishResult

    result = SheetPublishResult(
        status="warning",
        title="经营复盘报告",
        url="https://example.feishu.cn/sheets/shtcn123?token=secret",
        spreadsheet_token="shtcn123",
        written_table_count=3,
        native_chart_count=1,
        warnings=[
            "可展示提醒：部分图表未创建。",
            "stdout token=secret SELECT * FROM orders trace_path=/Users/me/trace.json provider_metadata prompt",
        ],
        tool_calls=[
            {
                "operation": "write_table",
                "command_name": "/Users/me/bin/lark-cli",
                "success": False,
                "elapsed_ms": 2,
                "exit_code": 2,
                "stderr": "secret",
            }
        ],
    )

    payload = result.to_safe_dict()
    payload_text = json.dumps(payload, ensure_ascii=False)

    assert payload["url"] is None
    assert payload["warnings"] == ["可展示提醒：部分图表未创建。"]
    assert payload["tool_calls"] == [
        {
            "operation": "write_table",
            "command_name": "lark-cli",
            "success": False,
            "elapsed_ms": 2,
            "exit_code": 2,
        }
    ]
    for forbidden in [
        "/Users/",
        "token=secret",
        "secret",
        "stdout",
        "stderr",
        "SELECT",
        "trace",
        "provider_metadata",
        "prompt",
    ]:
        assert forbidden not in payload_text
