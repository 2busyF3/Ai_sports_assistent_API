from datetime import datetime, timedelta

from database.sqlite import SQLiteRepository
from database.demo import seed_demo_data
from graph.graph import build_graph
from llm.extractor import extract_locally
from main import collect_workout_note, initialize_or_update_profile
from models import SleepEntry


TEXT = """Bench press 100x8
100x8
100x6

Chest fly 20x12
20x10
20x9

Sleep 6 hours
Weight 83 kg"""


def test_local_extractor() -> None:
    workout = extract_locally(TEXT)
    assert len(workout.exercises) == 2
    assert workout.exercises[0].name == "Bench press"
    assert workout.exercises[0].sets[-1].reps == 6
    assert workout.sleep_hours == 6


def test_russian_free_form_parser_and_session_metrics() -> None:
    workout = extract_locally("""Скручивания на пресс
15 без веса
5кг на 15
10кг на 15

Приседания в Смите, до 90 градусов
25х12
65х8
95х8

Поднимания на носки
60кг на 15 2 подхода
8х14 на 3

Тренировка длилась 1:30
Средний пульс 126 диапазон от 82 до 171""")
    assert [exercise.name for exercise in workout.exercises] == [
        "Скручивания на пресс", "Приседания в смите, до 90 градусов", "Поднимания на носки",
    ]
    assert [(item.weight_kg, item.reps) for item in workout.exercises[0].sets] == [(0, 15), (5, 15), (10, 15)]
    assert len(workout.exercises[2].sets) == 5
    assert workout.duration_minutes == 90
    assert (workout.average_heart_rate, workout.heart_rate_min, workout.heart_rate_max) == (126, 82, 171)


def test_response_uses_note_language(tmp_path) -> None:
    graph = build_graph(SQLiteRepository(tmp_path / "language.db"))
    result = graph.invoke({"raw_text": "Приседания 100х8\n100х8\nСон 6 часов"})
    assert "Приседания" in result["response"]
    assert "Подходы:" in result["response"]
    assert "Сон ниже целевого диапазона" in result["response"]
    assert "Итоговая рекомендация:" in result["response"]


def test_note_input_and_weekly_profile(tmp_path) -> None:
    note_answers = iter(["Bench press 100x8", "100x8", "END"])
    assert collect_workout_note(lambda _: next(note_answers)) == "Bench press 100x8\n100x8"
    repository = SQLiteRepository(tmp_path / "profile.db")
    first_setup = iter(["180", "83"])
    initialize_or_update_profile(repository, lambda _: next(first_setup))
    profile = repository.get_profile()
    assert profile and (profile.height_cm, profile.body_weight_kg) == (180, 83)
    assert not repository.weight_update_due(profile.weight_updated_at + timedelta(days=6))
    repository.save_profile(180, 83, datetime.now() - timedelta(days=8))
    update = iter(["82"])
    initialize_or_update_profile(repository, lambda _: next(update))
    assert repository.get_profile().body_weight_kg == 82


def test_graph_persists_and_compares(tmp_path) -> None:
    graph = build_graph(SQLiteRepository(tmp_path / "test.db"))
    first = graph.invoke({"raw_text": TEXT})
    second = graph.invoke({"raw_text": TEXT})
    assert "first record" in first["response"]
    assert "Previous workout: 100x8, 100x8, 100x6" in second["response"]
    assert "Sleep is below the target range" in second["response"]


def test_history_queries_return_strength_trend(tmp_path) -> None:
    repository = SQLiteRepository(tmp_path / "history.db")
    graph = build_graph(repository)
    graph.invoke({"raw_text": "Bench press 100x8\n100x8\nSleep 8 hours"})
    graph.invoke({"raw_text": "Bench press 105x8\n105x8\nSleep 8 hours"})
    assert repository.exercise_names() == ["Bench press"]
    trend = repository.exercise_trend("Bench press")
    assert len(trend) == 2
    assert trend[-1].best_set_score == 840
    assert trend[-1].total_volume_kg == 1680
    recent = repository.recent_workouts()
    assert recent[0]["exercises"] == "Bench press"


def test_logged_sleep_is_used_for_next_workout_analysis(tmp_path) -> None:
    repository = SQLiteRepository(tmp_path / "sleep.db")
    repository.save_sleep(SleepEntry(hours=6))
    result = build_graph(repository).invoke({"raw_text": "Bench press 100x8\n100x8"})
    assert "Sleep is below the target range" in result["response"]


def test_calendar_and_workout_detail_queries(tmp_path) -> None:
    repository = SQLiteRepository(tmp_path / "calendar.db")
    build_graph(repository).invoke({"raw_text": "Squat 100x5\n100x5"})
    today = datetime.now()
    assert today.day in repository.workouts_in_month(today.year, today.month)
    workouts = repository.workouts_on_date(today.year, today.month, today.day)
    assert len(workouts) == 1
    assert repository.workout_details(int(workouts[0]["id"]))[0]["name"] == "Squat"
    suggestion = repository.latest_workout_exercises()[0]
    assert (suggestion["name"], suggestion["max_weight_kg"], suggestion["max_reps"]) == ("Squat", 100, 5)


def test_demo_data_is_seeded_once_and_can_be_cleared(tmp_path) -> None:
    repository = SQLiteRepository(tmp_path / "demo.db")
    assert seed_demo_data(repository)
    assert repository.has_workouts()
    assert not seed_demo_data(repository)
    repository.clear_demo_data()
    assert not repository.has_workouts()
    assert repository.get_profile() is None
