from __future__ import annotations

from io import BytesIO
from pathlib import Path
import sys

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import student_analysis.charts as charts
from student_analysis.charts import combined_trend_chart_png, combined_trend_chart_svg
from student_analysis.models import ScoreRecord


def sample_records() -> list[ScoreRecord]:
    return [
        ScoreRecord("7班", "张三", "七上期中", 72.5, 18),
        ScoreRecord("7班", "张三", "七上期末", 81, 8),
        ScoreRecord("7班", "张三", "七下期中", 78, 11),
    ]


def test_combined_trend_svg_contains_score_and_rank_series() -> None:
    svg = combined_trend_chart_svg(
        sample_records(),
        "张三 成绩与位次趋势",
        exam_order=["七上期中", "七上期末", "七下期中"],
    )

    assert "成绩与位次趋势" in svg
    assert "score-series" in svg
    assert "rank-series" in svg
    assert "成绩" in svg
    assert "位次" in svg


def test_combined_trend_png_is_a_large_png() -> None:
    png = combined_trend_chart_png(
        sample_records(),
        "张三 成绩与位次趋势",
        exam_order=["七上期中", "七上期末", "七下期中"],
    )

    image = Image.open(BytesIO(png))
    assert image.format == "PNG"
    assert image.width >= 1800
    assert image.height >= 800


def test_combined_trend_png_offsets_overlapping_value_labels() -> None:
    labels = charts.layout_combined_series_labels(
        score_points=[(95, 360, 62.5), (520, 210, 68), (946, 150, 71)],
        rank_points=[(95, 380, 23), (520, 170, 16), (946, 210, 17)],
        measure_text=lambda text, series: (len(text) * (9 if series == "score" else 11), 16),
        plot_left=70,
        plot_right=964,
        plot_top=86,
        plot_bottom=364,
        width=1040,
    )

    for index, first in enumerate(labels):
        for second in labels[index + 1 :]:
            assert not charts.text_boxes_overlap(first.box, second.box, pad=2)

    middle_score = next(label for label in labels if label.text == "68")
    middle_rank = next(label for label in labels if label.text == "第16名")
    assert middle_score.series == "score"
    assert middle_rank.series == "rank"
    assert middle_score.y > 210
    assert not charts.text_boxes_overlap(middle_score.box, middle_rank.box, pad=2)


def test_combined_trend_labels_avoid_reference_labels_near_first_point() -> None:
    labels = charts.layout_combined_series_labels(
        score_points=[(104, 342, 60), (520, 360, 56.5), (936, 260, 58)],
        rank_points=[(104, 86, 26), (520, 250, 28), (936, 360, 29)],
        measure_text=lambda text, series: (len(text) * (9 if series == "score" else 11), 16),
        plot_left=70,
        plot_right=964,
        plot_top=86,
        plot_bottom=364,
        width=1040,
        occupied=[(78, 78, 134, 98), (78, 326, 134, 346)],
    )

    reference_boxes = [(78, 78, 134, 98), (78, 326, 134, 346)]
    for label in labels:
        for reference_box in reference_boxes:
            assert not charts.text_boxes_overlap(label.box, reference_box, pad=2)


def test_combined_trend_labels_keep_clear_of_lines() -> None:
    score_points = [(104, 188, 80), (520, 230, 77), (936, 105, 89)]
    rank_points = [(104, 86, 1), (520, 360, 8), (936, 86, 1)]
    labels = charts.layout_combined_series_labels(
        score_points=score_points,
        rank_points=rank_points,
        measure_text=lambda text, series: (len(text) * (9 if series == "score" else 11), 16),
        plot_left=70,
        plot_right=964,
        plot_top=86,
        plot_bottom=364,
        width=1040,
    )
    score_segments = charts.point_line_segments(score_points)
    rank_segments = charts.point_line_segments(rank_points)

    for label in labels:
        opposite_segments = rank_segments if label.series == "score" else score_segments
        assert not charts.box_too_close_to_segments(label.box, opposite_segments, pad=4)


def test_combined_trend_labels_prefer_clear_distance_from_crossing_lines() -> None:
    score_points = [(104, 286, 51.5), (520, 326, 50), (936, 124, 59)]
    rank_points = [(104, 326, 33), (520, 326, 33), (936, 86, 28)]
    labels = charts.layout_combined_series_labels(
        score_points=score_points,
        rank_points=rank_points,
        measure_text=lambda text, series: (len(text) * (9 if series == "score" else 11), 16),
        plot_left=70,
        plot_right=964,
        plot_top=86,
        plot_bottom=364,
        width=1040,
        line_pad=16,
    )
    rank_segments = charts.point_line_segments(rank_points)

    label_59 = next(label for label in labels if label.text == "59")
    assert not charts.box_too_close_to_segments(label_59.box, rank_segments, pad=8)
    assert label_59.y > score_points[2][1]


def test_combined_trend_svg_uses_label_backgrounds() -> None:
    records = [
        ScoreRecord("7班", "李浩轩", "七上期中", 70.5, 24),
        ScoreRecord("7班", "李浩轩", "七上期末", 83, 1),
        ScoreRecord("7班", "李浩轩", "七下期中", 78, 9),
    ]
    svg = combined_trend_chart_svg(records, "李浩轩 成绩与位次趋势", exam_order=["七上期中", "七上期末", "七下期中"])

    assert "value-label-bg" in svg
    assert "score-label-bg" in svg
    assert "rank-label-bg" in svg
    assert "dominant-baseline='middle'" in svg
    assert svg.index("line-ref-label") > svg.index("rank-series")


if __name__ == "__main__":
    test_combined_trend_svg_contains_score_and_rank_series()
    test_combined_trend_png_is_a_large_png()
    test_combined_trend_png_offsets_overlapping_value_labels()
    test_combined_trend_labels_avoid_reference_labels_near_first_point()
    test_combined_trend_labels_keep_clear_of_lines()
    test_combined_trend_labels_prefer_clear_distance_from_crossing_lines()
    test_combined_trend_svg_uses_label_backgrounds()
