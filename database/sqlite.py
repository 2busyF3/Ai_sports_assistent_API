from __future__ import annotations

import sqlite3
from pathlib import Path

from datetime import datetime, timedelta

from models import ExerciseSnapshot, ExerciseTrendPoint, SleepEntry, UserProfile, WorkoutInput


class SQLiteRepository:
    def __init__(self, path: str | Path = "fitness.db") -> None:
        self.path = str(path)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS workouts (
                    id INTEGER PRIMARY KEY,
                    performed_at TEXT NOT NULL,
                    sleep_hours REAL,
                    body_weight_kg REAL,
                    duration_minutes INTEGER,
                    average_heart_rate INTEGER,
                    heart_rate_min INTEGER,
                    heart_rate_max INTEGER,
                    is_demo INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS exercises (
                    id INTEGER PRIMARY KEY,
                    workout_id INTEGER NOT NULL REFERENCES workouts(id),
                    name TEXT NOT NULL,
                    position INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS exercise_sets (
                    id INTEGER PRIMARY KEY,
                    exercise_id INTEGER NOT NULL REFERENCES exercises(id),
                    weight_kg REAL NOT NULL,
                    reps INTEGER NOT NULL,
                    position INTEGER NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_exercises_name ON exercises(name);
                CREATE TABLE IF NOT EXISTS user_profile (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    height_cm REAL NOT NULL,
                    body_weight_kg REAL NOT NULL,
                    weight_updated_at TEXT NOT NULL,
                    is_demo INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS sleep_logs (
                    id INTEGER PRIMARY KEY,
                    slept_at TEXT NOT NULL,
                    hours REAL NOT NULL,
                    is_demo INTEGER NOT NULL DEFAULT 0
                );
                """
            )
            self._ensure_column(conn, "workouts", "duration_minutes", "INTEGER")
            self._ensure_column(conn, "workouts", "average_heart_rate", "INTEGER")
            self._ensure_column(conn, "workouts", "heart_rate_min", "INTEGER")
            self._ensure_column(conn, "workouts", "heart_rate_max", "INTEGER")
            self._ensure_column(conn, "workouts", "is_demo", "INTEGER NOT NULL DEFAULT 0")
            self._ensure_column(conn, "user_profile", "is_demo", "INTEGER NOT NULL DEFAULT 0")
            self._ensure_column(conn, "sleep_logs", "is_demo", "INTEGER NOT NULL DEFAULT 0")

    @staticmethod
    def _ensure_column(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
        columns = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
        if column not in columns:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    def save_workout(self, workout: WorkoutInput, is_demo: bool = False) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                """INSERT INTO workouts
                (performed_at, sleep_hours, body_weight_kg, duration_minutes, average_heart_rate, heart_rate_min, heart_rate_max, is_demo)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    workout.performed_at.isoformat(), workout.sleep_hours, workout.body_weight_kg,
                    workout.duration_minutes, workout.average_heart_rate,
                    workout.heart_rate_min, workout.heart_rate_max, int(is_demo),
                ),
            )
            workout_id = cursor.lastrowid
            for exercise_position, exercise in enumerate(workout.exercises):
                cursor = conn.execute(
                    "INSERT INTO exercises (workout_id, name, position) VALUES (?, ?, ?)",
                    (workout_id, exercise.name, exercise_position),
                )
                exercise_id = cursor.lastrowid
                conn.executemany(
                    "INSERT INTO exercise_sets (exercise_id, weight_kg, reps, position) VALUES (?, ?, ?, ?)",
                    [(exercise_id, item.weight_kg, item.reps, position) for position, item in enumerate(exercise.sets)],
                )
            return int(workout_id)

    def get_profile(self) -> UserProfile | None:
        with self._connect() as conn:
            row = conn.execute("SELECT height_cm, body_weight_kg, weight_updated_at FROM user_profile WHERE id = 1").fetchone()
        if row is None:
            return None
        return UserProfile(
            height_cm=row["height_cm"], body_weight_kg=row["body_weight_kg"],
            weight_updated_at=datetime.fromisoformat(row["weight_updated_at"]),
        )

    def save_profile(self, height_cm: float, body_weight_kg: float, updated_at: datetime | None = None, is_demo: bool = False) -> None:
        timestamp = (updated_at or datetime.now()).isoformat()
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO user_profile (id, height_cm, body_weight_kg, weight_updated_at, is_demo)
                VALUES (1, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET height_cm = excluded.height_cm,
                    body_weight_kg = excluded.body_weight_kg, weight_updated_at = excluded.weight_updated_at,
                    is_demo = excluded.is_demo""",
                (height_cm, body_weight_kg, timestamp, int(is_demo)),
            )

    def weight_update_due(self, now: datetime | None = None) -> bool:
        profile = self.get_profile()
        if profile is None:
            return True
        return (now or datetime.now()) - profile.weight_updated_at >= timedelta(days=7)

    def save_sleep(self, entry: SleepEntry, is_demo: bool = False) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                "INSERT INTO sleep_logs (slept_at, hours, is_demo) VALUES (?, ?, ?)",
                (entry.slept_at.isoformat(), entry.hours, int(is_demo)),
            )
            return int(cursor.lastrowid)

    def latest_sleep_hours(self, before: datetime | None = None) -> float | None:
        timestamp = (before or datetime.now()).isoformat()
        with self._connect() as conn:
            row = conn.execute(
                "SELECT hours FROM sleep_logs WHERE slept_at <= ? ORDER BY slept_at DESC LIMIT 1",
                (timestamp,),
            ).fetchone()
        return float(row["hours"]) if row else None

    def has_workouts(self) -> bool:
        with self._connect() as conn:
            return conn.execute("SELECT EXISTS(SELECT 1 FROM workouts)").fetchone()[0] == 1

    def clear_demo_data(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """DELETE FROM exercise_sets WHERE exercise_id IN (
                SELECT e.id FROM exercises e JOIN workouts w ON w.id = e.workout_id WHERE w.is_demo = 1)"""
            )
            conn.execute("DELETE FROM exercises WHERE workout_id IN (SELECT id FROM workouts WHERE is_demo = 1)")
            conn.execute("DELETE FROM workouts WHERE is_demo = 1")
            conn.execute("DELETE FROM sleep_logs WHERE is_demo = 1")
            conn.execute("DELETE FROM user_profile WHERE is_demo = 1")

    def latest_exercise(self, name: str) -> ExerciseSnapshot | None:
        """Return the latest historical occurrence, before the just-saved current workout."""
        with self._connect() as conn:
            exercise = conn.execute(
                """
                SELECT e.id, e.name, w.performed_at
                FROM exercises e JOIN workouts w ON w.id = e.workout_id
                WHERE lower(e.name) = lower(?)
                ORDER BY w.performed_at DESC, e.id DESC LIMIT 1
                """,
                (name,),
            ).fetchone()
            if exercise is None:
                return None
            rows = conn.execute(
                "SELECT weight_kg, reps FROM exercise_sets WHERE exercise_id = ? ORDER BY position",
                (exercise["id"],),
            ).fetchall()
        from datetime import datetime
        from models import SetEntry
        sets = [SetEntry(weight_kg=row["weight_kg"], reps=row["reps"]) for row in rows]
        return ExerciseSnapshot(
            name=exercise["name"], sets=sets,
            total_volume_kg=sum(item.weight_kg * item.reps for item in sets),
            performed_at=datetime.fromisoformat(exercise["performed_at"]),
        )

    def exercise_names(self) -> list[str]:
        with self._connect() as conn:
            rows = conn.execute("SELECT DISTINCT name FROM exercises ORDER BY name COLLATE NOCASE").fetchall()
        return [row["name"] for row in rows]

    def exercise_trend(self, name: str) -> list[ExerciseTrendPoint]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT w.performed_at,
                    SUM(s.weight_kg * s.reps) AS total_volume_kg,
                    MAX(s.weight_kg * s.reps) AS best_set_score,
                    MAX(s.weight_kg) AS max_weight_kg,
                    SUM(s.reps) AS total_reps
                FROM exercises e
                JOIN workouts w ON w.id = e.workout_id
                JOIN exercise_sets s ON s.exercise_id = e.id
                WHERE lower(e.name) = lower(?)
                GROUP BY e.id, w.performed_at
                ORDER BY w.performed_at
                """,
                (name,),
            ).fetchall()
        return [ExerciseTrendPoint(
            performed_at=datetime.fromisoformat(row["performed_at"]),
            total_volume_kg=row["total_volume_kg"],
            best_set_score=row["best_set_score"],
            max_weight_kg=row["max_weight_kg"],
            total_reps=row["total_reps"],
        ) for row in rows]

    def recent_workouts(self, limit: int = 100) -> list[dict[str, object]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT w.id, w.performed_at, w.sleep_hours, w.duration_minutes,
                    GROUP_CONCAT(DISTINCT e.name) AS exercises,
                    COALESCE(SUM(s.weight_kg * s.reps), 0) AS total_volume_kg
                FROM workouts w
                LEFT JOIN exercises e ON e.workout_id = w.id
                LEFT JOIN exercise_sets s ON s.exercise_id = e.id
                GROUP BY w.id
                ORDER BY w.performed_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def workouts_in_month(self, year: int, month: int) -> set[int]:
        prefix = f"{year:04d}-{month:02d}-"
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT DISTINCT substr(performed_at, 9, 2) AS day FROM workouts WHERE performed_at LIKE ?",
                (f"{prefix}%",),
            ).fetchall()
        return {int(row["day"]) for row in rows}

    def workouts_on_date(self, year: int, month: int, day: int) -> list[dict[str, object]]:
        date_prefix = f"{year:04d}-{month:02d}-{day:02d}"
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT w.id, w.performed_at, w.sleep_hours, w.duration_minutes,
                    GROUP_CONCAT(DISTINCT e.name) AS exercises,
                    COALESCE(SUM(s.weight_kg * s.reps), 0) AS total_volume_kg
                FROM workouts w
                LEFT JOIN exercises e ON e.workout_id = w.id
                LEFT JOIN exercise_sets s ON s.exercise_id = e.id
                WHERE w.performed_at LIKE ?
                GROUP BY w.id
                ORDER BY w.performed_at
                """,
                (f"{date_prefix}%",),
            ).fetchall()
        return [dict(row) for row in rows]

    def workout_details(self, workout_id: int) -> list[dict[str, object]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT e.name, s.weight_kg, s.reps, s.position
                FROM exercises e
                JOIN exercise_sets s ON s.exercise_id = e.id
                WHERE e.workout_id = ?
                ORDER BY e.position, s.position
                """,
                (workout_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def latest_workout_exercises(self) -> list[dict[str, object]]:
        with self._connect() as conn:
            latest = conn.execute("SELECT id FROM workouts ORDER BY performed_at DESC, id DESC LIMIT 1").fetchone()
            if latest is None:
                return []
            rows = conn.execute(
                """
                SELECT e.name, MAX(s.weight_kg) AS max_weight_kg, MAX(s.reps) AS max_reps
                FROM exercises e JOIN exercise_sets s ON s.exercise_id = e.id
                WHERE e.workout_id = ?
                GROUP BY e.id
                ORDER BY e.position
                """,
                (latest["id"],),
            ).fetchall()
        return [dict(row) for row in rows]
