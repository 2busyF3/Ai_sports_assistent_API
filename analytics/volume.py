from models import ExerciseEntry


def exercise_volume(exercise: ExerciseEntry) -> float:
    return sum(item.weight_kg * item.reps for item in exercise.sets)


def format_sets(exercise: ExerciseEntry) -> str:
    return ", ".join(f"{item.weight_kg:g}x{item.reps}" for item in exercise.sets)
