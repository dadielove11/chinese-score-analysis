from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from html import escape
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .models import ScoreLine, ScoreRecord


@dataclass(frozen=True)
class PositionedLabel:
    series: str
    text: str
    x: float
    y: float
    box: tuple[float, float, float, float]


def line_chart_svg(
    records: list[ScoreRecord],
    value: str,
    title: str,
    invert_rank: bool = False,
    exam_order: list[str] | None = None,
    reference_lines: list[ScoreLine] | None = None,
) -> str:
    width = 760
    height = 360
    pad_left = 56
    pad_top = 52
    pad_bottom = 66

    labels = exam_order or [record.exam_name for record in records]
    record_by_exam = {record.exam_name: record for record in records}
    ordered_values: list[float | None] = []
    for label in labels:
        record = record_by_exam.get(label)
        raw_value = getattr(record, value) if record else None
        ordered_values.append(float(raw_value) if raw_value is not None else None)

    values = [raw for raw in ordered_values if raw is not None]
    if not values:
        return "<div class='empty'>暂无可绘制数据</div>"

    min_v = min(values)
    max_v = max(values)
    if min_v == max_v:
        min_v -= 1
        max_v += 1

    show_refs = bool(reference_lines) and value == "score" and not invert_rank
    visible_refs: list[ScoreLine] = []
    if show_refs:
        for line in reference_lines or []:
            if min_v - 8 <= line.score <= max_v + 8:
                visible_refs.append(line)
                if line.score < min_v:
                    min_v = line.score
                if line.score > max_v:
                    max_v = line.score

    y_buffer = (max_v - min_v) * 0.08 or 1
    min_v -= y_buffer
    max_v += y_buffer

    pad_right = 96 if visible_refs else 32
    plot_w = width - pad_left - pad_right
    plot_h = height - pad_top - pad_bottom
    step = plot_w / max(1, len(labels) - 1) if len(labels) > 1 else 0

    def y_for(raw: float) -> float:
        ratio = (raw - min_v) / (max_v - min_v)
        if invert_rank:
            ratio = 1 - ratio
        return pad_top + (1 - ratio) * plot_h

    points: list[tuple[float, float, float] | None] = []
    for index, raw in enumerate(ordered_values):
        if raw is None:
            points.append(None)
            continue
        x = pad_left + index * step if len(labels) > 1 else pad_left + plot_w / 2
        points.append((x, y_for(raw), raw))

    segments: list[list[tuple[float, float, float]]] = []
    current: list[tuple[float, float, float]] = []
    for point in points:
        if point is None:
            if current:
                segments.append(current)
                current = []
            continue
        current.append(point)
    if current:
        segments.append(current)

    path_nodes = "\n".join(
        f"<polyline points=\"{' '.join(f'{x:.1f},{y:.1f}' for x, y, _ in segment)}\" fill=\"none\" class=\"series\"/>"
        for segment in segments
    )
    point_nodes = "\n".join(
        f"<circle cx='{x:.1f}' cy='{y:.1f}' r='5'/>"
        f"<text x='{x:.1f}' y='{y - 20:.1f}' text-anchor='middle' class='value-label'>{raw:g}</text>"
        for point in points
        if point is not None
        for x, y, raw in [point]
    )

    missing_y = pad_top + plot_h
    missing_nodes = "\n".join(
        f"<circle cx='{pad_left + index * step:.1f}' cy='{missing_y:.1f}' r='5' class='missing-point'/>"
        f"<text x='{pad_left + index * step:.1f}' y='{missing_y - 12:.1f}' text-anchor='middle' class='missing-label'>缺</text>"
        for index, raw in enumerate(ordered_values)
        if raw is None
    )
    label_nodes = "\n".join(
        f"<text x='{pad_left + index * step:.1f}' y='{height - 24}' text-anchor='middle' class='axis-label'>{escape(label)}</text>"
        for index, label in enumerate(labels)
    )

    ref_nodes = ""
    if visible_refs:
        ref_parts: list[str] = []
        for line in visible_refs:
            y = y_for(line.score)
            ref_parts.append(
                f"<line x1='{pad_left:.1f}' y1='{y:.1f}' x2='{width - pad_right:.1f}' y2='{y:.1f}' class='line-ref'/>"
                f"<text x='{width - pad_right + 6:.1f}' y='{y + 4:.1f}' text-anchor='start' class='line-ref-label'>{escape(line.label)}线 {line.score:g}</text>"
            )
        ref_nodes = "\n".join(ref_parts)

    return f"""
<svg viewBox="0 0 {width} {height}" class="line-chart" role="img" aria-label="{escape(title)}">
  <style><![CDATA[
    .line-chart {{ background: #fffdf8; }}
    .axis {{ stroke: #b8aa95; stroke-width: 1; }}
    .series {{ stroke: #3e5d52; stroke-width: 2.5; fill: none; }}
    circle {{ fill: #9b2c1f; stroke: #fffdf8; stroke-width: 1.5; }}
    text {{ fill: #6f6759; font-family: "Microsoft YaHei", "SimSun", sans-serif; font-size: 15px; letter-spacing: 0.5px; }}
    .value-label {{ fill: #1f1c18; font-weight: 600; }}
    .axis-label {{ fill: #6f6759; font-size: 14px; }}
    .missing-point {{ fill: #fffdf8; stroke: #6e1d12; stroke-width: 1.5; stroke-dasharray: 2 2; }}
    .missing-label {{ fill: #6e1d12; font-weight: 600; font-size: 14px; }}
    .chart-title {{ fill: #1f1c18; font-size: 19px; font-weight: 600; }}
    .line-ref {{ stroke: #b8aa95; stroke-width: 1; stroke-dasharray: 5 4; opacity: 0.85; }}
    .line-ref-label {{ fill: #8b806f; font-size: 12px; }}
  ]]></style>
  <text x="{pad_left}" y="28" class="chart-title">{escape(title)}</text>
  <line x1="{pad_left}" y1="{pad_top + plot_h}" x2="{width - pad_right}" y2="{pad_top + plot_h}" class="axis"/>
  <line x1="{pad_left}" y1="{pad_top}" x2="{pad_left}" y2="{pad_top + plot_h}" class="axis"/>
  {ref_nodes}
  {path_nodes}
  {point_nodes}
  {missing_nodes}
  {label_nodes}
</svg>
"""


