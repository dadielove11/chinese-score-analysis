from __future__ import annotations

from io import BytesIO
from pathlib import Path
import os
import sys
import tempfile
from unittest.mock import patch

from openpyxl import load_workbook
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from student_analysis.charts import combined_trend_chart_svg
import student_analysis.charts as charts
from student_analysis.models import DEFAULT_LINES, ScoreRecord
from student_analysis.storage import save_scores
from student_analysis.web import create_app


def sample_records() -> list[ScoreRecord]:
    return [
        ScoreRecord("7班", "张三", "七上期中", 72.5, 18),
        ScoreRecord("7班", "张三", "七上期末", 81, 8),
        ScoreRecord("7班", "张三", "七下期中", 78, 11),
        ScoreRecord("7班", "李四", "七上期中", 66, 25),
        ScoreRecord("7班", "李四", "七上期末", 70, 20),
    ]


def test_default_score_lines_are_teacher_thresholds() -> None:
    assert [(line.label, line.score) for line in DEFAULT_LINES] == [
        ("优秀", 80),
        ("良好", 70),
        ("及格", 60),
        ("低分", 40),
    ]


def test_combined_chart_legend_uses_colored_lines() -> None:
    svg = combined_trend_chart_svg(
        sample_records()[:3],
        "张三 成绩与位次趋势",
        exam_order=["七上期中", "七上期末", "七下期中"],
    )

    assert "score-legend-line" in svg
    assert "rank-legend-line" in svg
    assert "legend-point" not in svg


def test_export_progress_sheet_expands_each_exam_column() -> None:
    root = Path.cwd()
    tmp = tempfile.TemporaryDirectory()
    try:
        os.chdir(tmp.name)
        save_scores(sample_records())
        response = create_app().test_client().get("/export.xlsx")
        assert response.status_code == 200

        workbook = load_workbook(BytesIO(response.data), data_only=True)
        response.close()
        sheet = workbook["进退步概览"]
        headers = [cell.value for cell in sheet[1]]
        assert headers == [
            "班级",
            "姓名",
            "考试次数",
            "七上期中",
            "七上期末",
            "七下期中",
            "总分变化",
            "位次进步",
        ]
        first_row = [cell.value for cell in sheet[2]]
        assert first_row[0:3] == ["7班", "张三", 3]
        assert first_row[3:6] == ["72.5（第18名）", "81（第8名）", "78（第11名）"]
        workbook.close()
    finally:
        os.chdir(root)
        tmp.cleanup()


def test_combined_chart_png_rotates_crowded_axis_labels() -> None:
    records = [
        ScoreRecord("7班", "张三", f"七上第{index}次阶段检测", 60 + index, 30 - index)
        for index in range(1, 13)
    ]
    exam_order = [record.exam_name for record in records]

    with patch.object(charts, "draw_rotated_centered_text") as rotated_text:
        png = charts.combined_trend_chart_png(records, "张三 成绩与位次趋势", exam_order=exam_order)

    label_calls = [call for call in rotated_text.call_args_list if call.args and call.args[1] in exam_order]
    assert len(label_calls) == len(exam_order)
    assert min(call.args[2] for call in label_calls) >= 120
    assert Image.open(BytesIO(png)).height >= 1000


if __name__ == "__main__":
    test_default_score_lines_are_teacher_thresholds()
    test_combined_chart_legend_uses_colored_lines()
    test_export_progress_sheet_expands_each_exam_column()
    test_combined_chart_png_rotates_crowded_axis_labels()
