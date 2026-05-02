from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path

from .models import ScoreLine, ScoreRecord


DATA_DIR = Path("data")
SCORES_PATH = DATA_DIR / "scores.csv"
SETTINGS_PATH = DATA_DIR / "settings.json"
PREVIEW_DIR = DATA_DIR / "previews"
BACKUP_DIR = DATA_DIR / "backups"
MAX_BACKUPS = 10


def ensure_data_dir() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    PREVIEW_DIR.mkdir(exist_ok=True)


def _backup_existing_scores() -> None:
    if not SCORES_PATH.exists() or SCORES_PATH.stat().st_size == 0:
        return
    BACKUP_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target = BACKUP_DIR / f"scores_{timestamp}.csv"
    if target.exists():
        return
    target.write_bytes(SCORES_PATH.read_bytes())
    backups = sorted(BACKUP_DIR.glob("scores_*.csv"))
    if len(backups) > MAX_BACKUPS:
        for old in backups[:-MAX_BACKUPS]:
            old.unlink(missing_ok=True)


def load_scores() -> list[ScoreRecord]:
    ensure_data_dir()
    if not SCORES_PATH.exists():
        return []
    records: list[ScoreRecord] = []
    with SCORES_PATH.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rank_text = (row.get("rank") or "").strip()
            records.append(
                ScoreRecord(
                    class_name=row["class_name"],
                    student_name=row["student_name"],
                    exam_name=row["exam_name"],
                    score=float(row["score"]),
                    rank=int(rank_text) if rank_text else None,
                )
            )
    return records


def save_scores(records: list[ScoreRecord]) -> None:
    ensure_data_dir()
    _backup_existing_scores()
    with SCORES_PATH.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["class_name", "student_name", "exam_name", "score", "rank"],
        )
        writer.writeheader()
        for record in records:
            writer.writerow(
                {
                    "class_name": record.class_name,
                    "student_name": record.student_name,
                    "exam_name": record.exam_name,
                    "score": record.score,
                    "rank": record.rank or "",
                }
            )


def append_scores(records: list[ScoreRecord]) -> None:
    existing = load_scores()
    existing.extend(records)
    save_scores(existing)


def load_lines(default_lines: list[ScoreLine]) -> list[ScoreLine]:
    ensure_data_dir()
    if not SETTINGS_PATH.exists():
        return default_lines
    payload = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    return [ScoreLine(item["label"], float(item["score"])) for item in payload.get("lines", [])] or default_lines


def save_lines(lines: list[ScoreLine]) -> None:
    ensure_data_dir()
    payload = load_settings()
    payload["lines"] = [{"label": item.label, "score": item.score} for item in lines]
    SETTINGS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_exam_order() -> list[str]:
    return [str(item) for item in load_settings().get("exam_order", [])]


def save_exam_order(exam_order: list[str]) -> None:
    ensure_data_dir()
    payload = load_settings()
    payload["exam_order"] = exam_order
    SETTINGS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_settings() -> dict[str, object]:
    ensure_data_dir()
    if not SETTINGS_PATH.exists():
        return {}
    return json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))


def save_preview(token: str, payload: dict[str, object]) -> None:
    ensure_data_dir()
    preview_path(token).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_preview(token: str) -> dict[str, object] | None:
    path = preview_path(token)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def delete_preview(token: str) -> None:
    path = preview_path(token)
    if path.exists():
        path.unlink()


def preview_path(token: str) -> Path:
    safe_token = "".join(ch for ch in token if ch.isalnum() or ch in ("-", "_"))
    return PREVIEW_DIR / f"{safe_token}.json"