def sparkline_svg(values: list[float | None]) -> str:
    width = 110
    height = 30
    pad = 4
    plot_w = width - 2 * pad
    plot_h = height - 2 * pad

    valid = [(idx, value) for idx, value in enumerate(values) if value is not None]
    if len(valid) < 2:
        return f"<svg viewBox='0 0 {width} {height}' class='sparkline' aria-hidden='true'></svg>"

    only_values = [value for _idx, value in valid]
    min_v = min(only_values)
    max_v = max(only_values)
    if min_v == max_v:
        min_v -= 1
        max_v += 1

    step = plot_w / max(1, len(values) - 1)
    coords: list[tuple[float, float]] = []
    for index, value in enumerate(values):
        if value is None:
            continue
        x = pad + index * step
        ratio = (value - min_v) / (max_v - min_v)
        y = pad + (1 - ratio) * plot_h
        coords.append((x, y))

    path = " ".join(f"{x:.1f},{y:.1f}" for x, y in coords)
    last_x, last_y = coords[-1]
    trend = "up" if only_values[-1] >= only_values[0] else "down"
    return (
        f"<svg viewBox='0 0 {width} {height}' class='sparkline sparkline-{trend}' aria-hidden='true'>"
        f"<polyline points='{path}' class='spark-line'/>"
        f"<circle cx='{last_x:.1f}' cy='{last_y:.1f}' r='2.4' class='spark-end'/>"
        f"</svg>"
    )


