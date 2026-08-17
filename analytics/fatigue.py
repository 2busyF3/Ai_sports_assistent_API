def recovery_risks(sleep_hours: float | None, language: str = "en") -> list[str]:
    messages = {
        "ru": {
            "missing": "Данные о сне не указаны, поэтому восстановление оценено неполно.",
            "low": "Сон существенно ниже нормы (менее 6 часов).",
            "target": "Сон ниже целевого диапазона (7–9 часов).",
        },
        "en": {
            "missing": "Sleep data was not provided, so recovery cannot be fully assessed.",
            "low": "Sleep is substantially below target (under 6 hours).",
            "target": "Sleep is below the target range (7–9 hours).",
        },
    }["ru" if language == "ru" else "en"]
    if sleep_hours is None:
        return [messages["missing"]]
    if sleep_hours < 6:
        return [messages["low"]]
    if sleep_hours < 7:
        return [messages["target"]]
    return []
