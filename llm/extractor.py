from __future__ import annotations

import os
import re
from models import ExerciseEntry, SetEntry, WorkoutInput

SET_PATTERN = re.compile(
    r"(?P<weight>\d+(?:[.,]\d+)?)\s*(?:kg|кг|plates?|плитки)?\s*"
    r"(?:[xх×*]|на|for)\s*(?P<reps>\d+)"
    r"(?:\s*(?:reps?|повтор(?:а|ов)?))?"
    r"(?:.*?(?P<count>\d+)\s*(?:sets?|подход(?:а|ов)?))?",
    re.IGNORECASE,
)
BODYWEIGHT_SET_PATTERN = re.compile(
    r"(?P<reps>\d+)\s*(?:reps?\s*)?(?:без\s*веса|body\s*weight|bodyweight|bw)", re.IGNORECASE
)
SLEEP_PATTERN = re.compile(
    r"(?:sleep|сон)\s*[:=-]?\s*(\d+(?:[.,]\d+)?)\s*(?:hours?|hrs?|h|час(?:а|ов)?|ч)", re.IGNORECASE
)
BODY_WEIGHT_PATTERN = re.compile(
    r"(?:(?:body )?weight|вес)\s*[:=-]?\s*(\d+(?:[.,]\d+)?)\s*(?:kg|кг)", re.IGNORECASE
)
DURATION_CLOCK_PATTERN = re.compile(r"(?:workout|training|тренировка).*?(\d+)\s*:\s*(\d+)", re.IGNORECASE)
DURATION_MINUTES_PATTERN = re.compile(r"(?:workout|training|тренировка).*?(\d+)\s*(?:minutes?|mins?|минут(?:а|ы)?)", re.IGNORECASE)
AVERAGE_HR_PATTERN = re.compile(r"(?:average|avg|средн(?:ий|яя))\s*(?:heart rate|hr|пульс)\s*[:=-]?\s*(\d+)", re.IGNORECASE)
HR_RANGE_PATTERN = re.compile(r"(?:range|диапазон).*?(?:from|от)\s*(\d+)\s*(?:to|до|[-–])\s*(\d+)", re.IGNORECASE)


def _number(value: str) -> float:
    return float(value.replace(",", "."))


def detect_language(text: str) -> str:
    """Treat a note containing Cyrillic letters as Russian; English is the default."""
    return "ru" if re.search(r"[А-Яа-яЁё]", text) else "en"


def _repeat_count(line: str, match: re.Match[str]) -> int:
    if match.groupdict().get("count"):
        return int(match["count"])
    # Handles shorthand such as "8x14 x3" or "8x14 на 3".
    suffix = line[match.end():]
    shorthand = re.search(r"(?:[xх×*]|на|for)\s*(\d+)\s*$", suffix, re.IGNORECASE)
    return int(shorthand.group(1)) if shorthand else 1


def extract_locally(text: str) -> WorkoutInput:
    exercises: list[ExerciseEntry] = []
    current_name: str | None = None
    current_sets: list[SetEntry] = []

    def flush() -> None:
        nonlocal current_name, current_sets
        if current_sets:
            exercises.append(ExerciseEntry(name=current_name or "Exercise", sets=current_sets))
        current_name, current_sets = None, []

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            flush()
            continue
        lower = line.lower()
        if SLEEP_PATTERN.search(lower) or BODY_WEIGHT_PATTERN.search(lower):
            continue
        matches = list(SET_PATTERN.finditer(line))
        bodyweight_matches = list(BODYWEIGHT_SET_PATTERN.finditer(line))
        if not matches and not bodyweight_matches:
            flush()
            current_name = line
            continue
        first_match = min(matches + bodyweight_matches, key=lambda item: item.start())
        prefix = line[: first_match.start()].strip(" :,-–—")
        if prefix:
            flush()
            current_name = prefix
        for match in matches:
            current_sets.extend(
                SetEntry(weight_kg=_number(match["weight"]), reps=int(match["reps"]))
                for _ in range(_repeat_count(line, match))
            )
        for match in bodyweight_matches:
            current_sets.append(SetEntry(weight_kg=0, reps=int(match["reps"])))
    flush()

    duration_minutes = None
    if match := DURATION_CLOCK_PATTERN.search(text):
        duration_minutes = int(match.group(1)) * 60 + int(match.group(2))
    elif match := DURATION_MINUTES_PATTERN.search(text):
        duration_minutes = int(match.group(1))
    hr_range = HR_RANGE_PATTERN.search(text)
    return WorkoutInput(
        exercises=exercises,
        sleep_hours=_number(match.group(1)) if (match := SLEEP_PATTERN.search(text)) else None,
        body_weight_kg=_number(match.group(1)) if (match := BODY_WEIGHT_PATTERN.search(text)) else None,
        duration_minutes=duration_minutes,
        average_heart_rate=int(match.group(1)) if (match := AVERAGE_HR_PATTERN.search(text)) else None,
        heart_rate_min=int(hr_range.group(1)) if hr_range else None,
        heart_rate_max=int(hr_range.group(2)) if hr_range else None,
    )


def extract_workout(text: str) -> WorkoutInput:
    """Use OpenAI structured extraction when configured; otherwise use local parser."""
    if not os.getenv("OPENAI_API_KEY"):
        return extract_locally(text)
    from openai import OpenAI
    client = OpenAI()
    completion = client.beta.chat.completions.parse(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        messages=[
            {"role": "system", "content": "Extract workout data from Russian or English text. Do not invent exercises, sets, sleep, body weight, duration, or heart-rate data. Preserve every completed set you can identify."},
            {"role": "user", "content": text},
        ],
        response_format=WorkoutInput,
    )
    result = completion.choices[0].message.parsed
    if result is None:
        raise ValueError("The model did not return structured workout data")
    return result
