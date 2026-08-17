from __future__ import annotations

from models import SetEntry


# A score of 100 represents a demanding relative-strength reference for a
# loaded compound exercise. Unknown exercises use a conservative general
# reference, so the score remains useful as a personal trend rather than a
# medical or competitive classification.
BENCHMARK_RATIOS = {
    "bench": 2.3,
    "жим лежа": 2.3,
    "squat": 3.0,
    "присед": 3.0,
    "deadlift": 3.5,
    "станов": 3.5,
    "overhead press": 1.5,
    "жим стоя": 1.5,
    "barbell row": 2.0,
    "тяга штанги": 2.0,
}
DEFAULT_BENCHMARK_RATIO = 1.5


def estimated_one_rep_max(weight_kg: float, reps: int) -> float:
    """Epley estimate, capped to keep very high-rep sets from overstating strength."""
    if weight_kg <= 0:
        return 0.0
    return weight_kg * (1 + min(reps, 15) / 30)


def strength_rating(exercise_name: str, sets: list[SetEntry], body_weight_kg: float | None) -> int | None:
    """Return a readable 0–100 relative-strength score for one exercise session."""
    if not sets or not body_weight_kg or body_weight_kg <= 0:
        return None
    best_estimated_max = max(estimated_one_rep_max(item.weight_kg, item.reps) for item in sets)
    name = exercise_name.lower()
    benchmark = next((ratio for marker, ratio in BENCHMARK_RATIOS.items() if marker in name), DEFAULT_BENCHMARK_RATIO)
    raw_score = min(100, max(0, best_estimated_max / body_weight_kg / benchmark * 100))
    return int(5 * round(raw_score / 5))
