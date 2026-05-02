from __future__ import annotations

from io import BytesIO
from pathlib import Path
import sys

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

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


if __name__ == "__main__":
    test_combined_trend_svg_contains_score_and_rank_series()
    test_combined_trend_png_is_a_large_png()
