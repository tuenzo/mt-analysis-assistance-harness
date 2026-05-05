import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core import config
from app.core.database import get_session, init_db, reset_engine
from app.demo.seed import DemoSeedService, seed_demo_if_enabled
from app.main import app
from app.projects.models import AgentTurn, AnalysisSession, Artifact, Project, ProjectFile, Report


@pytest.fixture
def isolated_demo_env(tmp_path, monkeypatch):
    db_path = tmp_path / "demo.db"
    workspace_root = tmp_path / "workspaces"

    monkeypatch.setenv("APP_DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    monkeypatch.setenv("APP_WORKSPACE_ROOT", str(workspace_root))
    monkeypatch.setenv("APP_DEMO_PROJECT_ID", "proj_demo_test")
    monkeypatch.delenv("APP_DEMO_MODE", raising=False)
    monkeypatch.setattr(config.settings, "workspace_root", workspace_root)

    reset_engine()
    init_db()
    yield workspace_root
    reset_engine()


@pytest.fixture
def client(isolated_demo_env):
    return TestClient(app)


def test_demo_status_disabled_does_not_seed(client):
    response = client.get("/api/demo/status")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["enabled"] is False

    db = get_session()
    try:
        assert db.query(Project).filter(Project.id == "proj_demo_test").first() is None
    finally:
        db.close()


def test_demo_seed_enabled_creates_fixed_project(isolated_demo_env, monkeypatch, client):
    monkeypatch.setenv("APP_DEMO_MODE", "true")
    result = seed_demo_if_enabled()
    assert result["project_id"] == "proj_demo_test"

    response = client.get("/api/demo/status")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["enabled"] is True
    assert data["project_id"] == "proj_demo_test"
    assert data["session_id"] == "demo_session_keemart"

    db = get_session()
    try:
        project = db.query(Project).filter(Project.id == "proj_demo_test").one()
        assert project.is_test == 1
        assert project.current_stage == "report_ready"
        assert db.query(ProjectFile).filter(ProjectFile.project_id == project.id).count() == 4
        assert db.query(Artifact).filter(Artifact.project_id == project.id).count() >= 2
        assert db.query(Report).filter(Report.project_id == project.id).count() == 1
        session = db.query(AnalysisSession).filter(AnalysisSession.project_id == project.id).one()
        assert session.external_session_id is None
    finally:
        db.close()


def test_demo_seed_resets_existing_project(isolated_demo_env, monkeypatch):
    monkeypatch.setenv("APP_DEMO_MODE", "true")
    DemoSeedService().seed(reset=True)

    db = get_session()
    try:
        db.add(AgentTurn(
            id="temporary_demo_turn",
            session_id="demo_session_keemart",
            project_id="proj_demo_test",
            user_message="temp",
            assistant_message="temp",
            status="completed",
        ))
        db.commit()
        assert db.query(AgentTurn).filter(AgentTurn.id == "temporary_demo_turn").count() == 1
    finally:
        db.close()

    DemoSeedService().seed(reset=True)

    db = get_session()
    try:
        assert db.query(AgentTurn).filter(AgentTurn.id == "temporary_demo_turn").count() == 0
        assert db.query(Project).filter(Project.id == "proj_demo_test").count() == 1
        assert db.query(AnalysisSession).filter(AnalysisSession.project_id == "proj_demo_test").count() == 1
    finally:
        db.close()


def test_demo_seed_writes_workspace_manifest_context_latest_result(isolated_demo_env, monkeypatch):
    monkeypatch.setenv("APP_DEMO_MODE", "true")
    DemoSeedService().seed(reset=True)

    workspace = Path(isolated_demo_env) / "projects" / "proj_demo_test"
    assert (workspace / "data" / "raw" / "order_info.csv").exists()
    assert (workspace / "reports" / "report.md").exists()
    assert (workspace / ".analysis" / "context_summary.md").exists()
    latest = json.loads((workspace / ".analysis" / "latest_result.json").read_text(encoding="utf-8"))
    manifest = json.loads((workspace / ".analysis" / "project_manifest.json").read_text(encoding="utf-8"))

    assert latest["demo"] is True
    assert manifest["current_stage"] == "report_ready"
    assert len(manifest["files"]) == 4
    assert len(manifest["derived_assets"]) >= 2


def test_demo_session_messages_returns_seeded_history(isolated_demo_env, monkeypatch, client):
    monkeypatch.setenv("APP_DEMO_MODE", "true")
    DemoSeedService().seed(reset=True)

    response = client.get("/api/agent/sessions/demo_session_keemart/messages")
    assert response.status_code == 200
    messages = response.json()["data"]
    assert len(messages) == 4
    assert messages[0]["role"] == "user"
    assert "数据准备好" in messages[0]["content"]
    assert messages[-1]["role"] == "assistant"


def test_demo_latest_report_is_readable(isolated_demo_env, monkeypatch, client):
    monkeypatch.setenv("APP_DEMO_MODE", "true")
    DemoSeedService().seed(reset=True)

    response = client.get("/api/projects/proj_demo_test/reports/latest")
    assert response.status_code == 200
    data = response.json()["data"]
    assert "Keemart" in data["content"]
    assert data["path"].endswith("report.md")
