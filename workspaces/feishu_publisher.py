from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
from typing import Any, Protocol

from workspaces.external_publishing import (
    ExternalPublishResult,
    export_package_to_dict,
    failed_publish_result,
    is_report_export_package,
    safe_command_name,
    safe_warning,
)
from workspaces.models import utc_now_iso


DEFAULT_LARK_CLI_BIN = "lark-cli"
DEFAULT_TIMEOUT_SECONDS = 60
INSERTABLE_IMAGE_FORMATS = {"png", "jpg", "jpeg", "gif"}
MAX_EVIDENCE_TABLE_ROWS = 10


@dataclass
class CommandExecutionResult:
    exit_code: int
    stdout: str = ""
    stderr: str = ""
    elapsed_ms: int = 0
    command_name: str = ""


class CommandRunner(Protocol):
    def run(
        self,
        command: list[str],
        *,
        input_text: str | None = None,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    ) -> CommandExecutionResult:
        ...


class SubprocessCommandRunner:
    def __init__(self, *, working_dir: str | Path | None = None) -> None:
        self.working_dir = Path(working_dir).resolve() if working_dir else None

    def run(
        self,
        command: list[str],
        *,
        input_text: str | None = None,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    ) -> CommandExecutionResult:
        if not command:
            raise ValueError("command is required")
        command_name = safe_command_name(command[0])
        if shutil.which(command[0]) is None:
            raise FileNotFoundError(f"CLI binary is not available: {command_name or 'lark'}")

        started = time.monotonic()
        completed = subprocess.run(
            command,
            input=input_text,
            text=True,
            capture_output=True,
            cwd=str(self.working_dir) if self.working_dir else None,
            timeout=timeout_seconds,
            check=False,
        )
        elapsed_ms = int((time.monotonic() - started) * 1000)
        return CommandExecutionResult(
            exit_code=completed.returncode,
            stdout=completed.stdout or "",
            stderr=completed.stderr or "",
            elapsed_ms=elapsed_ms,
            command_name=command_name,
        )


