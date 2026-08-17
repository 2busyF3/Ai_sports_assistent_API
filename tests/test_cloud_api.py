from fastapi.testclient import TestClient


def test_cloud_api_workflow(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'cloud.db'}")
    monkeypatch.setenv("SEED_DEMO_DATA", "false")
    from cloud_api.main import app

    with TestClient(app) as client:
        assert client.get("/health").json() == {"status": "ok"}
        profile = client.put("/api/profile", json={"height_cm": 180, "body_weight_kg": 80})
        assert profile.status_code == 200
        assert client.post("/api/sleep", json={"hours": 7.5}).status_code == 200
        workout = client.post("/api/workouts/analyze", json={"text": "Bench press 100x8\n100x8"})
        assert workout.status_code == 200
        assert "response" in workout.json()
        assert len(client.get("/api/history/workouts").json()["workouts"]) == 1
        assert client.get("/api/history/exercises").json()["exercises"] == ["Bench press"]
