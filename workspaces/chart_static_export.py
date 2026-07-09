from __future__ import annotations

from html import escape
from pathlib import Path
import re
from typing import Any
from urllib.parse import parse_qsl, quote, urlsplit


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
    """Return safe static chart asset metadata, generating SVG from existing ECharts data when possible."""
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

    series_result = _series_from_echarts_option(option)
    if not series_result["success"]:
        warnings.append(f"图表 {chart_id} 无法从现有 echarts_option 生成静态 SVG：{series_result['warning']}")
        return {"success": False, "asset": {}, "chart_artifact": {}, "warnings": warnings}

    target["absolute_path"].parent.mkdir(parents=True, exist_ok=True)
    title = _safe_text(chart.get("title")) or _safe_text(_option_title(option)) or "导出图表"
    if target["format"] == "png":
        _render_png_file(
            target["absolute_path"],
            title=title,
            labels=series_result["labels"],
            series=series_result["series"],
            chart_type=_safe_text(chart.get("chart_type")) or series_result["chart_type"],
        )
    else:
        svg = _render_svg(
            title=title,
            labels=series_result["labels"],
            series=series_result["series"],
            chart_type=_safe_text(chart.get("chart_type")) or series_result["chart_type"],
        )
        target["absolute_path"].write_text(svg, encoding="utf-8")

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


def export_chart_static_assets(
    chart_artifacts: list[Any],
    *,
    workspace_root: str | Path | None = None,
    output_dir: str | Path | None = None,
) -> list[dict[str, Any]]:
    return [
        export_chart_static_asset(
            artifact,
            workspace_root=workspace_root,
            output_dir=output_dir,
        )
        for artifact in chart_artifacts
        if isinstance(artifact, dict)
    ]


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


def _series_from_echarts_option(option: dict[str, Any]) -> dict[str, Any]:
    series_items = option.get("series")
    if isinstance(series_items, dict):
        series_items = [series_items]
    if not isinstance(series_items, list) or not series_items:
        return {"success": False, "warning": "缺少 series 数据。"}

    parsed_series: list[dict[str, Any]] = []
    max_len = 0
    chart_type = "bar"
    for index, item in enumerate(series_items):
        if not isinstance(item, dict):
            continue
        raw_data = item.get("data")
        if not isinstance(raw_data, list) or not raw_data:
            continue
        values = [_numeric_value(value) for value in raw_data]
        if not any(value is not None for value in values):
            continue
        labels_from_data = [_data_label(value) for value in raw_data]
        chart_type = _safe_text(item.get("type")) or chart_type
        parsed_series.append(
            {
                "name": _safe_text(item.get("name")) or f"系列{index + 1}",
                "values": [0.0 if value is None else value for value in values],
                "labels_from_data": labels_from_data,
            }
        )
        max_len = max(max_len, len(values))

    if not parsed_series or max_len <= 0:
        return {"success": False, "warning": "series 中没有可绘制的数值。"}

    labels = _axis_labels(option)
    if not labels:
        labels = _first_non_empty_labels(parsed_series)
    if not labels:
        labels = [str(index + 1) for index in range(max_len)]
    labels = [_safe_text(label) or str(index + 1) for index, label in enumerate(labels[:max_len])]
    if _contains_sensitive_text(" ".join(labels + [series["name"] for series in parsed_series])):
        return {"success": False, "warning": "图表文本包含内部或敏感信息。"}
    return {"success": True, "labels": labels, "series": parsed_series, "chart_type": chart_type}


def _axis_labels(option: dict[str, Any]) -> list[str]:
    axis = option.get("xAxis")
    if isinstance(axis, list):
        axis = next((item for item in axis if isinstance(item, dict) and isinstance(item.get("data"), list)), {})
    if isinstance(axis, dict) and isinstance(axis.get("data"), list):
        return [_safe_text(item) for item in axis.get("data") or []]
    return []


def _first_non_empty_labels(series: list[dict[str, Any]]) -> list[str]:
    for item in series:
        labels = [_safe_text(label) for label in item.get("labels_from_data") or []]
        if any(labels):
            return labels
    return []