class CliFeishuPublisher:
    def __init__(
        self,
        *,
        runner: CommandRunner | None = None,
        cli_binary: str | None = None,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        workspace_root: str | Path | None = None,
        cli_working_dir: str | Path | None = None,
    ) -> None:
        self.cli_binary = cli_binary or os.getenv("LARK_CLI_BIN") or DEFAULT_LARK_CLI_BIN
        self.timeout_seconds = timeout_seconds
        self.workspace_root = Path(workspace_root).resolve() if workspace_root else None
        self.cli_working_dir = Path(cli_working_dir).resolve() if cli_working_dir else Path.cwd().resolve()
        self.runner = runner or SubprocessCommandRunner(working_dir=self.cli_working_dir)

    def publish_report(self, package: Any) -> ExternalPublishResult:
        package_data = export_package_to_dict(package)
        title = _safe_package_title(package_data)
        if not is_report_export_package(package_data):
            return failed_publish_result(
                platform="feishu",
                title=title,
                warning="飞书发布当前只支持 Report Center 的 report export package；Analysis Workbench 分析回答不能作为完整报告发布。",
            )

        command = self._build_create_document_command(title, _package_to_markdown(package_data))
        try:
            command_result = self.runner.run(
                command,
                input_text=None,
                timeout_seconds=self.timeout_seconds,
            )
        except Exception as exc:  # noqa: BLE001 - external command failures become publish results.
            return failed_publish_result(
                platform="feishu",
                title=title,
                warning=f"无法执行飞书 CLI：{_runner_error_summary(exc)}",
                tool_calls=[
                    _tool_call(
                        command_name=safe_command_name(self.cli_binary),
                        success=False,
                        exit_code=127,
                        elapsed_ms=0,
                    )
                ],
            )

        tool_calls = [
            _tool_call(
                command_name=command_result.command_name or self.cli_binary,
                success=command_result.exit_code == 0,
                exit_code=command_result.exit_code,
                elapsed_ms=command_result.elapsed_ms,
            )
        ]
        if command_result.exit_code != 0:
            return failed_publish_result(
                platform="feishu",
                title=title,
                warning=f"飞书 CLI 创建文档失败（exit code {command_result.exit_code}）：{_cli_output_summary(command_result.stderr)}",
                tool_calls=tool_calls,
            )

        parsed = _parse_json_object(command_result.stdout)
        if parsed is None:
            return failed_publish_result(
                platform="feishu",
                title=title,
                warning="飞书 CLI 创建文档成功但没有返回可解析的 JSON，无法确认文档链接或 ID。",
                tool_calls=tool_calls,
            )

        if parsed.get("ok") is False:
            return failed_publish_result(
                platform="feishu",
                title=title,
                warning=f"飞书 CLI 返回 ok=false：{_official_error_summary(parsed)}",
                tool_calls=tool_calls,
            )

        document = _official_document(parsed)
        if parsed.get("ok") is True and not document:
            return ExternalPublishResult(
                platform="feishu",
                status="warning",
                title=title,
                created_at=utc_now_iso(),
                warnings=["飞书 CLI 返回 ok=true，但缺少 data.document，无法确认文档链接或 ID。"],
                tool_calls=tool_calls,
            )

        result_source = document or parsed
        document_id = _first_text(result_source, "document_id", "doc_id", "document_token", "token")
        url = _first_text(result_source, "url", "document_url", "doc_url", "share_url")
        result_title = _first_text(result_source, "title", "document_title") or _first_text(parsed, "title", "document_title") or title
        created_at = _first_text(parsed, "created_at", "create_time") or utc_now_iso()
        warnings: list[str] = []
        if not document_id:
            warnings.append("飞书 CLI 返回成功，但缺少 document_id。")
        if not url:
            warnings.append("飞书 CLI 返回成功，但缺少文档 URL。")

        result = ExternalPublishResult(
            platform="feishu",
            status="warning" if warnings else "published",
            title=result_title,
            url=url or None,
            document_id=document_id or None,
            external_id=_first_text(parsed, "external_id", "id") or document_id or None,
            created_at=created_at,
            inserted_chart_count=0,
            failed_chart_count=0,
            warnings=warnings,
            tool_calls=tool_calls,
        )
        self._insert_chart_images(package_data, result)
        return result

    def _build_create_document_command(self, title: str, content: str) -> list[str]:
        return [
            self.cli_binary,
            "docs",
            "+create",
            "--doc-format",
            "markdown",
            "--title",
            title or "InsightFlow 报告",
            "--content",
            content,
        ]

    def _insert_chart_images(self, package: dict[str, Any], result: ExternalPublishResult) -> None:
        assets, asset_warnings = _collect_chart_image_assets(
            package,
            workspace_root=self.workspace_root,
            cli_working_dir=self.cli_working_dir,
        )
        result.warnings.extend(asset_warnings)
        result.failed_chart_count += len(asset_warnings)
        doc_ref = result.document_id or _docx_url_or_empty(result.url)
        if not doc_ref:
            if assets:
                result.failed_chart_count += len(assets)
                result.warnings.append("飞书文档已创建，但缺少可用于插入图表的 document_id，图表未插入。")
            if result.failed_chart_count:
                result.status = "warning"
            return

        for asset in assets:
            command = self._build_insert_chart_image_command(
                doc_ref=doc_ref,
                file_path=asset["file_path"],
                caption=asset["caption"],
            )
            try:
                command_result = self.runner.run(
                    command,
                    input_text=None,
                    timeout_seconds=self.timeout_seconds,
                )
            except Exception as exc:  # noqa: BLE001 - insertion failures should not erase created docs.
                result.failed_chart_count += 1
                result.warnings.append(_chart_insert_warning(asset["caption"]))
                result.tool_calls.append(
                    _tool_call(
                        operation="insert_chart_image",
                        command_name=safe_command_name(self.cli_binary),
                        success=False,
                        exit_code=127,
                        elapsed_ms=0,
                    )
                )
                continue

            result.tool_calls.append(
                _tool_call(
                    operation="insert_chart_image",
                    command_name=command_result.command_name or self.cli_binary,
                    success=command_result.exit_code == 0,
                    exit_code=command_result.exit_code,
                    elapsed_ms=command_result.elapsed_ms,
                )
            )
            if command_result.exit_code == 0:
                result.inserted_chart_count += 1
                continue
            result.failed_chart_count += 1
            result.warnings.append(_chart_insert_warning(asset["caption"]))

        if result.failed_chart_count or result.warnings:
            result.status = "warning"

    def _build_insert_chart_image_command(self, *, doc_ref: str, file_path: str, caption: str) -> list[str]:
        anchor_text = _chart_anchor_text(caption or "报告图表")
        return [
            self.cli_binary,
            "docs",
            "+media-insert",
            "--doc",
            doc_ref,
            "--file",
            file_path,
            "--type",
            "image",
            "--selection-with-ellipsis",
            anchor_text,
            "--align",
            "center",
            "--caption",
            caption or "报告图表",
            "--width",
            "800",
        ]


