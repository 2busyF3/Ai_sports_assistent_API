from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class SetEntry(BaseModel):
    weight_kg: float = Field(ge=0)
    reps: int = Field(ge=1)


class ExerciseEntry(BaseModel):
    name: str = Field(min_length=1)
    sets: list[SetEntry] = Field(min_length=1)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return " ".join(value.strip().split()).capitalize()


class WorkoutInput(BaseModel):
    exercises: list[ExerciseEntry] = Field(min_length=1)
    sleep_hours: float | None = Field(default=None, ge=0, le=24)
    body_weight_kg: float | None = Field(default=None, ge=0)
    duration_minutes: int | None = Field(default=None, ge=1)
    average_heart_rate: int | None = Field(default=None, ge=1)
    heart_rate_min: int | None = Field(default=None, ge=1)
    heart_rate_max: int | None = Field(default=None, ge=1)
    performed_at: datetime = Field(default_factory=datetime.now)


class ExerciseSnapshot(BaseModel):
    name: str
    total_volume_kg: float
    sets: list[SetEntry]
    performed_at: datetime


TrainingGoal = Literal["maintenance", "strength", "hypertrophy"]


class UserProfile(BaseModel):
    height_cm: float = Field(gt=0, le=300)
    body_weight_kg: float = Field(gt=0, le=500)
    weight_updated_at: datetime
    training_goal: TrainingGoal = "maintenance"


class ExerciseTrendPoint(BaseModel):
    performed_at: datetime
    total_volume_kg: float
    best_set_score: float
    max_weight_kg: float
    total_reps: int
    best_set_weight_kg: float
    best_set_reps: int


class SleepEntry(BaseModel):
    slept_at: datetime = Field(default_factory=datetime.now)
    hours: float = Field(gt=0, le=24)