def line_chart_png(
    records: list[ScoreRecord],
    value: str,
    title: str,
    invert_rank: bool = False,
    exam_order: list[str] | None = None,
    reference_lines: list[ScoreLine] | None = None,
) -> bytes:
    scale = 2
    width = 760
    height = 360
    pad_left = 56
    pad_top = 52
    pad_bottom = 66

    labels = exam_order or [record.exam_name for record in records]
    record_by_exam = {record.exam_name: record for record in records}
    ordered_values: list[float | None] = []
    for label in labels:
        record = record_by_exam.get(label)
        raw_value = getattr(record, value) if record else None
        ordered_values.append(float(raw_value) if raw_value is not None else None)

    values = [raw for raw in ordered_values if raw is not None]
    if not values:
        return empty_chart_png(title, "暂无可绘制数据", scale)

    min_v = min(values)
    max_v = max(values)
    if min_v == max_v:
        min_v -= 1
        max_v += 1

    show_refs = bool(reference_lines) and value == "score" and not invert_rank
    visible_refs: list[ScoreLine] = []
    if show_refs:
        for line in reference_lines or []:
            if min_v - 8 <= line.score <= max_v + 8:
                visible_refs.append(line)
                min_v = min(min_v, line.score)
                max_v = max(max_v, line.score)

    y_buffer = (max_v - min_v) * 0.08 or 1
    min_v -= y_buffer
    max_v += y_buffer

    pad_right = 96 if visible_refs else 32
    plot_w = width - pad_left - pad_right
    plot_h = height - pad_top - pad_bottom
    step = plot_w / max(1, len(labels) - 1) if len(labels) > 1 else 0

    image = Image.new("RGB", (width * scale, height * scale), "#fffdf8")
    draw = ImageDraw.Draw(image)
    fonts = chart_fonts(scale)

    def sx(raw: float) -> int:
        return int(round(raw * scale))

    def sy(raw: float) -> int:
        return int(round(raw * scale))

    def y_for(raw: float) -> float:
        ratio = (raw - min_v) / (max_v - min_v)
        if invert_rank:
            ratio = 1 - ratio
        return pad_top + (1 - ratio) * plot_h

    axis_color = "#b8aa95"
    series_color = "#3e5d52"
    point_color = "#9b2c1f"
    text_color = "#6f6759"
    title_color = "#1f1c18"
    missing_color = "#6e1d12"

    draw.text((sx(pad_left), sy(18)), title, fill=title_color, font=fonts["title"])
    draw.line((sx(pad_left), sy(pad_top + plot_h), sx(width - pad_right), sy(pad_top + plot_h)), fill=axis_color, width=scale)
    draw.line((sx(pad_left), sy(pad_top), sx(pad_left), sy(pad_top + plot_h)), fill=axis_color, width=scale)

    for line in visible_refs:
        y = y_for(line.score)
        draw_dashed_line(draw, (sx(pad_left), sy(y)), (sx(width - pad_right), sy(y)), axis_color, scale)
        draw.text((sx(width - pad_right + 6), sy(y - 8)), f"{line.label}线 {line.score:g}", fill="#8b806f", font=fonts["small"])

    points: list[tuple[float, float, float] | None] = []
    for index, raw in enumerate(ordered_values):
        if raw is None:
            points.append(None)
            continue
        x = pad_left + index * step if len(labels) > 1 else pad_left + plot_w / 2
        points.append((x, y_for(raw), raw))

    current: list[tuple[float, float]] = []
    for point in points:
        if point is None:
            draw_polyline(draw, current, series_color, scale)
            current = []
            continue
        x, y, _raw = point
        current.append((x, y))
    draw_polyline(draw, current, series_color, scale)

    for point in points:
        if point is None:
            continue
        x, y, raw = point
        draw.ellipse((sx(x - 5), sy(y - 5), sx(x + 5), sy(y + 5)), fill=point_color, outline="#fffdf8", width=scale)
        draw_centered_text(draw, f"{raw:g}", x, y - 36, fonts["label"], title_color, scale)

    missing_y = pad_top + plot_h
    for index, raw in enumerate(ordered_values):
        x = pad_left + index * step if len(labels) > 1 else pad_left + plot_w / 2
        if raw is None:
            draw.ellipse((sx(x - 5), sy(missing_y - 5), sx(x + 5), sy(missing_y + 5)), fill="#fffdf8", outline=missing_color, width=scale)
            draw_centered_text(draw, "缺", x, missing_y - 28, fonts["small"], missing_color, scale)
        draw_centered_text(draw, labels[index], x, height - 38, fonts["axis"], text_color, scale)

    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def combined_trend_chart_svg(
    records: list[ScoreRecord],
    title: str,
    exam_order: list[str] | None = None,
    reference_lines: list[ScoreLine] | None = None,
) -> str:
    width = 1040
    height = 440
    pad_left = 70
    pad_right = 76
    pad_top = 86
    pad_bottom = 76

    labels = exam_order or [record.exam_name for record in records]
    record_by_exam = {record.exam_name: record for record in records}
    scores: list[float | None] = []
    ranks: list[float | None] = []
    for label in labels:
        record = record_by_exam.get(label)
        scores.append(float(record.score) if record and record.score is not None else None)
        ranks.append(float(record.rank) if record and record.rank is not None else None)

    score_values = [value for value in scores if value is not None]
    rank_values = [value for value in ranks if value is not None]
    if not score_values and not rank_values:
        return "<div class='empty'>暂无可绘制数据</div>"

    score_min, score_max = value_range(score_values)
    visible_refs: list[ScoreLine] = []
    if reference_lines and score_values:
        for line in reference_lines:
            if score_min - 8 <= line.score <= score_max + 8:
                visible_refs.append(line)
                score_min = min(score_min, line.score)
                score_max = max(score_max, line.score)
    score_min, score_max = buffered_range(score_min, score_max)
    rank_min, rank_max = buffered_range(*value_range(rank_values), integer_floor=True) if rank_values else (0.0, 1.0)

    step_estimate = (width - pad_left - pad_right) / max(1, len(labels) - 1) if len(labels) > 1 else 999
    rotate_labels = step_estimate < 90 and len(labels) > 3
    if rotate_labels:
        height = 560
        pad_left = 140
        pad_right = 120
        pad_bottom = 210

    plot_w = width - pad_left - pad_right
    plot_h = height - pad_top - pad_bottom
    point_inset = 34 if len(labels) > 1 else 0
    step = (plot_w - point_inset * 2) / max(1, len(labels) - 1) if len(labels) > 1 else 0

    def x_for(index: int) -> float:
        return pad_left + point_inset + index * step if len(labels) > 1 else pad_left + plot_w / 2

    def score_y(raw: float) -> float:
        ratio = (raw - score_min) / (score_max - score_min)
        return pad_top + (1 - ratio) * plot_h

    def rank_y(raw: float) -> float:
        ratio = (raw - rank_min) / (rank_max - rank_min)
        return pad_top + ratio * plot_h

    score_points = build_points(scores, x_for, score_y)
    rank_points = build_points(ranks, x_for, rank_y)
    ref_label_boxes = [
        svg_text_box(f"{line.label}线 {line.score:g}", pad_left + 8, score_y(line.score) - 10, "ref")
        for line in visible_refs
    ]
    ref_line_nodes = "\n".join(
        f"<line x1='{pad_left:.1f}' y1='{score_y(line.score):.1f}' x2='{width - pad_right:.1f}' "
        f"y2='{score_y(line.score):.1f}' class='line-ref'/>"
        for line in visible_refs
    )
    ref_label_nodes = "\n".join(
        svg_ref_label_node(line, pad_left + 8, score_y(line.score) - 10)
        for line in visible_refs
    )
    score_nodes = svg_series_nodes(score_points, "score-series", "score-point")
    rank_nodes = svg_series_nodes(rank_points, "rank-series", "rank-point")
    value_labels = layout_combined_series_labels(
        score_points,
        rank_points,
        svg_label_size,
        pad_left,
        width - pad_right,
        pad_top,
        pad_top + plot_h,
        width,
        occupied=ref_label_boxes,
        line_pad=18,
    )
    value_label_nodes = "\n".join(svg_value_label_node(label) for label in value_labels)
    missing_nodes = "\n".join(
        f"<text x='{x_for(index):.1f}' y='{pad_top + plot_h + 22:.1f}' text-anchor='middle' class='missing-label'>缺</text>"
        for index, (score, rank) in enumerate(zip(scores, ranks))
        if score is None and rank is None
    )
    axis_y = pad_top + plot_h
    if rotate_labels:
        axis_label_nodes = "\n".join(
            f"<text transform='translate({x_for(index):.1f},{axis_y + 10:.1f}) rotate(-40)' "
            f"text-anchor='end' class='axis-label'>{escape(label)}</text>"
            for index, label in enumerate(labels)
        )
    else:
        axis_label_nodes = "\n".join(
            f"<text x='{x_for(index):.1f}' y='{height - 28}' text-anchor='middle' class='axis-label'>{escape(label)}</text>"
            for index, label in enumerate(labels)
        )

    return f"""
<svg viewBox="0 0 {width} {height}" class="line-chart combined-line-chart" role="img" aria-label="{escape(title)}">
  <style><![CDATA[
    .combined-line-chart {{ background: #fffdf8; }}
    .axis {{ stroke: #b8aa95; stroke-width: 1; }}
    .score-series {{ stroke: #9b2c1f; stroke-width: 3; fill: none; }}
    .rank-series {{ stroke: #3e5d52; stroke-width: 3; fill: none; }}
    .score-point {{ fill: #9b2c1f; stroke: #fffdf8; stroke-width: 1.5; }}
    .rank-point {{ fill: #3e5d52; stroke: #fffdf8; stroke-width: 1.5; }}
    text {{ fill: #6f6759; font-family: "Microsoft YaHei", "SimSun", sans-serif; font-size: 14px; letter-spacing: 0.5px; }}
    .chart-title {{ fill: #1f1c18; font-size: 20px; font-weight: 600; }}
    .axis-label {{ fill: #6f6759; font-size: 14px; }}
    .axis-title {{ fill: #1f1c18; font-size: 14px; font-weight: 600; }}
    .score-label {{ fill: #9b2c1f; font-weight: 600; font-size: 15px; }}
    .rank-label {{ fill: #3e5d52; font-weight: 600; font-size: 13px; }}
    .value-label-bg {{ fill: #fffdf8; opacity: 0.95; }}
    .score-label-bg {{ fill: #fffdf8; stroke: #9b2c1f; stroke-width: 0.8; opacity: 0.95; }}
    .rank-label-bg {{ fill: #fffdf8; stroke: #3e5d52; stroke-width: 0.8; opacity: 0.95; }}
    .legend-text {{ fill: #1f1c18; font-size: 13px; font-weight: 600; }}
    .missing-label {{ fill: #6e1d12; font-weight: 600; }}
    .line-ref {{ stroke: #b8aa95; stroke-width: 1; stroke-dasharray: 5 4; opacity: 0.75; }}
    .line-ref-label {{ fill: #8b806f; font-size: 12px; }}
  ]]></style>
  <text x="{pad_left}" y="32" class="chart-title">{escape(title)}</text>
  <line x1="{pad_left}" y1="{pad_top + plot_h}" x2="{width - pad_right}" y2="{pad_top + plot_h}" class="axis"/>
  <line x1="{pad_left}" y1="{pad_top}" x2="{pad_left}" y2="{pad_top + plot_h}" class="axis"/>
  <line x1="{width - pad_right}" y1="{pad_top}" x2="{width - pad_right}" y2="{pad_top + plot_h}" class="axis"/>
  <text x="{pad_left}" y="{pad_top - 18}" class="axis-title">成绩</text>
  <text x="{width - pad_right}" y="{pad_top - 18}" text-anchor="end" class="axis-title">位次</text>
  <line x1="{width - pad_right - 196}" y1="28" x2="{width - pad_right - 166}" y2="28" class="score-series score-legend-line"/>
  <text x="{width - pad_right - 156}" y="33" class="legend-text">成绩</text>
  <line x1="{width - pad_right - 94}" y1="28" x2="{width - pad_right - 64}" y2="28" class="rank-series rank-legend-line"/>
  <text x="{width - pad_right - 54}" y="33" class="legend-text">位次</text>
  {ref_line_nodes}
  {score_nodes}
  {rank_nodes}
  {ref_label_nodes}
  {value_label_nodes}
  {missing_nodes}
  {axis_label_nodes}
</svg>
"""


