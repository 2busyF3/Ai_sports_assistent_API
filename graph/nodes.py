from __future__ import annotations

from analytics.fatigue import recovery_risks
from analytics.progression import volume_change_percent
from analytics.volume import exercise_volume, format_sets
from database.sqlite import SQLiteRepository
from graph.state import FitnessState
from llm.coach import CoachAdvice, generate_coach_advice
from llm.extractor import detect_language, extract_workout


def extract_node(state: FitnessState) -> dict:
    """Use already structured interactive input, or extract it from raw text."""
    if "workout" in state:
        return {"language": state.get("language", "en")}
    raw_text = state["raw_text"]
    return {"workout": extract_workout(raw_text), "language": detect_language(raw_text)}


def history_node(repository: SQLiteRepository):
    def node(state: FitnessState) -> dict:
        # Read history before persisting current workout, so comparison is valid.
        workout = state["workout"]
        if workout.sleep_hours is None:
            latest_sleep = repository.latest_sleep_hours(workout.performed_at)
            if latest_sleep is not None:
                workout = workout.model_copy(update={"sleep_hours": latest_sleep})
        previous = {exercise.name: repository.latest_exercise(exercise.name) for exercise in workout.exercises}
        profile = repository.get_profile()
        repository.save_workout(workout)
        return {"workout": workout, "previous": previous,
                "training_goal": profile.training_goal if profile else "maintenance",
                "profile_body_weight_kg": profile.body_weight_kg if profile else None}
    return node


def analytics_node(state: FitnessState) -> dict:
    workout = state["workout"]
    return {"volume_changes": {
        exercise.name: volume_change_percent(exercise, state["previous"].get(exercise.name))
        for exercise in workout.exercises
    }}


def risks_node(state: FitnessState) -> dict:
    workout = state["workout"]
    language = state["language"]
    risks = recovery_risks(workout.sleep_hours, language)
    if workout.duration_minutes and workout.duration_minutes >= 120:
        risks.append(
            "Тренировка длилась не менее двух часов; при накоплении усталости сократите объём."
            if language == "ru" else "The session lasted at least two hours; consider reducing volume if fatigue is accumulating."
        )
    if workout.heart_rate_max and workout.heart_rate_max >= 170:
        risks.append(
            "Пиковый пульс был высоким; дайте себе достаточно времени на восстановление и следите за самочувствием."
            if language == "ru" else "Peak heart rate was high; allow adequate recovery and monitor how you feel."
        )
    return {"risks": risks}


def analysis_node(state: FitnessState) -> dict:
    changes = [item for item in state["volume_changes"].values() if item is not None]
    russian = state["language"] == "ru"
    if changes and min(changes) <= -10:
        recommendation = "сохраните текущий вес и восстановите объём на следующей тренировке." if russian else "keep the current weight and rebuild volume in the next workout."
    elif changes and all(change >= 0 for change in changes):
        recommendation = "добавьте одно повторение в одном подходе или 2,5 кг при уверенной технике." if russian else "add one rep to one set or 2.5 kg if your technique is solid."
    else:
        recommendation = "повторите текущую нагрузку и ориентируйтесь на технику и самочувствие." if russian else "repeat the current load and prioritize technique and how you feel."
    return {"recommendation": recommendation}


def coach_node(state: FitnessState) -> dict:
    """Ask the LLM to interpret verified analytics, not to replace them."""
    workout = state["workout"]
    exercises = []
    for exercise in workout.exercises:
        previous = state["previous"].get(exercise.name)
        exercises.append({
            "name": exercise.name,
            "current_sets": [{"weight_kg": item.weight_kg, "reps": item.reps} for item in exercise.sets],
            "current_volume_kg": exercise_volume(exercise),
            "previous_sets": ([{"weight_kg": item.weight_kg, "reps": item.reps} for item in previous.sets]
                              if previous else None),
            "previous_volume_kg": previous.total_volume_kg if previous else None,
            "volume_change_percent": state["volume_changes"].get(exercise.name),
        })
    context = {
        "training_goal": state.get("training_goal", "maintenance"),
        "athlete_body_weight_kg": workout.body_weight_kg or state.get("profile_body_weight_kg"),
        "session": {
            "sleep_hours": workout.sleep_hours,
            "duration_minutes": workout.duration_minutes,
            "average_heart_rate": workout.average_heart_rate,
            "heart_rate_max": workout.heart_rate_max,
        },
        "exercises": exercises,
        "recovery_flags": state["risks"],
        "deterministic_baseline": state["recommendation"],
    }
    advice = generate_coach_advice(context, state["language"])
    return {"coach_advice": advice, "coach_used": advice is not None}


