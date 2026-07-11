from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Any


PALETTE = ["#2563eb", "#16a34a", "#dc2626", "#9333ea", "#f59e0b"]


def series_from_echarts_option(option: dict[str, Any]) -> dict[str, Any]:
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
        chart_type = _text(item.get("type")) or chart_type
        parsed_series.append(
            {
                "name": _text(item.get("name")) or f"系列{index + 1}",
                "values": [0.0 if value is None else value for value in values],
                "labels_from_data": labels_from_data,
            }
        )
        max_len = max(max_len, len(values))

    if not parsed_series or max_len <= 0:
        return {"success": False, "warning": "series 中没有可绘制的数值。"}

    labels = _axis_labels(option) or _first_non_empty_labels(parsed_series)
    if not labels:
        labels = [str(index + 1) for index in range(max_len)]
    labels = [_text(label) or str(index + 1) for index, label in enumerate(labels[:max_len])]
    return {"success": True, "labels": labels, "series": parsed_series, "chart_type": chart_type}


def render_static_chart_file(
    path: str | Path,
    *,
    title: str,
    labels: list[str],
    series: list[dict[str, Any]],
    chart_type: str,
    annotation: str = "",
    unit: str = "",
    show_value_labels: bool = True,
) -> None:
    target = Path(path)
    if target.suffix.lower() == ".png":
        _render_png(
            target,
            title=title,
            labels=labels,
            series=series,
            chart_type=chart_type,
            annotation=annotation,
            unit=unit,
            show_value_labels=show_value_labels,
        )
        return
    target.write_text(
        _render_svg(
            title=title,
            labels=labels,
            series=series,
            chart_type=chart_type,
            annotation=annotation,
            unit=unit,
            show_value_labels=show_value_labels,
        ),
        encoding="utf-8",
    )


def option_title(option: dict[str, Any]) -> str:
    title = option.get("title")
    return _text(title.get("text")) if isinstance(title, dict) else ""


def _layout(annotation: str) -> dict[str, int]:
    return {
        "width": 920,
        "height": 560 if annotation else 540,
        "left": 88,
        "right": 36,
        "top": 78,
        "bottom": 112 if annotation else 92,
    }


def _render_png(
    path: Path,
    *,
    title: str,
    labels: list[str],
    series: list[dict[str, Any]],
    chart_type: str,
    annotation: str,
    unit: str,
    show_value_labels: bool,
) -> None:
    from PIL import Image, ImageDraw, ImageFont

    layout = _layout(annotation)
    width, height = layout["width"], layout["height"]
    left, right, top, bottom = layout["left"], layout["right"], layout["top"], layout["bottom"]
    chart_width, chart_height = width - left - right, height - top - bottom
    values = [float(value) for item in series for value in item.get("values", [])]
    max_value = max([abs(value) for value in values] or [1.0]) or 1.0
    category_count = max(len(labels), 1)
    category_width = chart_width / category_count

    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    title_font = _load_font(ImageFont, 22, bold=True)
    text_font = _load_font(ImageFont, 12)
    tick_font = _load_font(ImageFont, 11)

    _draw_text(draw, (left, 20), title, fill="#111827", font=title_font)
    _draw_axes(draw, left, top, chart_width, chart_height, max_value, tick_font, unit)

    mode = _render_mode(chart_type)
    if mode == "line":
        _draw_png_lines(draw, labels, series, left, top, chart_width, chart_height, max_value, show_value_labels, tick_font, unit)
    elif mode == "scatter":
        _draw_png_scatter(draw, labels, series, left, top, chart_width, chart_height, max_value, chart_type)
    elif mode == "funnel":
        _draw_png_funnel(draw, labels, series, left, top, chart_width, chart_height, max_value, text_font, unit)
    elif mode == "heatmap":
        _draw_png_heatmap(draw, labels, series, left, top, chart_width, chart_height, max_value, text_font, unit)
    else:
        _draw_png_bars(draw, labels, series, left, top, chart_width, chart_height, max_value, show_value_labels, tick_font, unit)

    if mode not in {"scatter", "funnel", "heatmap"}:
        _draw_category_labels(draw, labels, left, top + chart_height, category_width, text_font)
    _draw_legend(draw, series, left, height - (50 if annotation else 30), text_font)
    if annotation:
        _draw_text(draw, (left, height - 24), _clip_label(annotation, 95), fill="#4b5563", font=text_font)
    image.save(path, format="PNG")