def combined_trend_chart_png(
    records: list[ScoreRecord],
    title: str,
    exam_order: list[str] | None = None,
    reference_lines: list[ScoreLine] | None = None,
) -> bytes:
    scale = 2
    width = 1040
    height = 440
    pad_left = 70
    pad_right = 76
    pad_top = 86
    pad_bottom = 76

    labels = exam_order or [record.exam_name for record in records]
    record_by_exam = {record.exam_name: record for record in records}
    scores: list[float | None] = []
    ranks: list[float | None] = []
    for label in labels:
        record = record_by_exam.get(label)
        scores.append(float(record.score) if record and record.score is not None else None)
        ranks.append(float(record.rank) if record and record.rank is not None else None)

    score_values = [value for value in scores if value is not None]
    rank_values = [value for value in ranks if value is not None]
    if not score_values and not rank_values:
        return empty_chart_png(title, "暂无可绘制数据", scale)

    score_min, score_max = value_range(score_values)
    visible_refs: list[ScoreLine] = []
    if reference_lines and score_values:
        for line in reference_lines:
            if score_min - 8 <= line.score <= score_max + 8:
                visible_refs.append(line)
                score_min = min(score_min, line.score)
                score_max = max(score_max, line.score)
    score_min, score_max = buffered_range(score_min, score_max)
    rank_min, rank_max = buffered_range(*value_range(rank_values), integer_floor=True) if rank_values else (0.0, 1.0)

    step_estimate = (width - pad_left - pad_right) / max(1, len(labels) - 1) if len(labels) > 1 else 999
    rotate_labels = step_estimate < 90 and len(labels) > 3
    if rotate_labels:
        height = 560
        pad_left = 140
        pad_right = 120
        pad_bottom = 210

    plot_w = width - pad_left - pad_right
    plot_h = height - pad_top - pad_bottom
    point_inset = 34 if len(labels) > 1 else 0
    step = (plot_w - point_inset * 2) / max(1, len(labels) - 1) if len(labels) > 1 else 0

    image = Image.new("RGB", (width * scale, height * scale), "#fffdf8")
    draw = ImageDraw.Draw(image)
    fonts = chart_fonts(scale)

    def sx(raw: float) -> int:
        return int(round(raw * scale))

    def sy(raw: float) -> int:
        return int(round(raw * scale))

    def x_for(index: int) -> float:
        return pad_left + point_inset + index * step if len(labels) > 1 else pad_left + plot_w / 2

    def score_y(raw: float) -> float:
        ratio = (raw - score_min) / (score_max - score_min)
        return pad_top + (1 - ratio) * plot_h

    def rank_y(raw: float) -> float:
        ratio = (raw - rank_min) / (rank_max - rank_min)
        return pad_top + ratio * plot_h

    axis_color = "#b8aa95"
    score_color = "#9b2c1f"
    rank_color = "#3e5d52"
    text_color = "#6f6759"
    title_color = "#1f1c18"

    draw.text((sx(pad_left), sy(18)), title, fill=title_color, font=fonts["title"])
    draw.line((sx(pad_left), sy(pad_top + plot_h), sx(width - pad_right), sy(pad_top + plot_h)), fill=axis_color, width=scale)
    draw.line((sx(pad_left), sy(pad_top), sx(pad_left), sy(pad_top + plot_h)), fill=axis_color, width=scale)
    draw.line((sx(width - pad_right), sy(pad_top), sx(width - pad_right), sy(pad_top + plot_h)), fill=axis_color, width=scale)
    draw.text((sx(pad_left), sy(pad_top - 18)), "成绩", fill=title_color, font=fonts["axis"])
    draw.text((sx(width - pad_right - 34), sy(pad_top - 18)), "位次", fill=title_color, font=fonts["axis"])

    draw.line((sx(width - pad_right - 196), sy(28), sx(width - pad_right - 166), sy(28)), fill=score_color, width=3 * scale)
    draw.text((sx(width - pad_right - 156), sy(18)), "成绩", fill=title_color, font=fonts["small"])
    draw.line((sx(width - pad_right - 94), sy(28), sx(width - pad_right - 64), sy(28)), fill=rank_color, width=3 * scale)
    draw.text((sx(width - pad_right - 54), sy(18)), "位次", fill=title_color, font=fonts["small"])

    for line in visible_refs:
        y = score_y(line.score)
        draw_dashed_line(draw, (sx(pad_left), sy(y)), (sx(width - pad_right), sy(y)), axis_color, scale)

    score_points = build_points(scores, x_for, score_y)
    rank_points = build_points(ranks, x_for, rank_y)
    draw_segmented_png_line(draw, score_points, score_color, scale)
    draw_segmented_png_line(draw, rank_points, rank_color, scale)

    for point in score_points:
        if point is None:
            continue
        x, y, raw = point
        draw.ellipse((sx(x - 5), sy(y - 5), sx(x + 5), sy(y + 5)), fill=score_color, outline="#fffdf8", width=scale)
    for point in rank_points:
        if point is None:
            continue
        x, y, raw = point
        draw.ellipse((sx(x - 5), sy(y - 5), sx(x + 5), sy(y + 5)), fill=rank_color, outline="#fffdf8", width=scale)

    for line in visible_refs:
        y = score_y(line.score)
        draw_left_label(draw, f"{line.label}线 {line.score:g}", pad_left + 8, y - 10, fonts["small"], "#8b806f", scale)

    draw_png_series_labels(
        draw,
        score_points,
        rank_points,
        fonts,
        scale,
        width,
        pad_top,
        pad_left,
        width - pad_right,
        pad_top + plot_h,
        score_color,
        rank_color,
        occupied=[
            left_text_box(draw, f"{line.label}线 {line.score:g}", pad_left + 8, score_y(line.score) - 10, fonts["small"], scale)
            for line in visible_refs
        ],
    )

    axis_y = pad_top + plot_h
    for index, (score, rank) in enumerate(zip(scores, ranks)):
        x = x_for(index)
        if score is None and rank is None:
            draw_centered_text(draw, "缺", x, pad_top + plot_h + 22, fonts["small"], "#6e1d12", scale)
        if rotate_labels:
            draw_rotated_centered_text(image, labels[index], x, axis_y + 36, fonts["axis"], text_color, scale, angle=-40)
        else:
            draw_centered_text(draw, labels[index], x, height - 36, fonts["axis"], text_color, scale)

    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def empty_chart_png(title: str, message: str, scale: int) -> bytes:
    width = 760
    height = 360
    image = Image.new("RGB", (width * scale, height * scale), "#fffdf8")
    draw = ImageDraw.Draw(image)
    fonts = chart_fonts(scale)
    draw.text((56 * scale, 18 * scale), title, fill="#1f1c18", font=fonts["title"])
    draw.text((56 * scale, 92 * scale), message, fill="#6f6759", font=fonts["label"])
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def chart_fonts(scale: int) -> dict[str, ImageFont.FreeTypeFont | ImageFont.ImageFont]:
    return {
        "title": load_chart_font(19 * scale),
        "label": load_chart_font(15 * scale),
        "axis": load_chart_font(14 * scale),
        "small": load_chart_font(12 * scale),
    }


