from __future__ import annotations

from collections import defaultdict
import re
from statistics import mean, median

from .charts import sparkline_svg
from .models import ScoreLine, ScoreRecord


def class_summary(records: list[ScoreRecord], lines: list[ScoreLine], manual_order: list[str] | None = None) -> list[dict[str, object]]:
    grouped: dict[tuple[str, str], list[ScoreRecord]] = defaultdict(list)
    for record in records:
        grouped[(record.class_name, record.exam_name)].append(record)

    rows: list[dict[str, object]] = []
    first_seen = exam_first_seen(records)
    for (class_name, exam_name), group in sorted(grouped.items(), key=lambda item: (item[0][0], exam_sort_key(item[0][1], first_seen, manual_order))):
        scores = [item.score for item in group]
        row: dict[str, object] = {
            "class_name": class_name,
            "exam_name": exam_name,
            "count": len(group),
            "avg": round(mean(scores), 2),
            "median": round(median(scores), 2),
            "max": max(scores),
            "min": min(scores),
        }
        for line in lines:
            if line.label == "低分":
                matched_count = sum(score < line.score for score in scores)
            else:
                matched_count = sum(score >= line.score for score in scores)
            row[f"{line.label}率"] = round(matched_count / len(scores) * 100, 1)
        rows.append(row)
    return rows


def class_names(records: list[ScoreRecord]) -> list[str]:
    return sorted({record.class_name for record in records})


def filter_by_class(records: list[ScoreRecord], class_name: str) -> list[ScoreRecord]:
    if not class_name:
        return records
    return [record for record in records if record.class_name == class_name]


def student_series(
    records: list[ScoreRecord],
    student_name: str,
    class_name: str = "",
    manual_order: list[str] | None = None,
) -> list[ScoreRecord]:
    first_seen = exam_first_seen(records)
    return sorted(
        [
            record
            for record in records
            if record.student_name == student_name and (not class_name or record.class_name == class_name)
        ],
        key=lambda item: exam_sort_key(item.exam_name, first_seen, manual_order),
    )


def student_names(records: list[ScoreRecord]) -> list[str]:
    return sorted({record.student_name for record in records})


def student_exam_coverage(
    records: list[ScoreRecord],
    student_name: str,
    class_name: str = "",
    manual_order: list[str] | None = None,
) -> dict[str, list[str]]:
    ordered_exams = exam_order_labels(records, manual_order)
    series = student_series(records, student_name, class_name, manual_order) if student_name else []
    present = {record.exam_name for record in series}
    return {
        "present": [exam_name for exam_name in ordered_exams if exam_name in present],
        "missing": [exam_name for exam_name in ordered_exams if exam_name not in present],
    }


def exam_names(records: list[ScoreRecord], manual_order: list[str] | None = None) -> list[str]:
    return exam_order_labels(records, manual_order)


def progress_rows(records: list[ScoreRecord], manual_order: list[str] | None = None) -> list[dict[str, object]]:
    first_seen = exam_first_seen(records)
    by_student: dict[tuple[str, str], list[ScoreRecord]] = defaultdict(list)
    for record in records:
        by_student[(record.class_name, record.student_name)].append(record)

    rows: list[dict[str, object]] = []
    for (class_name, student), group in by_student.items():
        ordered = sorted(group, key=lambda item: exam_sort_key(item.exam_name, first_seen, manual_order))
        if len(ordered) < 2:
            continue
        first = ordered[0]
        last = ordered[-1]
        rows.append(
            {
                "class_name": class_name,
                "student_name": student,
                "from_exam": first.exam_name,
                "to_exam": last.exam_name,
                "score_delta": round(last.score - first.score, 2),
                "rank_delta": first.rank - last.rank if first.rank and last.rank else None,
            }
        )
    return sorted(rows, key=lambda item: (item["class_name"], -item["score_delta"]))


def progress_matrix(
    records: list[ScoreRecord],
    manual_order: list[str] | None = None,
    sort_by: str = "score_delta_desc",
) -> dict[str, object]:
    ordered_exams = exam_order_labels(records, manual_order)
    by_student: dict[tuple[str, str], dict[str, ScoreRecord]] = defaultdict(dict)
    for record in records:
        by_student[(record.class_name, record.student_name)][record.exam_name] = record

    rows: list[dict[str, object]] = []
    for (class_name, student_name), exam_map in by_student.items():
        if len(exam_map) < 2:
            continue
        cells: list[dict[str, object]] = []
        spark_values: list[float | None] = []
        prev_score: float | None = None
        prev_rank: int | None = None
        first_score: float | None = None
        first_rank: int | None = None
        last_score: float | None = None
        last_rank: int | None = None
        for exam_name in ordered_exams:
            record = exam_map.get(exam_name)
            if record is None:
                cells.append({
                    "exam": exam_name,
                    "score": None,
                    "rank": None,
                    "score_delta_prev": None,
                    "rank_delta_prev": None,
                })
                spark_values.append(None)
                continue
            score_delta_prev = round(record.score - prev_score, 2) if prev_score is not None else None
            rank_delta_prev = (prev_rank - record.rank) if (prev_rank is not None and record.rank is not None) else None
            cells.append({
                "exam": exam_name,
                "score": record.score,
                "rank": record.rank,
                "score_delta_prev": score_delta_prev,
                "rank_delta_prev": rank_delta_prev,
            })
            spark_values.append(record.score)
            if first_score is None:
                first_score = record.score
                first_rank = record.rank
            last_score = record.score
            last_rank = record.rank
            prev_score = record.score
            prev_rank = record.rank

        score_delta_total = round(last_score - first_score, 2) if (first_score is not None and last_score is not None) else None
        rank_delta_total = (first_rank - last_rank) if (first_rank is not None and last_rank is not None) else None
        rows.append({
            "class_name": class_name,
            "student_name": student_name,
            "cells": cells,
            "latest_score": last_score,
            "latest_rank": last_rank,
            "score_delta_total": score_delta_total,
            "rank_delta_total": rank_delta_total,
            "sparkline": sparkline_svg(spark_values),
            "exam_count": sum(1 for value in spark_values if value is not None),
        })

    rows.sort(key=lambda item: progress_sort_key(item, sort_by))
    return {"exams": ordered_exams, "rows": rows}


