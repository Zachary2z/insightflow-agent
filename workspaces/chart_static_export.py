from __future__ import annotations

from pathlib import Path
import re
from typing import Any
from urllib.parse import quote, urlsplit

from visualization.static_renderer import option_title, render_static_chart_file, series_from_echarts_option
from workspaces.safe_output import contains_sensitive_text as _contains_sensitive_text
from workspaces.safe_output import safe_text as _safe_text
from workspaces.safe_output import safe_url as _safe_url
from workspaces.safe_output import safe_workspace_path as _safe_path
from workspaces.safe_output import unsafe_relative_path as _unsafe_relative_path


DEFAULT_CHART_STATIC_EXPORT_DIR = "exports/charts"
STATIC_IMAGE_EXTENSIONS = {".png", ".svg", ".jpg", ".jpeg", ".webp"}
FEISHU_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif"}


def export_chart_static_asset(
    chart_artifact: dict[str, Any],
    *,
    workspace_root: str | Path | None = None,
    output_dir: str | Path | None = None,
    target_format: str | None = None,
) -> dict[str, Any]:
    """Return safe static chart metadata, generating an image from existing ECharts data when possible."""
    chart = chart_artifact if isinstance(chart_artifact, dict) else {}
    chart_id = _safe_chart_id(chart)
    requested_format = _target_format(target_format)
    warnings: list[str] = []

    reused_asset = _existing_static_asset(
        chart,
        workspace_root=workspace_root,
        warnings=warnings,
        target_format=requested_format,
    )
    if reused_asset:
        return {
            "success": True,
            "asset": reused_asset,
            "chart_artifact": _with_asset_fields(chart, reused_asset),
            "warnings": warnings,
        }

    option = chart.get("echarts_option") if isinstance(chart.get("echarts_option"), dict) else {}
    if not option:
        warnings.append(f"图表 {chart_id} 缺少可复用的静态图和 echarts_option，无法生成文档图表资产。")
        return {"success": False, "asset": {}, "chart_artifact": {}, "warnings": warnings}

    target = _generation_target(
        chart,
        workspace_root=workspace_root,
        output_dir=output_dir,
        target_format=requested_format or "svg",
    )
    if not target:
        warnings.append(f"图表 {chart_id} 需要 workspace_root 才能生成安全的工作区内静态资产。")
        return {"success": False, "asset": {}, "chart_artifact": {}, "warnings": warnings}

    parsed = series_from_echarts_option(option)
    if not parsed["success"]:
        warnings.append(f"图表 {chart_id} 无法从现有 echarts_option 生成静态 SVG：{parsed['warning']}")
        return {"success": False, "asset": {}, "chart_artifact": {}, "warnings": warnings}
    chart_text = " ".join(parsed["labels"] + [item["name"] for item in parsed["series"]])
    if _contains_sensitive_text(chart_text):
        warnings.append(f"图表 {chart_id} 无法从现有 echarts_option 生成静态 SVG：图表文本包含内部或敏感信息。")
        return {"success": False, "asset": {}, "chart_artifact": {}, "warnings": warnings}

    target["absolute_path"].parent.mkdir(parents=True, exist_ok=True)
    render_static_chart_file(
        target["absolute_path"],
        title=_safe_text(chart.get("title")) or _safe_text(option_title(option)) or "导出图表",
        labels=parsed["labels"],
        series=parsed["series"],
        chart_type=_safe_text(chart.get("chart_type")) or parsed["chart_type"],
    )

    asset = _asset_metadata(
        chart=chart,
        path=target["relative_path"],
        url=_asset_url(chart=chart, path=target["relative_path"], prefer_existing=False),
        fmt=target["format"],
        generated=True,
    )
    return {
        "success": True,
        "asset": asset,
        "chart_artifact": _with_asset_fields(chart, asset),
        "warnings": warnings,
    }