def load_chart_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        Path("C:/Windows/Fonts/msyh.ttc"),
        Path("C:/Windows/Fonts/simhei.ttf"),
        Path("C:/Windows/Fonts/simsun.ttc"),
    ]
    for path in candidates:
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def value_range(values: list[float]) -> tuple[float, float]:
    if not values:
        return 0.0, 1.0
    min_v = min(values)
    max_v = max(values)
    if min_v == max_v:
        min_v -= 1
        max_v += 1
    return min_v, max_v


def buffered_range(min_v: float, max_v: float, integer_floor: bool = False) -> tuple[float, float]:
    if min_v == max_v:
        min_v -= 1
        max_v += 1
    buffer = (max_v - min_v) * 0.08 or 1
    min_v -= buffer
    max_v += buffer
    if integer_floor:
        min_v = max(1, min_v)
    return min_v, max_v


def build_points(
    values: list[float | None],
    x_for,
    y_for,
) -> list[tuple[float, float, float] | None]:
    points: list[tuple[float, float, float] | None] = []
    for index, raw in enumerate(values):
        if raw is None:
            points.append(None)
        else:
            points.append((x_for(index), y_for(raw), raw))
    return points


def svg_series_nodes(
    points: list[tuple[float, float, float] | None],
    line_class: str,
    point_class: str,
) -> str:
    segments: list[list[tuple[float, float, float]]] = []
    current: list[tuple[float, float, float]] = []
    for point in points:
        if point is None:
            if current:
                segments.append(current)
                current = []
            continue
        current.append(point)
    if current:
        segments.append(current)

    lines = "\n".join(
        f"<polyline points=\"{' '.join(f'{x:.1f},{y:.1f}' for x, y, _ in segment)}\" fill=\"none\" class=\"{line_class}\"/>"
        for segment in segments
    )
    point_nodes = "\n".join(
        f"<circle cx='{x:.1f}' cy='{y:.1f}' r='5' class='{point_class}'/>"
        for point in points
        if point is not None
        for x, y, _raw in [point]
    )
    return "\n".join(part for part in (lines, point_nodes) if part)