def _numeric_value(value: Any) -> float | None:
    if isinstance(value, dict):
        value = value.get("value")
    if isinstance(value, (list, tuple)):
        numeric_values = [_numeric_value(item) for item in value]
        return next((item for item in reversed(numeric_values) if item is not None), None)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _data_label(value: Any) -> str:
    if isinstance(value, dict):
        return _safe_text(value.get("name"))
    if isinstance(value, (list, tuple)) and value:
        return _safe_text(value[0])
    return ""


def _render_svg(*, title: str, labels: list[str], series: list[dict[str, Any]], chart_type: str) -> str:
    width = 920
    height = 540
    left = 88
    right = 36
    top = 78
    bottom = 92
    chart_width = width - left - right
    chart_height = height - top - bottom
    palette = ["#2563eb", "#16a34a", "#dc2626", "#9333ea", "#f59e0b"]
    all_values = [abs(value) for item in series for value in item["values"]]
    max_value = max(all_values) if all_values else 1.0
    max_value = max(max_value, 1.0)
    category_count = max(len(labels), 1)
    category_width = chart_width / category_count
    bar_gap = 6
    series_count = max(len(series), 1)
    bar_width = max(8, (category_width - 18) / series_count - bar_gap)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{escape(title)}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<text x="{left}" y="36" font-family="Arial, sans-serif" font-size="22" font-weight="700" fill="#111827">{escape(title)}</text>',
        f'<line x1="{left}" y1="{top + chart_height}" x2="{left + chart_width}" y2="{top + chart_height}" stroke="#9ca3af" stroke-width="1"/>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + chart_height}" stroke="#9ca3af" stroke-width="1"/>',
    ]

    for tick in range(5):
        value = max_value * tick / 4
        y = top + chart_height - (value / max_value * chart_height)
        parts.append(f'<line x1="{left}" y1="{y:.1f}" x2="{left + chart_width}" y2="{y:.1f}" stroke="#e5e7eb" stroke-width="1"/>')
        parts.append(f'<text x="{left - 10}" y="{y + 4:.1f}" text-anchor="end" font-family="Arial, sans-serif" font-size="11" fill="#6b7280">{escape(_format_number(value))}</text>')

    if chart_type == "line" and len(series) == 1:
        points = []
        values = series[0]["values"]
        for index, value in enumerate(values[: len(labels)]):
            x = left + category_width * index + category_width / 2
            y = top + chart_height - (max(value, 0.0) / max_value * chart_height)
            points.append(f"{x:.1f},{y:.1f}")
        parts.append(f'<polyline points="{" ".join(points)}" fill="none" stroke="{palette[0]}" stroke-width="3"/>')
        for point in points:
            x, y = point.split(",")
            parts.append(f'<circle cx="{x}" cy="{y}" r="4" fill="{palette[0]}"/>')
    else:
        for series_index, item in enumerate(series):
            color = palette[series_index % len(palette)]
            for label_index, value in enumerate(item["values"][: len(labels)]):
                bar_height = max(value, 0.0) / max_value * chart_height
                x = left + category_width * label_index + 12 + series_index * (bar_width + bar_gap)
                y = top + chart_height - bar_height
                parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_width:.1f}" height="{bar_height:.1f}" rx="2" fill="{color}"/>')
                if bar_height > 18:
                    parts.append(f'<text x="{x + bar_width / 2:.1f}" y="{y - 6:.1f}" text-anchor="middle" font-family="Arial, sans-serif" font-size="10" fill="#374151">{escape(_format_number(value))}</text>')

    for index, label in enumerate(labels):
        x = left + category_width * index + category_width / 2
        clipped = _clip_label(label, 12)
        parts.append(f'<text x="{x:.1f}" y="{height - 48}" text-anchor="middle" font-family="Arial, sans-serif" font-size="12" fill="#374151">{escape(clipped)}</text>')

    legend_x = left
    legend_y = height - 22
    for index, item in enumerate(series[:5]):
        x = legend_x + index * 150
        parts.append(f'<rect x="{x}" y="{legend_y - 10}" width="10" height="10" fill="{palette[index % len(palette)]}"/>')
        parts.append(f'<text x="{x + 16}" y="{legend_y}" font-family="Arial, sans-serif" font-size="12" fill="#374151">{escape(_clip_label(item["name"], 16))}</text>')

    parts.append("</svg>")
    return "\n".join(parts)