def _existing_static_asset(
    chart: dict[str, Any],
    *,
    workspace_root: str | Path | None,
    warnings: list[str],
    target_format: str,
) -> dict[str, Any]:
    path = _safe_path(chart.get("image_path") or chart.get("path"), workspace_root=workspace_root)
    url = _safe_url(chart.get("image_url") or chart.get("url"))
    fmt = _asset_format(path or url)
    reusable_formats = _reusable_formats(target_format)
    if path and fmt in reusable_formats:
        return _asset_metadata(chart=chart, path=path, url=url, fmt=fmt.lstrip("."), generated=False)
    if url and fmt in reusable_formats:
        return _asset_metadata(chart=chart, path="", url=url, fmt=fmt.lstrip("."), generated=False)
    if target_format == "png" and fmt == ".svg" and chart.get("echarts_option"):
        return {}
    if chart.get("image_path") or chart.get("path") or chart.get("image_url") or chart.get("url"):
        warnings.append(f"图表 {_safe_chart_id(chart)} 的静态图路径或 URL 不安全，已拒绝复用。")
    return {}


def _generation_target(
    chart: dict[str, Any],
    *,
    workspace_root: str | Path | None,
    output_dir: str | Path | None,
    target_format: str,
) -> dict[str, Any]:
    if not workspace_root:
        return {}
    root = Path(workspace_root).resolve()
    output = Path(str(output_dir or DEFAULT_CHART_STATIC_EXPORT_DIR))
    if output.is_absolute():
        try:
            relative_output = output.resolve().relative_to(root)
        except (OSError, ValueError):
            return {}
    else:
        if _unsafe_relative_path(output.as_posix()):
            return {}
        relative_output = output
    fmt = "png" if target_format == "png" else "svg"
    filename = f"{_safe_filename(_safe_chart_id(chart))}.{fmt}"
    relative_path = (relative_output / filename).as_posix()
    absolute_path = (root / relative_path).resolve()
    try:
        absolute_path.relative_to(root)
    except ValueError:
        return {}
    return {"absolute_path": absolute_path, "relative_path": relative_path, "format": fmt}


def _asset_metadata(*, chart: dict[str, Any], path: str, url: str, fmt: str, generated: bool) -> dict[str, Any]:
    return {
        "asset_id": _safe_chart_id(chart),
        "asset_type": "chart_image",
        "title": _safe_text(chart.get("title")) or "导出图表",
        "path": path,
        "url": url,
        "format": fmt.lower().lstrip("."),
        "source": _safe_text(chart.get("source")),
        "rendering_status": "rendered",
        "generated": generated,
    }


def _with_asset_fields(chart: dict[str, Any], asset: dict[str, Any]) -> dict[str, Any]:
    updated = dict(chart)
    for key in ("path", "url", "image_path", "image_url"):
        updated.pop(key, None)
    if asset.get("path"):
        updated["path"] = asset["path"]
        updated["image_path"] = asset["path"]
    if asset.get("url"):
        updated["url"] = asset["url"]
        updated["image_url"] = asset["url"]
    updated["rendering_status"] = "rendered"
    return updated


def _asset_url(*, chart: dict[str, Any], path: str, prefer_existing: bool = True) -> str:
    existing = _safe_url(chart.get("image_url") or chart.get("url"))
    if prefer_existing and existing:
        return existing
    workspace_id = _safe_text(chart.get("workspace_id"))
    return f"/api/workspaces/{quote(workspace_id)}/artifacts/{quote(path, safe='/')}" if workspace_id else ""


def _asset_format(value: str) -> str:
    return Path(urlsplit(str(value or "")).path).suffix.lower()


def _target_format(value: str | None) -> str:
    return "png" if _safe_text(value).lower().lstrip(".") == "png" else ""


def _reusable_formats(target_format: str) -> set[str]:
    return FEISHU_IMAGE_EXTENSIONS if target_format == "png" else STATIC_IMAGE_EXTENSIONS


def _safe_chart_id(chart: dict[str, Any]) -> str:
    return _safe_text(chart.get("artifact_id") or chart.get("chart_id") or chart.get("title")) or "chart_static_asset"


def _safe_filename(value: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_-]+", "_", str(value or "").strip())
    return safe.strip("_") or "chart_static_asset"