def svg_value_label_node(label: PositionedLabel) -> str:
    left, top, right, bottom = label.box
    class_name = "score-label" if label.series == "score" else "rank-label"
    bg_class = "score-label-bg" if label.series == "score" else "rank-label-bg"
    return (
        f"<rect x='{left - 4:.1f}' y='{top - 3:.1f}' width='{right - left + 8:.1f}' "
        f"height='{bottom - top + 6:.1f}' rx='3' class='{bg_class}'/>"
        f"<text x='{label.x:.1f}' y='{label.y:.1f}' text-anchor='middle' "
        f"dominant-baseline='middle' class='{class_name}'>{escape(label.text)}</text>"
    )


def svg_ref_label_node(line: ScoreLine, x: float, y: float) -> str:
    text = f"{line.label}线 {line.score:g}"
    box = svg_text_box(text, x, y, "ref")
    left, top, right, bottom = box
    return (
        f"<rect x='{left - 4:.1f}' y='{top - 3:.1f}' width='{right - left + 8:.1f}' "
        f"height='{bottom - top + 6:.1f}' rx='3' class='value-label-bg'/>"
        f"<text x='{x:.1f}' y='{y:.1f}' class='line-ref-label'>{escape(text)}</text>"
    )


def svg_label_size(text: str, series: str) -> tuple[float, float]:
    if series == "ref":
        size = 12
    else:
        size = 15 if series == "score" else 13
    width = sum(size if ord(char) > 127 else size * 0.58 for char in text)
    return (width + 10, size + 8)


def svg_text_box(text: str, x: float, y: float, series: str) -> tuple[float, float, float, float]:
    width, height = svg_label_size(text, series)
    return (x, y - height, x + width, y)


def draw_polyline(draw: ImageDraw.ImageDraw, points: list[tuple[float, float]], color: str, scale: int) -> None:
    if len(points) < 2:
        return
    scaled = [(int(round(x * scale)), int(round(y * scale))) for x, y in points]
    draw.line(scaled, fill=color, width=3 * scale, joint="curve")


def draw_segmented_png_line(
    draw: ImageDraw.ImageDraw,
    points: list[tuple[float, float, float] | None],
    color: str,
    scale: int,
) -> None:
    current: list[tuple[float, float]] = []
    for point in points:
        if point is None:
            draw_polyline(draw, current, color, scale)
            current = []
            continue
        x, y, _raw = point
        current.append((x, y))
    draw_polyline(draw, current, color, scale)


def draw_dashed_line(
    draw: ImageDraw.ImageDraw,
    start: tuple[int, int],
    end: tuple[int, int],
    color: str,
    scale: int,
) -> None:
    x1, y1 = start
    x2, y2 = end
    dash = 8 * scale
    gap = 6 * scale
    x = x1
    while x < x2:
        draw.line((x, y1, min(x + dash, x2), y2), fill=color, width=scale)
        x += dash + gap


def draw_centered_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    x: float,
    y: float,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    color: str,
    scale: int,
) -> tuple[float, float, float, float]:
    bbox = draw.textbbox((0, 0), text, font=font)
    width = bbox[2] - bbox[0]
    height = bbox[3] - bbox[1]
    draw.text((int(round(x * scale - width / 2)), int(round(y * scale - height / 2))), text, fill=color, font=font)
    return centered_text_box(draw, text, x, y, font, scale)


def draw_centered_label(
    draw: ImageDraw.ImageDraw,
    text: str,
    x: float,
    y: float,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    color: str,
    scale: int,
) -> tuple[float, float, float, float]:
    box = centered_text_box(draw, text, x, y, font, scale)
    pad_x = 4
    pad_y = 3
    draw.rounded_rectangle(
        (
            int(round((box[0] - pad_x) * scale)),
            int(round((box[1] - pad_y) * scale)),
            int(round((box[2] + pad_x) * scale)),
            int(round((box[3] + pad_y) * scale)),
        ),
        radius=3 * scale,
        fill="#fffdf8",
        outline=color,
        width=max(1, scale),
    )
    return draw_centered_text(draw, text, x, y, font, color, scale)


def draw_left_label(
    draw: ImageDraw.ImageDraw,
    text: str,
    x: float,
    y: float,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    color: str,
    scale: int,
) -> tuple[float, float, float, float]:
    box = left_text_box(draw, text, x, y, font, scale)
    pad_x = 4
    pad_y = 3
    draw.rounded_rectangle(
        (
            int(round((box[0] - pad_x) * scale)),
            int(round((box[1] - pad_y) * scale)),
            int(round((box[2] + pad_x) * scale)),
            int(round((box[3] + pad_y) * scale)),
        ),
        radius=3 * scale,
        fill="#fffdf8",
    )
    draw.text((int(round(x * scale)), int(round((y - (box[3] - box[1]) / 2) * scale))), text, fill=color, font=font)
    return box


def draw_png_series_labels(
    draw: ImageDraw.ImageDraw,
    score_points: list[tuple[float, float, float] | None],
    rank_points: list[tuple[float, float, float] | None],
    fonts: dict[str, ImageFont.FreeTypeFont | ImageFont.ImageFont],
    scale: int,
    width: int,
    plot_top: float,
    plot_left: float,
    plot_right: float,
    plot_bottom: float,
    score_color: str,
    rank_color: str,
    occupied: list[tuple[float, float, float, float]] | None = None,
) -> None:
    labels = layout_combined_series_labels(
        score_points,
        rank_points,
        lambda text, series: text_size_units(draw, text, fonts["label" if series == "score" else "small"], scale),
        plot_left,
        plot_right,
        plot_top,
        plot_bottom,
        width,
        occupied=occupied,
        line_pad=16,
    )
    for label in labels:
        font = fonts["label"] if label.series == "score" else fonts["small"]
        color = score_color if label.series == "score" else rank_color
        draw_centered_label(draw, label.text, label.x, label.y, font, color, scale)