def _render_png_file(
    path: Path,
    *,
    title: str,
    labels: list[str],
    series: list[dict[str, Any]],
    chart_type: str,
) -> None:
    from PIL import Image, ImageDraw, ImageFont

    width = 920
    height = 540
    left = 88
    right = 36
    top = 78
    bottom = 92
    chart_width = width - left - right
    chart_height = height - top - bottom
    palette = ["#2563eb", "#16a34a", "#dc2626", "#9333ea", "#f59e0b"]
    all_values = [abs(float(value)) for item in series for value in item["values"]]
    max_value = max(all_values) if all_values else 1.0
    max_value = max(max_value, 1.0)
    category_count = max(len(labels), 1)
    category_width = chart_width / category_count
    series_count = max(len(series), 1)
    bar_gap = 6
    bar_width = max(8, (category_width - 18) / series_count - bar_gap)

    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    title_font = _load_font(ImageFont, 22, bold=True)
    text_font = _load_font(ImageFont, 12)
    tick_font = _load_font(ImageFont, 11)

    _draw_text(draw, (left, 20), title, fill="#111827", font=title_font)
    draw.line((left, top + chart_height, left + chart_width, top + chart_height), fill="#9ca3af", width=1)
    draw.line((left, top, left, top + chart_height), fill="#9ca3af", width=1)

    for tick in range(5):
        value = max_value * tick / 4
        y = top + chart_height - (value / max_value * chart_height)
        draw.line((left, y, left + chart_width, y), fill="#e5e7eb", width=1)
        tick_text = _format_number(value)
        bbox = draw.textbbox((0, 0), tick_text, font=tick_font)
        _draw_text(draw, (left - 14 - (bbox[2] - bbox[0]), y - 7), tick_text, fill="#6b7280", font=tick_font)

    if chart_type == "line" and len(series) == 1:
        points: list[tuple[float, float]] = []
        for index, value in enumerate(series[0]["values"][: len(labels)]):
            x = left + category_width * index + category_width / 2
            y = top + chart_height - (max(float(value), 0.0) / max_value * chart_height)
            points.append((x, y))
        if len(points) >= 2:
            draw.line(points, fill=palette[0], width=3)
        for x, y in points:
            draw.ellipse((x - 4, y - 4, x + 4, y + 4), fill=palette[0])
    else:
        for series_index, item in enumerate(series):
            color = palette[series_index % len(palette)]
            for label_index, value in enumerate(item["values"][: len(labels)]):
                numeric_value = max(float(value), 0.0)
                bar_height = numeric_value / max_value * chart_height
                x = left + category_width * label_index + 12 + series_index * (bar_width + bar_gap)
                y = top + chart_height - bar_height
                draw.rectangle((x, y, x + bar_width, top + chart_height), fill=color)
                if bar_height > 18:
                    value_text = _format_number(numeric_value)
                    bbox = draw.textbbox((0, 0), value_text, font=tick_font)
                    _draw_text(
                        draw,
                        (x + bar_width / 2 - (bbox[2] - bbox[0]) / 2, y - 18),
                        value_text,
                        fill="#374151",
                        font=tick_font,
                    )

    for index, label in enumerate(labels):
        x = left + category_width * index + category_width / 2
        text = _clip_label(label, 12)
        bbox = draw.textbbox((0, 0), text, font=text_font)
        _draw_text(draw, (x - (bbox[2] - bbox[0]) / 2, height - 58), text, fill="#374151", font=text_font)

    legend_y = height - 30
    for index, item in enumerate(series[:5]):
        x = left + index * 150
        draw.rectangle((x, legend_y - 10, x + 10, legend_y), fill=palette[index % len(palette)])
        _draw_text(draw, (x + 16, legend_y - 14), _clip_label(item["name"], 16), fill="#374151", font=text_font)

    image.save(path, format="PNG")