def _draw_axes(draw: Any, left: int, top: int, width: int, height: int, max_value: float, font: Any, unit: str) -> None:
    draw.line((left, top + height, left + width, top + height), fill="#9ca3af", width=1)
    draw.line((left, top, left, top + height), fill="#9ca3af", width=1)
    for tick in range(5):
        value = max_value * tick / 4
        y = top + height - (value / max_value * height)
        draw.line((left, y, left + width, y), fill="#e5e7eb", width=1)
        label = _format_value(value, unit)
        bbox = draw.textbbox((0, 0), label, font=font)
        _draw_text(draw, (left - 14 - (bbox[2] - bbox[0]), y - 7), label, fill="#6b7280", font=font)


def _draw_png_lines(draw: Any, labels: list[str], series: list[dict[str, Any]], left: int, top: int, width: int, height: int, max_value: float, show_values: bool, font: Any, unit: str) -> None:
    slot = width / max(len(labels), 1)
    for series_index, item in enumerate(series):
        points = [
            (left + slot * index + slot / 2, top + height - max(float(value), 0.0) / max_value * height)
            for index, value in enumerate(item.get("values", [])[: len(labels)])
        ]
        if len(points) >= 2:
            draw.line(points, fill=PALETTE[series_index % len(PALETTE)], width=3)
        for point_index, (x, y) in enumerate(points):
            color = PALETTE[series_index % len(PALETTE)]
            draw.ellipse((x - 4, y - 4, x + 4, y + 4), fill=color)
            if show_values:
                value = float(item["values"][point_index])
                _draw_text(draw, (x - 12, y - 20), _format_value(value, unit), fill="#374151", font=font)


def _draw_png_scatter(draw: Any, labels: list[str], series: list[dict[str, Any]], left: int, top: int, width: int, height: int, max_y: float, chart_type: str) -> None:
    x_values = [_float_or_index(label, index) for index, label in enumerate(labels)]
    max_x = max([abs(value) for value in x_values] or [1.0]) or 1.0
    all_y = [float(value) for item in series for value in item.get("values", [])]
    for series_index, item in enumerate(series):
        color = PALETTE[series_index % len(PALETTE)]
        for index, value in enumerate(item.get("values", [])[: len(x_values)]):
            x = left + max(x_values[index], 0.0) / max_x * width
            y = top + height - max(float(value), 0.0) / max_y * height
            draw.ellipse((x - 5, y - 5, x + 5, y + 5), fill=color)
    if chart_type == "risk_matrix" and x_values and all_y:
        mean_x = sum(x_values) / len(x_values)
        mean_y = sum(all_y) / len(all_y)
        x = left + max(mean_x, 0.0) / max_x * width
        y = top + height - max(mean_y, 0.0) / max_y * height
        draw.line((x, top, x, top + height), fill="#6b7280", width=1)
        draw.line((left, y, left + width, y), fill="#6b7280", width=1)


def _draw_png_bars(draw: Any, labels: list[str], series: list[dict[str, Any]], left: int, top: int, width: int, height: int, max_value: float, show_values: bool, font: Any, unit: str) -> None:
    category_width = width / max(len(labels), 1)
    series_count = max(len(series), 1)
    gap = 6
    bar_width = max(8, (category_width - 18) / series_count - gap)
    for series_index, item in enumerate(series):
        color = PALETTE[series_index % len(PALETTE)]
        for label_index, value in enumerate(item.get("values", [])[: len(labels)]):
            numeric = max(float(value), 0.0)
            bar_height = numeric / max_value * height
            x = left + category_width * label_index + 12 + series_index * (bar_width + gap)
            y = top + height - bar_height
            draw.rectangle((x, y, x + bar_width, top + height), fill=color)
            if show_values and bar_height > 18:
                _draw_text(draw, (x, y - 18), _format_value(numeric, unit), fill="#374151", font=font)


