from models import ExerciseEntry, ExerciseSnapshot
from analytics.volume import exercise_volume


def volume_change_percent(current: ExerciseEntry, previous: ExerciseSnapshot | None) -> float | None:
    if previous is None or previous.total_volume_kg == 0:
        return None
    return (exercise_volume(current) - previous.total_volume_kg) / previous.total_volume_kg * 100