def _load_font(image_font: Any, size: int, *, bold: bool = False) -> Any:
    candidates = [
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for candidate in candidates:
        if not candidate or not Path(candidate).exists():
            continue
        try:
            return image_font.truetype(candidate, size=size)
        except OSError:
            continue
    return image_font.load_default()


def _draw_text(draw: Any, xy: tuple[float, float], text: str, *, fill: str, font: Any) -> None:
    try:
        draw.text(xy, text, fill=fill, font=font)
    except UnicodeEncodeError:
        draw.text(xy, text.encode("ascii", "ignore").decode("ascii") or "chart", fill=fill, font=font)


def _asset_metadata(
    *,
    chart: dict[str, Any],
    path: str,
    url: str,
    fmt: str,
    generated: bool,
) -> dict[str, Any]:
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
    if not workspace_id:
        return ""
    return f"/api/workspaces/{quote(workspace_id)}/artifacts/{quote(path, safe='/')}"


def _safe_path(value: Any, *, workspace_root: str | Path | None) -> str:
    text = _safe_text(value)
    if not text:
        return ""
    if _unsafe_relative_path(text):
        return ""
    path = Path(text)
    if not path.is_absolute():
        return path.as_posix()
    if not workspace_root:
        return ""
    try:
        return path.resolve().relative_to(Path(workspace_root).resolve()).as_posix()
    except (OSError, ValueError):
        return ""


def _safe_url(value: Any) -> str:
    text = _safe_text(value)
    if not text or _url_has_secret_marker(text):
        return ""
    if text.startswith("/api/") or text.startswith("http://") or text.startswith("https://"):
        return text
    return ""


def _asset_format(value: str) -> str:
    path = urlsplit(str(value or "")).path
    return Path(path).suffix.lower()


def _target_format(value: str | None) -> str:
    text = _safe_text(value).lower().lstrip(".")
    return "png" if text == "png" else ""


def _reusable_formats(target_format: str) -> set[str]:
    if target_format == "png":
        return FEISHU_IMAGE_EXTENSIONS
    return STATIC_IMAGE_EXTENSIONS


def _option_title(option: dict[str, Any]) -> str:
    title = option.get("title")
    if isinstance(title, dict):
        return _safe_text(title.get("text"))
    return ""


def _safe_chart_id(chart: dict[str, Any]) -> str:
    return _safe_text(chart.get("artifact_id") or chart.get("chart_id") or chart.get("title")) or "chart_static_asset"


def _safe_filename(value: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_-]+", "_", str(value or "").strip())
    return safe.strip("_") or "chart_static_asset"


def _safe_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return "" if _contains_sensitive_text(text) else text


def _unsafe_relative_path(value: str) -> bool:
    text = value.strip()
    if text.startswith("~"):
        return True
    return any(part == ".." for part in Path(text).parts)


def _url_has_secret_marker(value: str) -> bool:
    secret_keys = {"api_key", "apikey", "access_key", "access_token", "token", "secret", "password", "key"}
    lower = value.lower()
    if any(marker in lower for marker in ("api_key=", "access_token=", "token=", "secret=", "password=")):
        return True
    try:
        parsed = urlsplit(value)
    except ValueError:
        return True
    return any(key.lower() in secret_keys for key, _ in parse_qsl(parsed.query, keep_blank_values=True))


def _contains_sensitive_text(value: str) -> bool:
    text = str(value or "").strip()
    if not text:
        return False
    lowered = text.lower()
    if re.search(r"\b(?:select|with|insert|update|delete|drop|alter|create|pragma)\b", text, re.IGNORECASE):
        return True
    if re.search(r"(^|[=/\s])(?:/users/|/tmp/|~[/\\])", lowered):
        return True
    if re.search(r"\b(?:raw_sql|generated_sql|raw_rows|trace_path|trace_id|provider_metadata|api_key|apikey|access_key|access_token|secret|password|database_path|analysis\.db|task_id|task_purpose|debug_id|prompt(?:_id|_text|_version)?|completion_tokens|prompt_tokens)\b", lowered):
        return True
    if re.search(r"\bsk-[A-Za-z0-9_-]+", text):
        return True
    return False


def _format_number(value: float) -> str:
    return f"{value:,.0f}" if float(value).is_integer() else f"{value:,.2f}"


def _clip_label(value: str, limit: int) -> str:
    text = str(value or "")
    return text if len(text) <= limit else f"{text[: limit - 1]}..."
