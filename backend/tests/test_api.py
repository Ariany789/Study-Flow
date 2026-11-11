import os
from uuid import uuid4

os.environ["DATABASE_URL"] = "sqlite:///./test-studyflow.db"
os.environ["JWT_SECRET"] = "test-secret"

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.main import app
from app.database import engine, ensure_compatible_schema

client = TestClient(app)


def test_register_and_create_task():
    email = f"ana-{uuid4().hex}@example.com"
    register = client.post("/api/v1/auth/register", json={"name": "Ana", "email": email, "password": "password123"})
    assert register.status_code == 201
    token = register.json()["access_token"]
    created = client.post("/api/v1/tasks", headers={"Authorization": f"Bearer {token}"}, json={"title": "Estudar FastAPI", "priority": "HIGH"})
    assert created.status_code == 201
    assert created.json()["title"] == "Estudar FastAPI"


def test_tasks_require_authentication():
    assert client.get("/api/v1/tasks").status_code == 401


def test_subject_persists_and_is_scoped_to_authenticated_user():
    owner_email = f"subject-owner-{uuid4().hex}@example.com"
    other_email = f"subject-other-{uuid4().hex}@example.com"
    owner = client.post("/api/v1/auth/register", json={"name": "Owner", "email": owner_email, "password": "password123"}).json()
    other = client.post("/api/v1/auth/register", json={"name": "Other", "email": other_email, "password": "password123"}).json()
    owner_headers = {"Authorization": f"Bearer {owner['access_token']}"}
    other_headers = {"Authorization": f"Bearer {other['access_token']}"}

    created = client.post("/api/v1/subjects", headers=owner_headers, json={"name": "Banco de Dados"})
    assert created.status_code == 201
    assert created.json()["name"] == "Banco de Dados"

    listed = client.get("/api/v1/subjects", headers=owner_headers)
    assert listed.status_code == 200
    assert any(item["id"] == created.json()["id"] for item in listed.json())

    assert client.get("/api/v1/subjects", headers=other_headers).json() == []


def test_subject_list_backfills_legacy_null_updated_at():
    email = f"legacy-subject-{uuid4().hex}@example.com"
    account = client.post("/api/v1/auth/register", json={"name": "Legacy", "email": email, "password": "password123"}).json()
    headers = {"Authorization": f"Bearer {account['access_token']}"}
    created = client.post("/api/v1/subjects", headers=headers, json={"name": "Legacy subject"}).json()

    with engine.begin() as connection:
        connection.execute(text("UPDATE subjects SET updated_at = NULL WHERE id = :subject_id"), {"subject_id": created["id"]})
    ensure_compatible_schema()

    listed = client.get("/api/v1/subjects", headers=headers)
    assert listed.status_code == 200
    assert listed.json()[0]["updated_at"] is not None


def test_goals_and_subject_details_survive_legacy_priority_and_related_goal():
    email = f"goal-regression-{uuid4().hex}@example.com"
    account = client.post("/api/v1/auth/register", json={"name": "Goal regression", "email": email, "password": "password123"}).json()
    headers = {"Authorization": f"Bearer {account['access_token']}"}
    subject = client.post("/api/v1/subjects", headers=headers, json={"name": "Banco de Dados"}).json()
    goal = client.post("/api/v1/goals", headers=headers, json={"title": "Estudar SQL", "target": 10, "subject_id": subject["id"]})
    assert goal.status_code == 201

    with engine.begin() as connection:
        connection.execute(text("UPDATE goals SET priority = 'MEDIUM' WHERE id = :goal_id"), {"goal_id": goal.json()["id"]})
    ensure_compatible_schema()

    listed = client.get("/api/v1/goals", headers=headers)
    assert listed.status_code == 200
    assert listed.json()[0]["priority"] == "MEDIUM"

    detail = client.get(f"/api/v1/subjects/{subject['id']}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["related_goals"][0]["title"] == "Estudar SQL"


def test_study_session_state_machine_and_single_active_session():
    email = f"session-regression-{uuid4().hex}@example.com"
    account = client.post("/api/v1/auth/register", json={"name": "Session regression", "email": email, "password": "password123"}).json()
    headers = {"Authorization": f"Bearer {account['access_token']}"}
    subject = client.post("/api/v1/subjects", headers=headers, json={"name": "Python"}).json()

    started = client.post("/api/v1/study-sessions/start", headers=headers, json={"subject_id": subject["id"]})
    assert started.status_code == 201
    session_id = started.json()["id"]
    assert started.json()["status"] == "RUNNING"
    assert client.post("/api/v1/study-sessions/start", headers=headers, json={"subject_id": subject["id"]}).status_code == 409

    paused = client.post(f"/api/v1/study-sessions/{session_id}/pause", headers=headers)
    assert paused.status_code == 200
    assert paused.json()["status"] == "PAUSED"
    resumed = client.post(f"/api/v1/study-sessions/{session_id}/resume", headers=headers)
    assert resumed.status_code == 200
    assert resumed.json()["status"] == "RUNNING"
    finished = client.post(f"/api/v1/study-sessions/{session_id}/finish", headers=headers)
    assert finished.status_code == 200
    assert finished.json()["status"] == "COMPLETED"
    assert finished.json()["duration_seconds"] >= 0
    assert client.post(f"/api/v1/study-sessions/{session_id}/finish", headers=headers).status_code == 409