def layout_combined_series_labels(
    score_points: list[tuple[float, float, float] | None],
    rank_points: list[tuple[float, float, float] | None],
    measure_text,
    plot_left: float,
    plot_right: float,
    plot_top: float,
    plot_bottom: float,
    width: int,
    occupied: list[tuple[float, float, float, float]] | None = None,
    line_pad: float = 7,
) -> list[PositionedLabel]:
    occupied_boxes = list(occupied or [])
    score_segments = point_line_segments(score_points)
    rank_segments = point_line_segments(rank_points)
    for point in [*score_points, *rank_points]:
        if point is None:
            continue
        x, y, _raw = point
        occupied_boxes.append((x - 18, y - 18, x + 18, y + 18))

    labels: list[PositionedLabel] = []
    count = max(len(score_points), len(rank_points))
    for index in range(count):
        score_point = score_points[index] if index < len(score_points) else None
        rank_point = rank_points[index] if index < len(rank_points) else None

        if score_point is not None:
            x, y, raw = score_point
            text = f"{raw:g}"
            side = side_label_offset(x, width, plot_right)
            if rank_point is not None and rank_point[1] < y:
                candidates = [
                    (x, y + 30),
                    (x, y + 46),
                    (x + side, y + 24),
                    (x - side, y + 24),
                    (x + side, y + 42),
                    (x - side, y + 42),
                    (x + side * 1.6, y),
                    (x - side * 1.6, y),
                    (x, y - 30),
                ]
            else:
                candidates = [
                    (x, y - 26),
                    (x, y - 42),
                    (x, y - 58),
                    (x + side, y - 16),
                    (x - side, y - 16),
                    (x + side, y - 34),
                    (x - side, y - 34),
                    (x + side, y - 52),
                    (x - side, y - 52),
                    (x, y + 30),
                    (x + side * 1.6, y),
                    (x - side * 1.6, y),
                ]
            label = place_series_label(
                "score",
                text,
                candidates,
                measure_text,
                occupied_boxes,
                rank_segments,
                line_pad,
                plot_left,
                plot_right,
                plot_top,
                plot_bottom,
            )
            labels.append(label)
            occupied_boxes.append(label.box)

        if rank_point is not None:
            x, y, raw = rank_point
            text = f"第{raw:g}名"
            side = side_label_offset(x, width, plot_right)
            if score_point is not None and score_point[1] > y:
                candidates = [
                    (x, y - 28),
                    (x, y - 44),
                    (x + side, y - 18),
                    (x - side, y - 18),
                    (x + side, y - 36),
                    (x - side, y - 36),
                    (x + side * 1.6, y),
                    (x - side * 1.6, y),
                    (x, y + 28),
                ]
            else:
                candidates = [
                    (x, y + 24),
                    (x, y + 42),
                    (x, y + 58),
                    (x + side, y + 16),
                    (x - side, y + 16),
                    (x + side, y + 34),
                    (x - side, y + 34),
                    (x + side, y + 52),
                    (x - side, y + 52),
                    (x, y - 28),
                    (x + side * 1.6, y),
                    (x - side * 1.6, y),
                ]
            label = place_series_label(
                "rank",
                text,
                candidates,
                measure_text,
                occupied_boxes,
                score_segments,
                line_pad,
                plot_left,
                plot_right,
                plot_top,
                plot_bottom,
            )
            labels.append(label)
            occupied_boxes.append(label.box)
    return labels


def side_label_offset(x: float, width: int, plot_right: float) -> float:
    if x > min(width - 88, plot_right - 42):
        return -46
    return 46


def place_series_label(
    series: str,
    text: str,
    candidates: list[tuple[float, float]],
    measure_text,
    occupied: list[tuple[float, float, float, float]],
    line_segments: list[tuple[float, float, float, float]],
    line_pad: float,
    min_x: float,
    max_x: float,
    min_y: float,
    max_y: float,
) -> PositionedLabel:
    fallback: tuple[int, PositionedLabel] | None = None
    for candidate_index, (raw_x, raw_y) in enumerate(candidates):
        label_w, label_h = measure_text(text, series)
        x, y = clamp_label_center(raw_x, raw_y, label_w, label_h, min_x, max_x, min_y, max_y)
        box = (x - label_w / 2, y - label_h / 2, x + label_w / 2, y + label_h / 2)
        label = PositionedLabel(series=series, text=text, x=x, y=y, box=box)
        overlap_count = sum(1 for other in occupied if text_boxes_overlap(box, other, pad=2))
        line_penalty = box_line_penalty(box, line_segments, target_clearance=line_pad)
        score = overlap_count * 1000 + line_penalty * 20 + candidate_index
        if fallback is None or score < fallback[0]:
            fallback = (score, label)
        if overlap_count == 0 and line_penalty == 0:
            return label
    return fallback[1] if fallback is not None else PositionedLabel(series, text, min_x, min_y, (min_x, min_y, min_x, min_y))


def clamp_label_center(
    x: float,
    y: float,
    width: float,
    height: float,
    min_x: float,
    max_x: float,
    min_y: float,
    max_y: float,
) -> tuple[float, float]:
    margin = 6
    half_w = width / 2
    half_h = height / 2
    low_x = min_x + half_w + margin
    high_x = max_x - half_w - margin
    low_y = min_y + half_h + margin
    high_y = max_y - half_h - margin
    if low_x > high_x:
        x = (min_x + max_x) / 2
    else:
        x = max(low_x, min(x, high_x))
    if low_y > high_y:
        y = (min_y + max_y) / 2
    else:
        y = max(low_y, min(y, high_y))
    return x, y


