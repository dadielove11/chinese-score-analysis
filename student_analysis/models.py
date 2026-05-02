from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class ScoreRecord:
    class_name: str
    student_name: str
    exam_name: str
    score: float
    rank: int | None = None


@dataclass(frozen=True)
class ScoreLine:
    label: str
    score: float


DEFAULT_LINES = [
    ScoreLine("优秀", 80),
    ScoreLine("良好", 70),
    ScoreLine("及格", 60),
    ScoreLine("低分", 40),
]


def coerce_score(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace("，", ".")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def competition_ranks(records: Iterable[ScoreRecord]) -> list[ScoreRecord]:
    grouped: dict[tuple[str, str], list[ScoreRecord]] = {}
    for record in records:
        grouped.setdefault((record.class_name, record.exam_name), []).append(record)

    ranked: list[ScoreRecord] = []
    for group in grouped.values():
        ordered = sorted(group, key=lambda item: (-item.score, item.student_name))
        last_score: float | None = None
        last_rank = 0
        for index, record in enumerate(ordered, start=1):
            rank = last_rank if last_score == record.score else index
            ranked.append(
                ScoreRecord(
                    class_name=record.class_name,
                    student_name=record.student_name,
                    exam_name=record.exam_name,
                    score=record.score,
                    rank=rank,
                )
            )
            last_score = record.score
            last_rank = rank
    return ranked