def response_node(state: FitnessState) -> dict:
    workout = state["workout"]
    russian = state["language"] == "ru"
    advice = state.get("coach_advice")
    if isinstance(advice, CoachAdvice):
        return {"response": _format_coach_advice(advice, russian)}

    lines: list[str] = [
        "Локальный анализ (LLM недоступна или API-ключ не задан)" if russian
        else "Local analysis (LLM unavailable or no API key configured)"
    ]
    for exercise in workout.exercises:
        current_volume = exercise_volume(exercise)
        max_weight = max(item.weight_kg for item in exercise.sets)
        lines.append(f"\n{exercise.name}")
        lines.append(f"{'Подходы' if russian else 'Working sets'}: {format_sets(exercise)}")
        lines.append(f"{'Текущий объём' if russian else 'Current volume'}: {current_volume:,.0f} kg")
        previous = state["previous"].get(exercise.name)
        if previous:
            old_sets = ", ".join(f"{item.weight_kg:g}x{item.reps}" for item in previous.sets)
            lines.append(f"{'Прошлый раз' if russian else 'Previous workout'}: {old_sets}")
            change = state["volume_changes"][exercise.name]
            if russian:
                lines.append(f"Объём {'вырос' if change >= 0 else 'снизился'} на {abs(change):.0f}%.")
                if change >= 5:
                    assessment = "Нагрузка растёт — это хороший сигнал, если техника и самочувствие стабильны."
                elif change <= -10:
                    assessment = "Объём заметно снизился: проверьте восстановление и не форсируйте прогрессию."
                else:
                    assessment = "Нагрузка близка к прошлому уровню — закрепляйте технику и качество повторений."
            else:
                lines.append(f"Volume {'increased' if change >= 0 else 'decreased'} by {abs(change):.0f}%.")
                if change >= 5:
                    assessment = "Workload is increasing, which is positive if technique and recovery remain stable."
                elif change <= -10:
                    assessment = "Volume dropped noticeably; review recovery and do not force progression."
                else:
                    assessment = "Workload is close to the previous session; consolidate technique and rep quality."
            lines.append(f"{'Оценка' if russian else 'Assessment'}: {assessment}")
        else:
            lines.append("Оценка: первая запись — она станет базовой точкой для следующего сравнения." if russian else "Assessment: first record — this becomes the baseline for your next comparison.")
        if state["risks"]:
            suggested_weight = max_weight * 0.9
            next_step = (
                f"Следующий шаг: начните примерно с {suggested_weight:g} kg и оставьте 1–2 повтора в запасе."
                if russian else f"Next step: start around {suggested_weight:g} kg and keep 1–2 repetitions in reserve."
            )
        elif previous and state["volume_changes"][exercise.name] >= 0:
            suggested_weight = max_weight + 2.5
            next_step = (
                f"Следующий шаг: при уверенной технике попробуйте {suggested_weight:g} kg в первом рабочем подходе."
                if russian else f"Next step: with confident technique, try {suggested_weight:g} kg in the first working set."
            )
        else:
            next_step = (
                f"Следующий шаг: повторите рабочий вес {max_weight:g} kg и стремитесь улучшить один повтор."
                if russian else f"Next step: repeat the {max_weight:g} kg working weight and aim to improve one repetition."
            )
        lines.append(next_step)
    if state["risks"]:
        lines.extend(state["risks"])
    recommendation = state["recommendation"]
    if state["risks"]:
        recommendation = "не повышайте рабочий вес; повторите тренировку не раньше чем через 72 часа." if russian else "do not increase working weight; repeat this workout no earlier than 72 hours from now."
    lines.append(f"\n{'Итоговая рекомендация' if russian else 'Overall recommendation'}: {recommendation}")
    return {"response": "\n".join(lines)}


def _format_coach_advice(advice: CoachAdvice, russian: bool) -> str:
    if russian:
        lines = ["AI-анализ тренировки", advice.headline, "", "Оценка", advice.assessment, "", "Следующая тренировка"]
        lines.extend(f"{item.exercise}: {item.prescription}\nПочему: {item.rationale}" for item in advice.next_session)
        lines.extend(["", "Восстановление", advice.recovery])
        if advice.questions:
            lines.extend(["", "Что уточнить", *[f"• {item}" for item in advice.questions]])
    else:
        lines = ["AI workout analysis", advice.headline, "", "Assessment", advice.assessment, "", "Next session"]
        lines.extend(f"{item.exercise}: {item.prescription}\nWhy: {item.rationale}" for item in advice.next_session)
        lines.extend(["", "Recovery", advice.recovery])
        if advice.questions:
            lines.extend(["", "Useful follow-up", *[f"• {item}" for item in advice.questions]])
    return "\n".join(lines)