def centered_text_box(
    draw: ImageDraw.ImageDraw,
    text: str,
    x: float,
    y: float,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    scale: int,
) -> tuple[float, float, float, float]:
    width, height = text_size_units(draw, text, font, scale)
    return (x - width / 2, y - height / 2, x + width / 2, y + height / 2)


def left_text_box(
    draw: ImageDraw.ImageDraw,
    text: str,
    x: float,
    y: float,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    scale: int,
) -> tuple[float, float, float, float]:
    width, height = text_size_units(draw, text, font, scale)
    return (x, y - height / 2, x + width, y + height / 2)


def text_size_units(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    scale: int,
) -> tuple[float, float]:
    bbox = draw.textbbox((0, 0), text, font=font)
    return ((bbox[2] - bbox[0]) / scale, (bbox[3] - bbox[1]) / scale)


def text_boxes_overlap(
    first: tuple[float, float, float, float],
    second: tuple[float, float, float, float],
    pad: float = 0,
) -> bool:
    return not (
        first[2] + pad < second[0]
        or second[2] + pad < first[0]
        or first[3] + pad < second[1]
        or second[3] + pad < first[1]
    )


def point_line_segments(points: list[tuple[float, float, float] | None]) -> list[tuple[float, float, float, float]]:
    segments: list[tuple[float, float, float, float]] = []
    previous: tuple[float, float, float] | None = None
    for point in points:
        if point is None:
            previous = None
            continue
        if previous is not None:
            x1, y1, _raw1 = previous
            x2, y2, _raw2 = point
            segments.append((x1, y1, x2, y2))
        previous = point
    return segments


def box_too_close_to_segments(
    box: tuple[float, float, float, float],
    segments: list[tuple[float, float, float, float]],
    pad: float,
) -> bool:
    left, top, right, bottom = box
    expanded = (left - pad, top - pad, right + pad, bottom + pad)
    return any(segment_intersects_box(segment, expanded) for segment in segments)


def box_line_penalty(
    box: tuple[float, float, float, float],
    segments: list[tuple[float, float, float, float]],
    target_clearance: float,
) -> float:
    penalty = 0.0
    for segment in segments:
        distance = segment_box_distance(segment, box)
        if distance < target_clearance:
            penalty += target_clearance - distance
    return penalty


def segment_box_distance(
    segment: tuple[float, float, float, float],
    box: tuple[float, float, float, float],
) -> float:
    if segment_intersects_box(segment, box):
        return 0.0
    x1, y1, x2, y2 = segment
    left, top, right, bottom = box
    corners = [(left, top), (right, top), (right, bottom), (left, bottom)]
    endpoint_distances = [point_box_distance(x1, y1, box), point_box_distance(x2, y2, box)]
    corner_distances = [point_segment_distance(corner[0], corner[1], x1, y1, x2, y2) for corner in corners]
    return min(endpoint_distances + corner_distances)


def point_box_distance(x: float, y: float, box: tuple[float, float, float, float]) -> float:
    left, top, right, bottom = box
    dx = max(left - x, 0, x - right)
    dy = max(top - y, 0, y - bottom)
    return math.hypot(dx, dy)


def point_segment_distance(px: float, py: float, x1: float, y1: float, x2: float, y2: float) -> float:
    dx = x2 - x1
    dy = y2 - y1
    if dx == 0 and dy == 0:
        return math.hypot(px - x1, py - y1)
    t = ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    nearest_x = x1 + t * dx
    nearest_y = y1 + t * dy
    return math.hypot(px - nearest_x, py - nearest_y)


def segment_intersects_box(
    segment: tuple[float, float, float, float],
    box: tuple[float, float, float, float],
) -> bool:
    x1, y1, x2, y2 = segment
    left, top, right, bottom = box
    if point_in_box(x1, y1, box) or point_in_box(x2, y2, box):
        return True
    return (
        segments_intersect((x1, y1), (x2, y2), (left, top), (right, top))
        or segments_intersect((x1, y1), (x2, y2), (right, top), (right, bottom))
        or segments_intersect((x1, y1), (x2, y2), (right, bottom), (left, bottom))
        or segments_intersect((x1, y1), (x2, y2), (left, bottom), (left, top))
    )


def point_in_box(x: float, y: float, box: tuple[float, float, float, float]) -> bool:
    left, top, right, bottom = box
    return left <= x <= right and top <= y <= bottom


def segments_intersect(
    a1: tuple[float, float],
    a2: tuple[float, float],
    b1: tuple[float, float],
    b2: tuple[float, float],
) -> bool:
    def orientation(p: tuple[float, float], q: tuple[float, float], r: tuple[float, float]) -> float:
        return (q[1] - p[1]) * (r[0] - q[0]) - (q[0] - p[0]) * (r[1] - q[1])

    o1 = orientation(a1, a2, b1)
    o2 = orientation(a1, a2, b2)
    o3 = orientation(b1, b2, a1)
    o4 = orientation(b1, b2, a2)
    return (o1 > 0) != (o2 > 0) and (o3 > 0) != (o4 > 0)


def draw_rotated_centered_text(
    image: Image.Image,
    text: str,
    x: float,
    y: float,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    color: str,
    scale: int,
    angle: float = -40,
) -> None:
    draw = ImageDraw.Draw(image)
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    pad = 8 * scale
    label = Image.new("RGBA", (text_w + pad * 2, text_h + pad * 2), (255, 255, 255, 0))
    label_draw = ImageDraw.Draw(label)
    label_draw.text((pad - bbox[0], pad - bbox[1]), text, fill=color, font=font)
    rotated = label.rotate(angle, expand=True, resample=Image.Resampling.BICUBIC)
    paste_x = int(round(x * scale - rotated.width + 8 * scale))
    paste_y = int(round(y * scale - 8 * scale))
    image.paste(rotated, (paste_x, paste_y), rotated)
