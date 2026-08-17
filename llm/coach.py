from __future__ import annotations

import json
import logging
import os
from typing import Any

from pydantic import BaseModel, Field


# Uvicorn exposes this logger at INFO level in Docker, so successful calls are
# visible through `docker compose logs api` without printing any secrets.
logger = logging.getLogger("uvicorn.error")


class NextExercisePlan(BaseModel):
    exercise: str
    prescription: str = Field(description="Specific proposed sets, reps, load or a clear progression criterion.")
    rationale: str = Field(description="Tie the choice to the supplied training data.")


class CoachAdvice(BaseModel):
    headline: str = Field(description="One concise assessment of this session.")
    assessment: str = Field(description="Data-grounded explanation of progress, recovery and the selected user goal.")
    next_session: list[NextExercisePlan] = Field(description="A next-session proposal for the logged exercises.")
    recovery: str = Field(description="Specific recovery or scheduling recommendation based only on supplied data.")
    questions: list[str] = Field(description="At most two high-value questions for data needed next time; empty when none are needed.")


def generate_coach_advice(context: dict[str, Any], language: str) -> CoachAdvice | None:
    """Generate an evidence-bound coaching interpretation only when an API key is configured."""
    if not os.getenv("OPENAI_API_KEY"):
        logger.info("AI coach skipped: OPENAI_API_KEY is not configured")
        return None

    instruction_language = "Russian" if language == "ru" else "English"
    system_prompt = f"""You are a careful strength and hypertrophy coaching assistant. Reply only in {instruction_language}.
Use only the supplied athlete data. Do not invent RPE, injuries, technique quality, a training programme, medical facts, or past performance.
Give a useful, specific decision rather than generic phrases such as 'listen to your body' or 'add a little weight'.
For each logged exercise, state a concrete next-session target or an explicit criterion that determines when to progress.
Interpret the athlete's stated goal (maintenance, strength, or hypertrophy), recovery data and historical comparison together.
Do not diagnose conditions or give medical treatment. If pain or a health warning appears in the provided data, recommend stopping and seeking an appropriate professional.
Keep prescriptions conservative when evidence is missing. Return the requested structured response."""

    try:
        from openai import OpenAI

        model = os.getenv("OPENAI_COACH_MODEL", os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
        logger.info("AI coach request started with model %s", model)
        completion = OpenAI().beta.chat.completions.parse(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(context, ensure_ascii=False, default=str)},
            ],
            response_format=CoachAdvice,
        )
        advice = completion.choices[0].message.parsed
        logger.info("AI coach request completed: structured advice=%s", advice is not None)
        return advice
    except Exception as error:
        # The deterministic recommendation remains available offline or when
        # an API request cannot be completed.
        logger.warning("AI coach request failed; using local fallback (%s)", type(error).__name__)
        return None
