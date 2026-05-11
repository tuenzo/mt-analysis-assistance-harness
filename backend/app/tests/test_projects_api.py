import pytest
import tempfile
import shutil
import os
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import init_db, get_engine, Base, get_session
from app.projects.models import (
    AgentEvent,
    AgentTurn,
    AnalysisSession,
    ApprovalRequest,
    Artifact,
    Job,
    MemoryCandidate,
    Report,
    ToolCall,
)


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


def test_agent_runtime_metadata(client):
    r = client.get("/api/agent/runtime")
    assert r.status_code == 200
    payload = r.json()
    assert payload["ok"] is True
    assert payload["data"]["runtime_provider"]
    assert payload["data"]["model"]


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


def test_test_projects_only_load_in_test_mode(client, monkeypatch):
    visible = client.post("/api/projects", json={"name": "Visible Project"}).json()
    hidden = client.post("/api/projects", json={"name": "Hidden Test Project", "is_test": True}).json()

    r = client.get("/api/projects")
    assert r.status_code == 200
    project_ids = {p["id"] for p in r.json()["data"]}
    assert visible["id"] in project_ids
    assert hidden["id"] not in project_ids

    r_hidden = client.get(f"/api/projects/{hidden['id']}")
    assert r_hidden.status_code == 404

    monkeypatch.setenv("APP_TEST_MODE", "true")
    r_test_mode = client.get("/api/projects")
    assert r_test_mode.status_code == 200
    test_mode_ids = {p["id"] for p in r_test_mode.json()["data"]}
    assert hidden["id"] in test_mode_ids

    r_hidden_test_mode = client.get(f"/api/projects/{hidden['id']}")
    assert r_hidden_test_mode.status_code == 200


def test_project_workspace_created(client):
    r = client.post("/api/projects", json={"name": "Workspace Test"})
    proj_id = r.json()["id"]
    workspace_path = r.json()["workspace_path"]
    assert Path(workspace_path).exists()
    assert (Path(workspace_path) / ".analysis" / "project_manifest.json").exists()


def test_delete_project_removes_record_and_workspace(client):
    r = client.post("/api/projects", json={"name": "Delete Me"})
    proj_id = r.json()["id"]
    workspace_path = Path(r.json()["workspace_path"])
    assert workspace_path.exists()

    delete_response = client.delete(f"/api/projects/{proj_id}")

    assert delete_response.status_code == 200
    payload = delete_response.json()["data"]
    assert payload["id"] == proj_id
    assert payload["workspace_deleted"] is True
    assert not workspace_path.exists()
    assert client.get(f"/api/projects/{proj_id}").status_code == 404


def test_delete_project_removes_related_records(client):
    r = client.post("/api/projects", json={"name": "Delete With History"})
    proj_id = r.json()["id"]

    db = get_session()
    try:
        session = AnalysisSession(id="sess_delete", project_id=proj_id)
        turn = AgentTurn(id="turn_delete", session_id=session.id, project_id=proj_id, user_message="run analysis")
        tool_call = ToolCall(
            id="tool_delete",
            session_id=session.id,
            turn_id=turn.id,
            project_id=proj_id,
            tool_name="business_analysis",
            action="analysis.run_diagnostics",
            payload_json="{}",
            payload_hash="hash",
        )
        job = Job(id="job_delete", project_id=proj_id, session_id=session.id, turn_id=turn.id, tool_call_id=tool_call.id, action="analysis.run_diagnostics")
        artifact = Artifact(id="artifact_delete", project_id=proj_id, job_id=job.id, tool_call_id=tool_call.id, type="table", title="Diagnostics", path="artifacts/diagnostics.json")
        report = Report(id="report_delete", project_id=proj_id, job_id=job.id, status="draft")
        memory = MemoryCandidate(id="memory_delete", project_id=proj_id, session_id=session.id, turn_id=turn.id, scope="project", content="Keep this")
        approval = ApprovalRequest(id="approval_delete", project_id=proj_id, session_id=session.id, turn_id=turn.id, tool_call_id=tool_call.id, action="analysis.run_full_pipeline", risk_level="high", payload_json="{}")
        event = AgentEvent(id="event_delete", session_id=session.id, turn_id=turn.id, project_id=proj_id, type="tool_call_started", payload_json="{}")
        db.add_all([session, turn, tool_call, job, artifact, report, memory, approval, event])
        db.commit()
    finally:
        db.close()

    delete_response = client.delete(f"/api/projects/{proj_id}")

    assert delete_response.status_code == 200
    db = get_session()
    try:
        for model in (AnalysisSession, AgentTurn, ToolCall, Job, Artifact, Report, MemoryCandidate, ApprovalRequest, AgentEvent):
            assert db.query(model).filter(model.project_id == proj_id).count() == 0
    finally:
        db.close()


def test_delete_hidden_test_project_by_id_removes_record_and_workspace(client):
    r = client.post("/api/projects", json={"name": "Delete Hidden Test", "is_test": True})
    proj_id = r.json()["id"]
    workspace_path = Path(r.json()["workspace_path"])

    assert client.get(f"/api/projects/{proj_id}").status_code == 404

    delete_response = client.delete(f"/api/projects/{proj_id}")

    assert delete_response.status_code == 200
    assert delete_response.json()["data"]["workspace_deleted"] is True
    assert not workspace_path.exists()


def test_delete_missing_project_returns_404(client):
    response = client.delete("/api/projects/proj_missing")

    assert response.status_code == 404
