from __future__ import annotations

import os
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Iterator

from psycopg import Connection, connect
from psycopg.rows import dict_row

from models import ExerciseSnapshot, ExerciseTrendPoint, SetEntry, SleepEntry, UserProfile, WorkoutInput


class PostgresRepository:
    """PostgreSQL implementation of the repository used by the LangGraph workflow."""

    def __init__(self, database_url: str | None = None) -> None:
        self.database_url = database_url or os.environ["DATABASE_URL"]
        self._initialize()

    @contextmanager
    def _connect(self) -> Iterator[Connection]:
        with connect(self.database_url, row_factory=dict_row) as conn:
            yield conn

    def _initialize(self) -> None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS workouts (
                    id BIGSERIAL PRIMARY KEY,
                    performed_at TIMESTAMP NOT NULL,
                    sleep_hours REAL,
                    body_weight_kg REAL,
                    duration_minutes INTEGER,
                    average_heart_rate INTEGER,
                    heart_rate_min INTEGER,
                    heart_rate_max INTEGER,
                    is_demo BOOLEAN NOT NULL DEFAULT FALSE
                );
                CREATE TABLE IF NOT EXISTS exercises (
                    id BIGSERIAL PRIMARY KEY,
                    workout_id BIGINT NOT NULL REFERENCES workouts(id),
                    name TEXT NOT NULL,
                    position INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS exercise_sets (
                    id BIGSERIAL PRIMARY KEY,
                    exercise_id BIGINT NOT NULL REFERENCES exercises(id),
                    weight_kg REAL NOT NULL,
                    reps INTEGER NOT NULL,
                    position INTEGER NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_exercises_name ON exercises(name);
                CREATE TABLE IF NOT EXISTS user_profile (
                    id SMALLINT PRIMARY KEY CHECK (id = 1),
                    height_cm REAL NOT NULL,
                    body_weight_kg REAL NOT NULL,
                    weight_updated_at TIMESTAMP NOT NULL,
                    training_goal TEXT NOT NULL DEFAULT 'maintenance',
                    is_demo BOOLEAN NOT NULL DEFAULT FALSE
                );
                CREATE TABLE IF NOT EXISTS sleep_logs (
                    id BIGSERIAL PRIMARY KEY,
                    slept_at TIMESTAMP NOT NULL,
                    hours REAL NOT NULL,
                    is_demo BOOLEAN NOT NULL DEFAULT FALSE
                );
            """)
            cur.execute("ALTER TABLE user_profile ADD COLUMN IF NOT EXISTS training_goal TEXT NOT NULL DEFAULT 'maintenance'")

    def save_workout(self, workout: WorkoutInput, is_demo: bool = False) -> int:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """INSERT INTO workouts
                (performed_at, sleep_hours, body_weight_kg, duration_minutes, average_heart_rate, heart_rate_min, heart_rate_max, is_demo)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id""",
                (workout.performed_at, workout.sleep_hours, workout.body_weight_kg, workout.duration_minutes,
                 workout.average_heart_rate, workout.heart_rate_min, workout.heart_rate_max, is_demo),
            )
            workout_id = cur.fetchone()["id"]
            for exercise_position, exercise in enumerate(workout.exercises):
                cur.execute(
                    "INSERT INTO exercises (workout_id, name, position) VALUES (%s, %s, %s) RETURNING id",
                    (workout_id, exercise.name, exercise_position),
                )
                exercise_id = cur.fetchone()["id"]
                cur.executemany(
                    "INSERT INTO exercise_sets (exercise_id, weight_kg, reps, position) VALUES (%s, %s, %s, %s)",
                    [(exercise_id, item.weight_kg, item.reps, position) for position, item in enumerate(exercise.sets)],
                )
            return int(workout_id)

    def latest_exercise(self, name: str) -> ExerciseSnapshot | None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("""
                SELECT e.id, e.name, w.performed_at FROM exercises e JOIN workouts w ON w.id = e.workout_id
                WHERE lower(e.name) = lower(%s) ORDER BY w.performed_at DESC, e.id DESC LIMIT 1
            """, (name,))
            exercise = cur.fetchone()
            if exercise is None:
                return None
            cur.execute("SELECT weight_kg, reps FROM exercise_sets WHERE exercise_id = %s ORDER BY position", (exercise["id"],))
            sets = [SetEntry(weight_kg=row["weight_kg"], reps=row["reps"]) for row in cur.fetchall()]
        return ExerciseSnapshot(name=exercise["name"], sets=sets,
                                total_volume_kg=sum(item.weight_kg * item.reps for item in sets),
                                performed_at=exercise["performed_at"])

    def get_profile(self) -> UserProfile | None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT height_cm, body_weight_kg, weight_updated_at, training_goal FROM user_profile WHERE id = 1")
            row = cur.fetchone()
        return UserProfile(**row) if row else None

    def save_profile(self, height_cm: float, body_weight_kg: float, updated_at: datetime | None = None,
                     is_demo: bool = False, training_goal: str = "maintenance") -> None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("""
                INSERT INTO user_profile (id, height_cm, body_weight_kg, weight_updated_at, training_goal, is_demo)
                VALUES (1, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET height_cm = EXCLUDED.height_cm, body_weight_kg = EXCLUDED.body_weight_kg,
                    weight_updated_at = EXCLUDED.weight_updated_at, training_goal = EXCLUDED.training_goal, is_demo = EXCLUDED.is_demo
            """, (height_cm, body_weight_kg, updated_at or datetime.now(), training_goal, is_demo))

    def weight_update_due(self, now: datetime | None = None) -> bool:
        profile = self.get_profile()
        return profile is None or (now or datetime.now()) - profile.weight_updated_at >= timedelta(days=7)

    def save_sleep(self, entry: SleepEntry, is_demo: bool = False) -> int:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("INSERT INTO sleep_logs (slept_at, hours, is_demo) VALUES (%s, %s, %s) RETURNING id",
                        (entry.slept_at, entry.hours, is_demo))
            return int(cur.fetchone()["id"])

    def latest_sleep_hours(self, before: datetime | None = None) -> float | None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT hours FROM sleep_logs WHERE slept_at <= %s ORDER BY slept_at DESC LIMIT 1", (before or datetime.now(),))
            row = cur.fetchone()
        return float(row["hours"]) if row else None

    def has_workouts(self) -> bool:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT EXISTS(SELECT 1 FROM workouts) AS value")
            return bool(cur.fetchone()["value"])

    def clear_demo_data(self) -> None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("DELETE FROM exercise_sets WHERE exercise_id IN (SELECT e.id FROM exercises e JOIN workouts w ON w.id=e.workout_id WHERE w.is_demo)")
            cur.execute("DELETE FROM exercises WHERE workout_id IN (SELECT id FROM workouts WHERE is_demo)")
            cur.execute("DELETE FROM workouts WHERE is_demo")
            cur.execute("DELETE FROM sleep_logs WHERE is_demo")
            cur.execute("DELETE FROM user_profile WHERE is_demo")

    def exercise_names(self) -> list[str]:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT DISTINCT name FROM exercises ORDER BY name")
            return [row["name"] for row in cur.fetchall()]

    def exercise_trend(self, name: str) -> list[ExerciseTrendPoint]:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("""
                SELECT w.performed_at, SUM(s.weight_kg*s.reps) AS total_volume_kg,
                    MAX(s.weight_kg*s.reps) AS best_set_score, MAX(s.weight_kg) AS max_weight_kg, SUM(s.reps) AS total_reps,
                    (SELECT s2.weight_kg FROM exercise_sets s2 WHERE s2.exercise_id=e.id
                     ORDER BY s2.weight_kg*s2.reps DESC, s2.position LIMIT 1) AS best_set_weight_kg,
                    (SELECT s2.reps FROM exercise_sets s2 WHERE s2.exercise_id=e.id
                     ORDER BY s2.weight_kg*s2.reps DESC, s2.position LIMIT 1) AS best_set_reps
                FROM exercises e JOIN workouts w ON w.id=e.workout_id JOIN exercise_sets s ON s.exercise_id=e.id
                WHERE lower(e.name)=lower(%s) GROUP BY e.id, w.performed_at ORDER BY w.performed_at
            """, (name,))
            return [ExerciseTrendPoint(**row) for row in cur.fetchall()]

    def recent_workouts(self, limit: int = 100) -> list[dict[str, object]]:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("""
                SELECT w.id, w.performed_at, w.sleep_hours, w.duration_minutes, STRING_AGG(DISTINCT e.name, ', ') AS exercises,
                    COALESCE(SUM(s.weight_kg*s.reps),0) AS total_volume_kg
                FROM workouts w LEFT JOIN exercises e ON e.workout_id=w.id LEFT JOIN exercise_sets s ON s.exercise_id=e.id
                GROUP BY w.id ORDER BY w.performed_at DESC LIMIT %s
            """, (limit,))
            return [dict(row) for row in cur.fetchall()]

    def workouts_in_month(self, year: int, month: int) -> set[int]:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT DISTINCT EXTRACT(DAY FROM performed_at)::int AS day FROM workouts WHERE EXTRACT(YEAR FROM performed_at)=%s AND EXTRACT(MONTH FROM performed_at)=%s", (year, month))
            return {row["day"] for row in cur.fetchall()}

    def workouts_on_date(self, year: int, month: int, day: int) -> list[dict[str, object]]:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("""
                SELECT w.id,w.performed_at,w.sleep_hours,w.duration_minutes,STRING_AGG(DISTINCT e.name, ', ') AS exercises,
                    COALESCE(SUM(s.weight_kg*s.reps),0) AS total_volume_kg
                FROM workouts w LEFT JOIN exercises e ON e.workout_id=w.id LEFT JOIN exercise_sets s ON s.exercise_id=e.id
                WHERE EXTRACT(YEAR FROM w.performed_at)=%s AND EXTRACT(MONTH FROM w.performed_at)=%s AND EXTRACT(DAY FROM w.performed_at)=%s
                GROUP BY w.id ORDER BY w.performed_at
            """, (year, month, day))
            return [dict(row) for row in cur.fetchall()]

    def workout_details(self, workout_id: int) -> list[dict[str, object]]:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("""SELECT e.name,s.weight_kg,s.reps,s.position FROM exercises e JOIN exercise_sets s ON s.exercise_id=e.id
                         WHERE e.workout_id=%s ORDER BY e.position,s.position""", (workout_id,))
            return [dict(row) for row in cur.fetchall()]

    def latest_workout_exercises(self) -> list[dict[str, object]]:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("""SELECT e.name,MAX(s.weight_kg) AS max_weight_kg,MAX(s.reps) AS max_reps FROM exercises e
                         JOIN exercise_sets s ON s.exercise_id=e.id WHERE e.workout_id=(SELECT id FROM workouts ORDER BY performed_at DESC,id DESC LIMIT 1)
                         GROUP BY e.id ORDER BY MIN(e.position)""")
            return [dict(row) for row in cur.fetchall()]
