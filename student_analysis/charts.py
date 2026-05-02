from __future__ import annotations

from io import BytesIO
from html import escape
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .models import ScoreLine, ScoreRecord


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
    step = plot_w / max(1, len(labels) - 1) if len(labels) > 1 else 0

    def x_for(index: int) -> float:
        return pad_left + index * step if len(labels) > 1 else pad_left + plot_w / 2

    def score_y(raw: float) -> float:
        ratio = (raw - score_min) / (score_max - score_min)
        return pad_top + (1 - ratio) * plot_h

    def rank_y(raw: float) -> float:
        ratio = (raw - rank_min) / (rank_max - rank_min)
        return pad_top + ratio * plot_h

    score_points = build_points(scores, x_for, score_y)
    rank_points = build_points(ranks, x_for, rank_y)
    ref_nodes = "\n".join(
        f"<line x1='{pad_left:.1f}' y1='{score_y(line.score):.1f}' x2='{width - pad_right:.1f}' y2='{score_y(line.score):.1f}' class='line-ref'/>"
        f"<text x='{pad_left + 8:.1f}' y='{score_y(line.score) - 6:.1f}' class='line-ref-label'>{escape(line.label)}线 {line.score:g}</text>"
        for line in visible_refs
    )
    score_nodes = svg_series_nodes(score_points, "score-series", "score-point", "score-label", "{:g}", -22)
    rank_nodes = svg_series_nodes(rank_points, "rank-series", "rank-point", "rank-label", "第{:g}名", 28)
    missing_nodes = "\n".join(
        f"<text x='{x_for(index):.1f}' y='{pad_top + plot_h + 22:.1f}' text-anchor='middle' class='missing-label'>缺</text>"
        for index, (score, rank) in enumerate(zip(scores, ranks))
        if score is None and rank is None
    )
    axis_y = pad_top + plot_h
    if rotate_labels:
        label_nodes = "\n".join(
            f"<text transform='translate({x_for(index):.1f},{axis_y + 10:.1f}) rotate(-40)' "
            f"text-anchor='end' class='axis-label'>{escape(label)}</text>"
            for index, label in enumerate(labels)
        )
    else:
        label_nodes = "\n".join(
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
  {ref_nodes}
  {score_nodes}
  {rank_nodes}
  {missing_nodes}
  {label_nodes}
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
    step = plot_w / max(1, len(labels) - 1) if len(labels) > 1 else 0

    image = Image.new("RGB", (width * scale, height * scale), "#fffdf8")
    draw = ImageDraw.Draw(image)
    fonts = chart_fonts(scale)

    def sx(raw: float) -> int:
        return int(round(raw * scale))

    def sy(raw: float) -> int:
        return int(round(raw * scale))

    def x_for(index: int) -> float:
        return pad_left + index * step if len(labels) > 1 else pad_left + plot_w / 2

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
        draw.text((sx(pad_left + 8), sy(y - 18)), f"{line.label}线 {line.score:g}", fill="#8b806f", font=fonts["small"])

    score_points = build_points(scores, x_for, score_y)
    rank_points = build_points(ranks, x_for, rank_y)
    draw_segmented_png_line(draw, score_points, score_color, scale)
    draw_segmented_png_line(draw, rank_points, rank_color, scale)

    for point in score_points:
        if point is None:
            continue
        x, y, raw = point
        draw.ellipse((sx(x - 5), sy(y - 5), sx(x + 5), sy(y + 5)), fill=score_color, outline="#fffdf8", width=scale)
        draw_centered_text(draw, f"{raw:g}", x, y - 34, fonts["label"], score_color, scale)
    for point in rank_points:
        if point is None:
            continue
        x, y, raw = point
        draw.ellipse((sx(x - 5), sy(y - 5), sx(x + 5), sy(y + 5)), fill=rank_color, outline="#fffdf8", width=scale)
        draw_centered_text(draw, f"第{raw:g}名", x, y + 32, fonts["small"], rank_color, scale)

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
    label_class: str,
    label_format: str,
    label_offset: float,
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
        f"<text x='{x:.1f}' y='{y + label_offset:.1f}' text-anchor='middle' class='{label_class}'>{label_format.format(raw)}</text>"
        for point in points
        if point is not None
        for x, y, raw in [point]
    )
    return "\n".join(part for part in (lines, point_nodes) if part)


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
) -> None:
    bbox = draw.textbbox((0, 0), text, font=font)
    width = bbox[2] - bbox[0]
    height = bbox[3] - bbox[1]
    draw.text((int(round(x * scale - width / 2)), int(round(y * scale - height / 2))), text, fill=color, font=font)


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
