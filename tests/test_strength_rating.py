from analytics.strength import strength_rating
from models import SetEntry


def test_bench_rating_uses_relative_strength_and_rep_count() -> None:
    body_weight = 83
    assert strength_rating("Bench press", [SetEntry(weight_kg=100, reps=10)], body_weight) == 70
    assert strength_rating("Bench press", [SetEntry(weight_kg=100, reps=8)], body_weight) == 65


def test_strength_rating_requires_body_weight() -> None:
    assert strength_rating("Bench press", [SetEntry(weight_kg=100, reps=10)], None) is None
