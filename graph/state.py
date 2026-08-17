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
    training_goal: str
    profile_body_weight_kg: float | None
    coach_advice: object
    coach_used: bool
    response: str
