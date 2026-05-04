import pytest
import tempfile
import shutil
import os
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import init_db, get_engine, Base


@pytest.fixture
def test_db():
    tmp = tempfile.mkdtemp()
    os.chdir(tmp)
    init_db()
    yield
    os.chdir("..")
    shutil.rmtree(tmp)


@pytest.fixture
def client(test_db):
    return TestClient(app)


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_create_project(client):
    r = client.post("/api/projects", json={"name": "Test Project", "domain": "promo_analysis"})
    assert r.status_code == 200
    data = r.json()
    assert data["id"].startswith("proj_")
    assert data["name"] == "Test Project"
    assert data["status"] == "created"


def test_get_project_state(client):
    r = client.post("/api/projects", json={"name": "State Test"})
    proj_id = r.json()["id"]
    r2 = client.get(f"/api/projects/{proj_id}/state")
    assert r2.status_code == 200
    state = r2.json()["data"]
    assert state["project"]["id"] == proj_id
    assert "next_actions" in state


def test_list_projects(client):
    client.post("/api/projects", json={"name": "P1"})
    client.post("/api/projects", json={"name": "P2"})
    r = client.get("/api/projects")
    assert r.status_code == 200
    data = r.json()["data"]
    assert len(data) >= 2


def test_project_workspace_created(client):
    r = client.post("/api/projects", json={"name": "Workspace Test"})
    proj_id = r.json()["id"]
    workspace_path = r.json()["workspace_path"]
    assert Path(workspace_path).exists()
    assert (Path(workspace_path) / ".analysis" / "project_manifest.json").exists()
