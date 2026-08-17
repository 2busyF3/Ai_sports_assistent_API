from analytics.volume import exercise_volume
from graph.nodes import coach_node, response_node
from llm.coach import CoachAdvice, NextExercisePlan
from models import ExerciseEntry, SetEntry, WorkoutInput


def test_llm_coach_output_replaces_template_when_available(monkeypatch) -> None:
    workout = WorkoutInput(exercises=[ExerciseEntry(name="Bench press", sets=[SetEntry(weight_kg=100, reps=8)])], sleep_hours=7.5)
    advice = CoachAdvice(
        headline="Bench press performance is stable.",
        assessment="The logged set matches the previous volume while sleep is adequate.",
        next_session=[NextExercisePlan(exercise="Bench press", prescription="100 kg for 3 sets of 8", rationale="Keep the load until all planned sets are completed.")],
        recovery="Train this movement again after at least 48 hours.",
        questions=["How many repetitions were left in reserve?"],
    )
    monkeypatch.setattr("graph.nodes.generate_coach_advice", lambda context, language: advice)
    state = {
        "workout": workout,
        "previous": {"Bench press": None},
        "volume_changes": {"Bench press": None},
        "risks": [],
        "recommendation": "repeat the current load",
        "training_goal": "strength",
        "language": "en",
    }
    result = coach_node(state)
    assert result["coach_used"] is True
    response = response_node({**state, **result})["response"]
    assert "AI workout analysis" in response
    assert "100 kg for 3 sets of 8" in response
    assert exercise_volume(workout.exercises[0]) == 800
