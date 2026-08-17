from __future__ import annotations

import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from database.demo import seed_demo_data
from database.factory import create_repository
from graph.graph import build_graph
from models import SleepEntry


class WorkoutNoteRequest(BaseModel):
    text: str = Field(min_length=1, max_length=20_000)


class SleepRequest(BaseModel):
    hours: float = Field(gt=0, le=24)
    slept_at: datetime | None = None


class ProfileRequest(BaseModel):
    height_cm: float = Field(gt=0, le=300)
    body_weight_kg: float = Field(gt=0, le=500)


def repository(request: Request):
    return request.app.state.repository


@asynccontextmanager
async def lifespan(app: FastAPI):
    database_url = os.getenv("DATABASE_URL", "sqlite:///fitness-cloud.db")
    app.state.repository = create_repository(database_url)
    if os.getenv("SEED_DEMO_DATA", "true").lower() == "true":
        seed_demo_data(app.state.repository)
    app.state.graph = build_graph(app.state.repository)
    yield


app = FastAPI(title="AI Fitness Assistant API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[item for item in os.getenv("CORS_ORIGINS", "*").split(",") if item],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health(request: Request) -> dict[str, str]:
    repository(request).has_workouts()
    return {"status": "ok"}


@app.post("/api/workouts/analyze")
def analyze_workout(payload: WorkoutNoteRequest, request: Request) -> dict[str, Any]:
    try:
        result = request.app.state.graph.invoke({"raw_text": payload.text})
    except Exception as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return {"response": result["response"], "workout": result["workout"].model_dump(mode="json")}


@app.get("/api/profile")
def get_profile(request: Request) -> dict[str, Any]:
    profile = repository(request).get_profile()
    return {"profile": profile.model_dump(mode="json") if profile else None}


@app.put("/api/profile")
def update_profile(payload: ProfileRequest, request: Request) -> dict[str, Any]:
    repo = repository(request)
    repo.save_profile(payload.height_cm, payload.body_weight_kg)
    return {"profile": repo.get_profile().model_dump(mode="json")}


@app.post("/api/sleep")
def log_sleep(payload: SleepRequest, request: Request) -> dict[str, Any]:
    repo = repository(request)
    entry = SleepEntry(hours=payload.hours, slept_at=payload.slept_at or datetime.now())
    return {"id": repo.save_sleep(entry), "latest_sleep_hours": repo.latest_sleep_hours()}


@app.get("/api/history/workouts")
def workout_history(request: Request, limit: int = 100) -> dict[str, Any]:
    return {"workouts": repository(request).recent_workouts(min(max(limit, 1), 500))}


@app.get("/api/history/exercises")
def exercise_names(request: Request) -> dict[str, list[str]]:
    return {"exercises": repository(request).exercise_names()}


@app.get("/api/history/exercises/{name}/trend")
def exercise_trend(name: str, request: Request) -> dict[str, Any]:
    return {"exercise": name, "points": [point.model_dump(mode="json") for point in repository(request).exercise_trend(name)]}


@app.post("/api/demo/clear")
def clear_demo(request: Request) -> dict[str, str]:
    repository(request).clear_demo_data()
    return {"status": "demo data cleared"}