def progress_sort_key(row: dict[str, object], sort_by: str) -> tuple[object, ...]:
    class_name = str(row["class_name"])
    student_name = str(row["student_name"])
    latest_score = row.get("latest_score")
    latest_rank = row.get("latest_rank")
    score_delta = row.get("score_delta_total")
    rank_delta = row.get("rank_delta_total")
    if sort_by == "name":
        return (class_name, student_name)
    if sort_by == "score_desc":
        return (class_name, none_last_desc(latest_score), student_name)
    if sort_by == "score_asc":
        return (class_name, none_last_asc(latest_score), student_name)
    if sort_by == "score_delta_asc":
        return (class_name, none_last_asc(score_delta), student_name)
    if sort_by == "rank_delta_desc":
        return (class_name, none_last_desc(rank_delta), student_name)
    if sort_by == "rank_asc":
        return (class_name, none_last_asc(latest_rank), student_name)
    return (class_name, none_last_desc(score_delta), student_name)


def none_last_desc(value: object) -> tuple[int, float]:
    return (1, 0) if value is None else (0, -float(value))


def none_last_asc(value: object) -> tuple[int, float]:
    return (1, 0) if value is None else (0, float(value))


def exam_order_labels(records: list[ScoreRecord], manual_order: list[str] | None = None) -> list[str]:
    first_seen = exam_first_seen(records)
    return sorted(first_seen, key=lambda exam_name: exam_sort_key(exam_name, first_seen, manual_order))


def exam_first_seen(records: list[ScoreRecord]) -> dict[str, int]:
    first_seen: dict[str, int] = {}
    for index, record in enumerate(records):
        first_seen.setdefault(record.exam_name, index)
    return first_seen


def exam_sort_key(
    exam_name: str,
    first_seen: dict[str, int] | None = None,
    manual_order: list[str] | None = None,
) -> tuple[int, int, int, int, int, str]:
    text = normalize_exam_name(exam_name)
    first_seen = first_seen or {}
    if manual_order and exam_name in manual_order:
        return (0, manual_order.index(exam_name), 0, 0, first_seen.get(exam_name, 9999), text)
    grade = grade_order(text)
    semester = semester_order(text)
    phase = phase_order(text)
    return (1, grade, semester, phase, first_seen.get(exam_name, 9999), text)


def normalize_exam_name(exam_name: str) -> str:
    return re.sub(r"\s+", "", exam_name.strip())


def grade_order(text: str) -> int:
    if any(token in text for token in ("七年级", "初一", "七上", "七下", "7年级")):
        return 7
    if any(token in text for token in ("八年级", "初二", "八上", "八下", "8年级")):
        return 8
    if any(token in text for token in ("九年级", "初三", "九上", "九下", "9年级")):
        return 9
    return 99


def semester_order(text: str) -> int:
    if any(token in text for token in ("上学期", "七上", "八上", "九上")):
        return 1
    if any(token in text for token in ("下学期", "七下", "八下", "九下")):
        return 2
    return 9


def phase_order(text: str) -> int:
    if any(token in text for token in ("入学", "开学", "摸底")):
        return 0
    month_number = numbered_exam_index(text)
    if "月考" in text:
        if month_number == 1:
            return 20
        if month_number == 2:
            return 70
        if month_number is not None:
            return 20 + month_number * 10
        return 40
    if "期中" in text:
        return 50
    if "期末" in text:
        return 90
    number = numbered_exam_index(text)
    if number is not None:
        return number * 10
    return 999


def numbered_exam_index(text: str) -> int | None:
    arabic = re.search(r"第?(\d+)次", text)
    if arabic:
        return int(arabic.group(1))
    chinese_numbers = {
        "一": 1,
        "二": 2,
        "两": 2,
        "三": 3,
        "四": 4,
        "五": 5,
        "六": 6,
        "七": 7,
        "八": 8,
        "九": 9,
        "十": 10,
    }
    match = re.search(r"第?([一二两三四五六七八九十])次", text)
    if match:
        return chinese_numbers[match.group(1)]
    return None
