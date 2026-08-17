from __future__ import annotations

from datetime import datetime, timedelta

from database.sqlite import SQLiteRepository
from models import ExerciseEntry, SetEntry, SleepEntry, WorkoutInput


def _exercise(name: str, sets: list[tuple[float, int]]) -> ExerciseEntry:
    return ExerciseEntry(name=name, sets=[SetEntry(weight_kg=weight, reps=reps) for weight, reps in sets])


def seed_demo_data(repository: SQLiteRepository) -> bool:
    """Create a small, realistic data set only for a brand-new local database."""
    if repository.has_workouts():
        return False
    now = datetime.now().replace(second=0, microsecond=0)
    repository.save_profile(180, 78.5, now - timedelta(days=3), is_demo=True)
    sessions = [
        (28, 7.5, [
            _exercise("Bench press", [(80, 8), (80, 8), (80, 7)]),
            _exercise("Barbell row", [(60, 10), (60, 10), (60, 9)]),
        ]),
        (21, 6.0, [
            _exercise("Squat", [(90, 8), (90, 8), (90, 7)]),
            _exercise("Romanian deadlift", [(80, 10), (80, 9), (80, 8)]),
        ]),
        (14, 7.0, [
            _exercise("Bench press", [(82.5, 8), (82.5, 8), (82.5, 7)]),
            _exercise("Barbell row", [(62.5, 10), (62.5, 10), (62.5, 9)]),
        ]),
        (7, 7.5, [
            _exercise("Squat", [(95, 8), (95, 8), (95, 7)]),
            _exercise("Romanian deadlift", [(85, 10), (85, 9), (85, 8)]),
        ]),
        (2, 6.5, [
            _exercise("Bench press", [(85, 8), (85, 8), (85, 7)]),
            _exercise("Barbell row", [(65, 10), (65, 10), (65, 9)]),
        ]),
    ]
    for days_ago, sleep_hours, exercises in sessions:
        performed_at = now - timedelta(days=days_ago)
        repository.save_sleep(SleepEntry(slept_at=performed_at - timedelta(hours=10), hours=sleep_hours), is_demo=True)
        repository.save_workout(WorkoutInput(
            exercises=exercises, sleep_hours=sleep_hours, body_weight_kg=78.5,
            duration_minutes=70, average_heart_rate=122, performed_at=performed_at,
        ), is_demo=True)
    return True
