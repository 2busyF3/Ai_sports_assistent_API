from typing import TypedDict
from models import ExerciseSnapshot, WorkoutInput


class FitnessState(TypedDict, total=False):
    raw_text: str
    language: str
    workout: WorkoutInput
    previous: dict[str, ExerciseSnapshot | None]
    volume_changes: dict[str, float | None]
    risks: list[str]
    recommendation: str
    response: str
