from fastapi.testclient import TestClient
from datetime import datetime


def test_cloud_api_workflow(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'cloud.db'}")
    monkeypatch.setenv("SEED_DEMO_DATA", "false")
    from cloud_api.main import app

    with TestClient(app) as client:
        assert client.get("/health").json() == {"status": "ok"}
        profile = client.put("/api/profile", json={"height_cm": 180, "body_weight_kg": 80, "training_goal": "strength"})
        assert profile.status_code == 200
        assert profile.json()["profile"]["training_goal"] == "strength"
        assert client.post("/api/sleep", json={"hours": 7.5}).status_code == 200
        workout = client.post("/api/workouts/analyze", json={"text": "Bench press 100x8\n100x8"})
        assert workout.status_code == 200
        assert "response" in workout.json()
        assert len(client.get("/api/history/workouts").json()["workouts"]) == 1
        assert client.get("/api/history/exercises").json()["exercises"] == ["Bench press"]
        trend = client.get("/api/history/exercises/Bench%20press/trend").json()["points"]
        assert trend[0]["strength_rating"] is not None
        dashboard = client.get("/api/dashboard").json()
        assert dashboard["profile"]["height_cm"] == 180
        assert dashboard["training_goal"] == "strength"
        assert dashboard["suggestions"][0]["name"] == "Bench press"
        today = datetime.now()
        assert client.get(f"/api/history/calendar?year={today.year}&month={today.month}").status_code == 200
