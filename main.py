import argparse

from database.sqlite import SQLiteRepository
from graph.graph import build_graph


def _required_number(label: str, input_fn=input) -> float:
    while True:
        value = input_fn(label).strip().replace(",", ".")
        try:
            number = float(value)
            if number > 0:
                return number
        except ValueError:
            pass
        print("Enter a number greater than zero.")


def collect_workout_note(input_fn=input) -> str:
    print("Paste or type your workout.")
    print("Type END on a separate line when you are finished.")
    lines: list[str] = []
    while True:
        line = input_fn("")
        if line.strip().upper() == "END":
            break
        lines.append(line)
    text = "\n".join(lines).strip()
    if not text:
        raise ValueError("Workout note cannot be empty.")
    return text


def initialize_or_update_profile(repository: SQLiteRepository, input_fn=input) -> None:
    """Ask for height/weight once, and request only a weekly weight update later."""
    profile = repository.get_profile()
    if profile is None:
        print("First-time setup: these metrics are stored once and are not requested after every workout.")
        repository.save_profile(
            height_cm=_required_number("Height (cm): ", input_fn),
            body_weight_kg=_required_number("Current body weight (kg): ", input_fn),
        )
        return
    if repository.weight_update_due():
        value = input_fn("Weekly body-weight update in kg (press Enter to skip): ").strip().replace(",", ".")
        if value:
            try:
                weight = float(value)
                if weight > 0:
                    repository.save_profile(profile.height_cm, weight)
                else:
                    print("Weight update skipped: value must be greater than zero.")
            except ValueError:
                print("Weight update skipped: enter a number next time.")


def main() -> None:
    parser = argparse.ArgumentParser(description="AI Fitness Assistant")
    parser.add_argument("--text", help="Free-form workout note")
    parser.add_argument("--db", default="fitness.db", help="Path to the SQLite database")
    args = parser.parse_args()
    repository = SQLiteRepository(args.db)
    initialize_or_update_profile(repository)
    raw_text = args.text or collect_workout_note()
    result = build_graph(repository).invoke({"raw_text": raw_text})
    print(result["response"])


if __name__ == "__main__":
    main()