def _draw_png_funnel(draw: Any, labels: list[str], series: list[dict[str, Any]], left: int, top: int, width: int, height: int, max_value: float, font: Any, unit: str) -> None:
    values = list(series[0].get("values", []))[: len(labels)] if series else []
    row_height = height / max(len(values), 1)
    for index, value in enumerate(values):
        bar_width = max(float(value), 0.0) / max_value * width
        x = left + (width - bar_width) / 2
        y = top + index * row_height + 4
        draw.rectangle((x, y, x + bar_width, y + row_height - 8), fill=PALETTE[index % len(PALETTE)])
        _draw_text(draw, (left + 4, y + 4), f"{_clip_label(labels[index], 14)}  {_format_value(float(value), unit)}", fill="#111827", font=font)


def _draw_png_heatmap(draw: Any, labels: list[str], series: list[dict[str, Any]], left: int, top: int, width: int, height: int, max_value: float, font: Any, unit: str) -> None:
    cell_width = width / max(len(labels), 1)
    cell_height = height / max(len(series), 1)
    for row_index, item in enumerate(series):
        for column_index, value in enumerate(item.get("values", [])[: len(labels)]):
            intensity = min(max(float(value), 0.0) / max_value, 1.0)
            color = (round(239 - 202 * intensity), round(246 - 147 * intensity), round(255 - 20 * intensity))
            x = left + column_index * cell_width
            y = top + row_index * cell_height
            draw.rectangle((x, y, x + cell_width, y + cell_height), fill=color, outline="#ffffff")
            _draw_text(draw, (x + 6, y + 6), _format_value(float(value), unit), fill="#111827", font=font)
        _draw_text(draw, (left + 6, top + row_index * cell_height + cell_height - 18), _clip_label(item.get("name", ""), 14), fill="#374151", font=font)


def _draw_category_labels(draw: Any, labels: list[str], left: int, baseline: int, slot: float, font: Any) -> None:
    for index, label in enumerate(labels):
        text = _clip_label(label, 12)
        bbox = draw.textbbox((0, 0), text, font=font)
        x = left + slot * index + slot / 2 - (bbox[2] - bbox[0]) / 2
        _draw_text(draw, (x, baseline + 14), text, fill="#374151", font=font)


def _draw_legend(draw: Any, series: list[dict[str, Any]], left: int, y: int, font: Any) -> None:
    for index, item in enumerate(series[:5]):
        x = left + index * 150
        draw.rectangle((x, y - 10, x + 10, y), fill=PALETTE[index % len(PALETTE)])
        _draw_text(draw, (x + 16, y - 14), _clip_label(item.get("name", ""), 16), fill="#374151", font=font)