def _package_to_markdown(package: dict[str, Any]) -> str:
    lines: list[str] = []
    document = package.get("document") if isinstance(package.get("document"), dict) else {}
    time_range = _safe_text(document.get("time_range"))
    data_sources = _business_data_source_labels(document.get("data_sources"))
    if time_range:
        lines.extend([f"时间范围：{time_range}", ""])
    if data_sources:
        lines.extend([f"数据来源：{'、'.join(data_sources)}", ""])
    summary = _safe_text(package.get("business_content_summary")) or _safe_text(document.get("opening_summary"))
    if summary:
        lines.extend(["## 摘要", summary, ""])
    evidence_tables = _safe_evidence_tables(package.get("evidence_tables"))
    rendered_table_ids: set[str] = set()
    rendered_chart_keys: set[str] = set()
    for section in package.get("sections") or document.get("sections") or []:
        if not isinstance(section, dict):
            continue
        section_title = _safe_text(section.get("title"))
        section_body = _safe_text(section.get("body"))
        section_id = _safe_text(section.get("section_id"))
        if section_title:
            lines.extend([f"## {section_title}", ""])
        if section_body:
            lines.extend([section_body, ""])
        for table in _tables_for_section(evidence_tables, section_id):
            rendered_table_ids.add(table["table_id"])
            lines.extend(_render_evidence_table(table))
            lines.append("")
        section_charts = _chart_items_for_section(package, section)
        for chart in section_charts:
            rendered_chart_keys.add(chart["key"])
            lines.extend(_render_chart_anchor(chart["title"]))
            lines.append("")
    remaining_tables = [table for table in evidence_tables if table["table_id"] not in rendered_table_ids]
    if remaining_tables:
        lines.extend(["## 数据依据", ""])
        for table in remaining_tables:
            lines.extend(_render_evidence_table(table))
            lines.append("")
    remaining_charts = [chart for chart in _all_chart_items(package) if chart["key"] not in rendered_chart_keys]
    if remaining_charts:
        lines.extend(["## 图表说明", ""])
        for chart in remaining_charts:
            lines.extend(_render_chart_anchor(chart["title"]))
            lines.append("")
    recommendations = _safe_text_list(package.get("action_recommendations"))
    if recommendations:
        lines.extend(["## 行动建议", ""])
        lines.extend([f"- {item}" for item in recommendations])
        lines.append("")
    boundaries = _safe_text_list(package.get("data_boundaries"))
    if boundaries:
        lines.extend(["## 数据边界", ""])
        lines.extend([f"- {item}" for item in boundaries])
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def _safe_evidence_tables(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    tables: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            continue
        columns = _safe_text_list(item.get("columns"))
        rows = [row for row in item.get("rows") or [] if isinstance(row, dict)]
        if not columns or not rows:
            continue
        table_id = _safe_text(item.get("table_id")) or f"evidence_table_{index + 1}"
        tables.append(
            {
                "table_id": table_id,
                "title": _safe_text(item.get("title")) or "证据表",
                "description": _safe_text(item.get("description")),
                "source_chapter_id": _safe_text(item.get("source_chapter_id")),
                "columns": columns,
                "rows": rows,
            }
        )
    return tables


def _tables_for_section(tables: list[dict[str, Any]], section_id: str) -> list[dict[str, Any]]:
    if not section_id:
        return []
    return [table for table in tables if table.get("source_chapter_id") == section_id]


def _render_evidence_table(table: dict[str, Any]) -> list[str]:
    columns = list(table["columns"])
    rows = list(table["rows"])
    visible_rows = rows[:MAX_EVIDENCE_TABLE_ROWS]
    lines = [f"**证据表：{_markdown_cell(table['title'])}**", ""]
    description = _safe_text(table.get("description"))
    if description:
        lines.extend([description, ""])
    lines.extend(
        [
            "| " + " | ".join(_markdown_cell(column) for column in columns) + " |",
            "| " + " | ".join("---" for _ in columns) + " |",
        ]
    )
    for row in visible_rows:
        lines.append("| " + " | ".join(_markdown_cell(row.get(column)) for column in columns) + " |")
    if len(rows) > len(visible_rows):
        lines.extend(["", f"（仅展示前 {len(visible_rows)} 行，共 {len(rows)} 行。）"])
    return lines


def _render_chart_anchor(title: str) -> list[str]:
    return [f"**{_chart_anchor_text(title)}**", f"下图展示{title}，请结合正文和证据表解读。"]


def _markdown_cell(value: Any) -> str:
    text = _safe_text(value)
    if not text:
        return ""
    return text.replace("\\", "\\\\").replace("|", "\\|")


def _chart_items_for_section(package: dict[str, Any], section: dict[str, Any]) -> list[dict[str, str]]:
    refs = set(_safe_text_list(section.get("chart_refs")))
    section_id = _safe_text(section.get("section_id"))
    selected: list[dict[str, str]] = []
    for chart in package.get("chart_artifacts") or []:
        if not isinstance(chart, dict):
            continue
        aliases = _chart_aliases(chart)
        chart_key = _safe_text(chart.get("artifact_id")) or next(iter(aliases), "")
        source_chapter_id = _safe_text(chart.get("source_chapter_id"))
        if (refs and refs.intersection(aliases)) or (section_id and source_chapter_id == section_id):
            title = _safe_text(chart.get("title"))
            if title:
                selected.append({"key": chart_key or title, "title": title})
    for asset in package.get("static_assets") or []:
        if not isinstance(asset, dict):
            continue
        asset_id = _safe_text(asset.get("asset_id"))
        if refs and asset_id in refs:
            title = _safe_text(asset.get("title"))
            if title:
                selected.append({"key": asset_id or title, "title": title})
    return _unique_chart_items(selected)


def _chart_aliases(chart: dict[str, Any]) -> set[str]:
    aliases = {
        _safe_text(chart.get("artifact_id")),
        _safe_text(chart.get("chart_id")),
    }
    aliases.update(_safe_text_list(chart.get("chart_ids")))
    return {alias for alias in aliases if alias}


def _all_chart_items(package: dict[str, Any]) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for chart in package.get("chart_artifacts") or []:
        if isinstance(chart, dict):
            key = _safe_text(chart.get("artifact_id") or chart.get("chart_id"))
            title = _safe_text(chart.get("title"))
            if title:
                items.append({"key": key or title, "title": title})
    for asset in package.get("static_assets") or []:
        if isinstance(asset, dict):
            key = _safe_text(asset.get("asset_id"))
            title = _safe_text(asset.get("title"))
            if title:
                items.append({"key": key or title, "title": title})
    return _unique_chart_items(items)


def _unique_chart_items(items: list[dict[str, str]]) -> list[dict[str, str]]:
    unique: dict[str, dict[str, str]] = {}
    for item in items:
        title = _safe_text(item.get("title"))
        if not title:
            continue
        key = _safe_text(item.get("key")) or title
        unique.setdefault(key, {"key": key, "title": title})
    return list(unique.values())


def _parse_json_object(value: str) -> dict[str, Any] | None:
    try:
        parsed = json.loads(value or "")
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _first_text(data: dict[str, Any], *keys: str) -> str:
    for key in keys:
        text = _safe_text(data.get(key))
        if text:
            return text
    return ""


def _official_document(data: dict[str, Any]) -> dict[str, Any]:
    nested_data = data.get("data") if isinstance(data.get("data"), dict) else {}
    document = nested_data.get("document") if isinstance(nested_data.get("document"), dict) else {}
    return document


def _safe_package_title(package: dict[str, Any]) -> str:
    document = package.get("document") if isinstance(package.get("document"), dict) else {}
    return _safe_text(package.get("title")) or _safe_text(document.get("title")) or "InsightFlow 报告"


def _business_data_source_labels(value: Any) -> list[str]:
    labels: list[str] = []
    for item in _safe_text_list(value):
        label = _business_data_source_label(item)
        if label:
            labels.append(label)
    return list(dict.fromkeys(labels))


def _business_data_source_label(value: str) -> str:
    lowered = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", " ", value.lower())
    compact = lowered.replace(" ", "")
    if any(marker in compact for marker in ("order", "订单", "sales", "销售")):
        return "订单"
    if any(marker in compact for marker in ("customer", "客户", "member", "会员")):
        return "客户"
    if any(marker in compact for marker in ("marketing", "campaign", "ad", "spend", "投放", "广告", "渠道")):
        return "营销投放"
    if any(marker in compact for marker in ("support", "ticket", "feedback", "客服", "工单", "反馈")):
        return "客服反馈"
    if any(marker in compact for marker in ("product", "sku", "商品", "品类")):
        return "商品"
    if any(marker in compact for marker in ("store", "shop", "门店", "店铺")):
        return "门店"
    if any(marker in compact for marker in ("region", "区域", "城市")):
        return "区域"
    return ""


def _safe_text_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [text for text in (_safe_text(item) for item in value) if text]


def _safe_text(value: Any) -> str:
    text = safe_warning(value)
    if not text:
        return ""
    if "\n" in text:
        text = " ".join(part.strip() for part in text.splitlines() if part.strip())
    return text


def _chart_anchor_text(title: str) -> str:
    safe_title = _safe_text(title) or "报告图表"
    return f"图表：{safe_title}"


def _chart_insert_warning(title: str) -> str:
    safe_title = _safe_text(title) or "报告图表"
    return f"图表「{safe_title}」未能插入到对应章节，请在飞书文档中手动调整。"


def _tool_call(
    *,
    operation: str = "create_document",
    command_name: str,
    success: bool,
    exit_code: int,
    elapsed_ms: int,
) -> dict[str, Any]:
    return {
        "operation": operation,
        "command_name": safe_command_name(command_name) or DEFAULT_LARK_CLI_BIN,
        "success": success,
        "elapsed_ms": max(0, int(elapsed_ms or 0)),
        "exit_code": int(exit_code or 0),
    }


def _collect_chart_image_assets(
    package: dict[str, Any],
    *,
    workspace_root: Path | None,
    cli_working_dir: Path,
) -> tuple[list[dict[str, str]], list[str]]:
    assets: list[dict[str, str]] = []
    warnings: list[str] = []
    for index, item in enumerate(package.get("static_assets") or []):
        if not isinstance(item, dict):
            continue
        if _safe_text(item.get("asset_type")) not in {"", "chart_image"}:
            continue
        title = _safe_text(item.get("title")) or f"报告图表 {index + 1}"
        path = _safe_text(item.get("path"))
        fmt = _asset_format(item)
        if fmt == "svg":
            warnings.append(f"图表「{title}」当前没有可插入的 PNG/JPEG/GIF 文件，已跳过。")
            continue
        if fmt and fmt not in INSERTABLE_IMAGE_FORMATS:
            warnings.append(f"图表「{title}」格式 {fmt.upper()} 暂不支持插入飞书文档。")
            continue
        if not path:
            warnings.append(f"图表「{title}」缺少可插入的本地图片文件，URL 资产不会在发布阶段下载。")
            continue
        resolved, warning = _resolve_local_asset_path(
            path,
            workspace_root=workspace_root,
            cli_working_dir=cli_working_dir,
            title=title,
        )
        if warning:
            warnings.append(warning)
            continue
        path_format = Path(resolved).suffix.lower().lstrip(".")
        if path_format not in INSERTABLE_IMAGE_FORMATS:
            warnings.append(f"图表「{title}」不是 PNG/JPEG/GIF 图片，已跳过。")
            continue
        assets.append({"caption": title, "file_path": resolved})
    return assets, warnings


def _asset_format(asset: dict[str, Any]) -> str:
    fmt = _safe_text(asset.get("format")).lower().lstrip(".")
    if fmt:
        return "jpg" if fmt == "jpeg" else fmt
    path = _safe_text(asset.get("path") or asset.get("url"))
    suffix = Path(path).suffix.lower().lstrip(".")
    return "jpg" if suffix == "jpeg" else suffix


def _resolve_local_asset_path(
    path: str,
    *,
    workspace_root: Path | None,
    cli_working_dir: Path,
    title: str,
) -> tuple[str, str]:
    if _unsafe_relative_path(path):
        return "", f"图表「{title}」图片路径不安全，已跳过。"
    candidate = Path(path)
    if candidate.is_absolute():
        if not workspace_root:
            return "", f"图表「{title}」图片路径不安全，已跳过。"
        try:
            candidate.resolve().relative_to(workspace_root)
        except (OSError, ValueError):
            return "", f"图表「{title}」图片路径不安全，已跳过。"
    elif workspace_root:
        candidate = workspace_root / candidate
    candidate = candidate.resolve()
    if workspace_root:
        try:
            candidate.relative_to(workspace_root)
        except ValueError:
            return "", f"图表「{title}」图片路径不安全，已跳过。"
    if not candidate.is_file():
        return "", f"图表「{title}」文件不存在，未插入飞书文档。"
    try:
        return candidate.relative_to(cli_working_dir).as_posix(), ""
    except ValueError:
        return "", f"图表「{title}」图片不在飞书 CLI 当前工作目录内，未插入飞书文档。"


def _unsafe_relative_path(value: str) -> bool:
    text = str(value or "").strip()
    if not text or text.startswith("~"):
        return True
    return any(part == ".." for part in Path(text).parts)


def _docx_url_or_empty(url: str | None) -> str:
    text = _safe_text(url)
    return text if "/docx/" in text else ""


def _runner_error_summary(exc: Exception) -> str:
    if isinstance(exc, FileNotFoundError):
        return "CLI 不存在或当前环境不可执行。请配置 LARK_CLI_BIN 并确认已安装、已登录。"
    if isinstance(exc, subprocess.TimeoutExpired):
        return "CLI 执行超时，请稍后重试或检查飞书 CLI 登录状态。"
    return "CLI 执行失败，请检查飞书 CLI 安装和登录状态。"


def _official_error_summary(data: dict[str, Any]) -> str:
    error = data.get("error") if isinstance(data.get("error"), dict) else {}
    parts = [
        _safe_text(error.get("type")),
        _safe_text(error.get("subtype")),
        _safe_text(error.get("message")),
        _safe_text(error.get("hint")),
    ]
    summary = "；".join(part for part in parts if part)
    return summary or "未返回安全错误摘要。"


def _cli_output_summary(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return "未返回错误摘要。"
    text = re.sub(r"(?i)\b(?:api_key|apikey|access_key|access_token|token|secret|password)\s*=\s*\S+", "", text)
    text = re.sub(r"(?i)\b(?:trace|trace_path|raw_sql|raw_rows|provider_metadata|prompt)\s*=\s*\S+", "", text)
    text = re.sub(r"(?i)\b\w*path\w*\s*=\s*\S+", "", text)
    text = re.sub(r"(?i)(?:/users/|/private/|/tmp/|/var/|~[/\\])\S+", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    safe = safe_warning(text[:240])
    return safe or "CLI 返回了错误信息，但内容包含敏感字段，已隐藏。"