def _render_svg(*, title: str, labels: list[str], series: list[dict[str, Any]], chart_type: str, annotation: str, unit: str, show_value_labels: bool) -> str:
    layout = _layout(annotation)
    width, height = layout["width"], layout["height"]
    left, right, top, bottom = layout["left"], layout["right"], layout["top"], layout["bottom"]
    chart_width, chart_height = width - left - right, height - top - bottom
    all_values = [abs(float(value)) for item in series for value in item.get("values", [])]
    max_value = max(all_values or [1.0]) or 1.0
    slot = chart_width / max(len(labels), 1)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{escape(title)}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<text x="{left}" y="36" font-family="Arial, sans-serif" font-size="22" font-weight="700" fill="#111827">{escape(title)}</text>',
        f'<line x1="{left}" y1="{top + chart_height}" x2="{left + chart_width}" y2="{top + chart_height}" stroke="#9ca3af"/>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + chart_height}" stroke="#9ca3af"/>',
    ]
    for tick in range(5):
        value = max_value * tick / 4
        y = top + chart_height - value / max_value * chart_height
        parts.extend([
            f'<line x1="{left}" y1="{y:.1f}" x2="{left + chart_width}" y2="{y:.1f}" stroke="#e5e7eb"/>',
            f'<text x="{left - 10}" y="{y + 4:.1f}" text-anchor="end" font-family="Arial, sans-serif" font-size="11" fill="#6b7280">{escape(_format_value(value, unit))}</text>',
        ])
    if _render_mode(chart_type) == "line":
        for index, item in enumerate(series):
            points = [f"{left + slot * position + slot / 2:.1f},{top + chart_height - max(float(value), 0.0) / max_value * chart_height:.1f}" for position, value in enumerate(item.get("values", [])[: len(labels)])]
            parts.append(f'<polyline points="{" ".join(points)}" fill="none" stroke="{PALETTE[index % len(PALETTE)]}" stroke-width="3"/>')
    else:
        count = max(len(series), 1)
        gap = 6
        bar_width = max(8, (slot - 18) / count - gap)
        for series_index, item in enumerate(series):
            for label_index, value in enumerate(item.get("values", [])[: len(labels)]):
                bar_height = max(float(value), 0.0) / max_value * chart_height
                x = left + slot * label_index + 12 + series_index * (bar_width + gap)
                y = top + chart_height - bar_height
                parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_width:.1f}" height="{bar_height:.1f}" rx="2" fill="{PALETTE[series_index % len(PALETTE)]}"/>')
                if show_value_labels and bar_height > 18:
                    parts.append(f'<text x="{x + bar_width / 2:.1f}" y="{y - 6:.1f}" text-anchor="middle" font-family="Arial, sans-serif" font-size="10" fill="#374151">{escape(_format_value(float(value), unit))}</text>')
    for index, label in enumerate(labels):
        x = left + slot * index + slot / 2
        parts.append(f'<text x="{x:.1f}" y="{top + chart_height + 28}" text-anchor="middle" font-family="Arial, sans-serif" font-size="12" fill="#374151">{escape(_clip_label(label, 12))}</text>')
    if annotation:
        parts.append(f'<text x="{left}" y="{height - 18}" font-family="Arial, sans-serif" font-size="12" fill="#4b5563">{escape(_clip_label(annotation, 95))}</text>')
    parts.append("</svg>")
    return "\n".join(parts)


def _axis_labels(option: dict[str, Any]) -> list[str]:
    axis = option.get("xAxis")
    if isinstance(axis, list):
        axis = next((item for item in axis if isinstance(item, dict) and isinstance(item.get("data"), list)), {})
    return [_text(item) for item in axis.get("data", [])] if isinstance(axis, dict) and isinstance(axis.get("data"), list) else []


def _first_non_empty_labels(series: list[dict[str, Any]]) -> list[str]:
    for item in series:
        labels = [_text(label) for label in item.get("labels_from_data", [])]
        if any(labels):
            return labels
    return []


def _numeric_value(value: Any) -> float | None:
    if isinstance(value, dict):
        value = value.get("value")
    if isinstance(value, (list, tuple)):
        numeric = [_numeric_value(item) for item in value]
        return next((item for item in reversed(numeric) if item is not None), None)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _data_label(value: Any) -> str:
    if isinstance(value, dict):
        return _text(value.get("name"))
    return _text(value[0]) if isinstance(value, (list, tuple)) and value else ""


def _load_font(image_font: Any, size: int, *, bold: bool = False) -> Any:
    candidates = [
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            try:
                return image_font.truetype(candidate, size=size)
            except OSError:
                pass
    return image_font.load_default()


def _draw_text(draw: Any, xy: tuple[float, float], text: str, *, fill: str, font: Any) -> None:
    try:
        draw.text(xy, str(text), fill=fill, font=font)
    except UnicodeEncodeError:
        draw.text(xy, str(text).encode("ascii", "ignore").decode("ascii") or "chart", fill=fill, font=font)


def _render_mode(chart_type: str) -> str:
    value = str(chart_type or "").lower()
    if value in {"line", "dual_axis_line"}:
        return "line"
    if value in {"scatter", "risk_matrix"}:
        return "scatter"
    if value == "funnel":
        return "funnel"
    if value == "heatmap":
        return "heatmap"
    return "bar"


def _float_or_index(value: Any, index: int) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(index + 1)


def _text(value: Any) -> str:
    return str(value or "").strip()


def _format_value(value: float, unit: str) -> str:
    label = f"{value:,.0f}" if float(value).is_integer() else f"{value:,.2f}"
    return f"{label}{unit}" if unit else label


def _clip_label(value: Any, limit: int) -> str:
    text = str(value or "")
    return text if len(text) <= limit else f"{text[: limit - 1]}..."
