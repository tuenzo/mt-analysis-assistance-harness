import pytest
import tempfile
import shutil
import os
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


@pytest.fixture
def project(client):
    r = client.post("/api/projects", json={"name": "AgentTest"})
    return r.json()


def test_send_message_returns_turn_id(client, project):
    r = client.post("/api/agent/messages", json={
        "project_id": project["id"],
        "message": "你好",
        "ui_context": {"active_view": "agent_command_center"}
    })
    assert r.status_code == 200
    data = r.json()
    assert "turn_id" in data
    assert "session_id" in data
    assert data["status"] == "running"
    assert "/api/agent/sessions/" in data["event_stream_url"]


def test_mock_adapter_conversation(client, project):
    r = client.post("/api/agent/messages", json={
        "project_id": project["id"],
        "message": "今天天气怎么样",
    })
    assert r.status_code == 200


def test_mock_adapter_status_query(client, project):
    r = client.post("/api/agent/messages", json={
        "project_id": project["id"],
        "message": "当前项目状态",
    })
    assert r.status_code == 200


def test_mock_adapter_analysis_request(client, project):
    r = client.post("/api/agent/messages", json={
        "project_id": project["id"],
        "message": "帮我分析这批数据",
    })
    assert r.status_code == 200


def test_mock_full_pipeline_request_creates_approval_not_data_ingest(client, project):
    from app.agent.message_runtime import get_message_runtime

    r = client.post("/api/agent/messages", json={
        "project_id": project["id"],
        "message": "Run the full promotion analysis pipeline.",
    })
    assert r.status_code == 200
    data = r.json()

    events = get_message_runtime().get_events(data["session_id"], data["turn_id"])
    actions = [event.get("action") for event in events if event.get("tool") == "business_analysis"]

    assert "analysis.run_full_pipeline" in actions
    assert "data.discover_source_files" not in actions
    approval_events = [event for event in events if event["type"] == "approval_requested"]
    assert approval_events
    assert approval_events[0]["reason"] == "Run the approved end-to-end promotion analysis pipeline and generate outputs."


def test_mock_dashboard_image_request_calls_render_dashboard(client, project):
    from app.agent.message_runtime import get_message_runtime

    r = client.post("/api/agent/messages", json={
        "project_id": project["id"],
        "message": "请重新生成看板图片",
    })
    assert r.status_code == 200
    data = r.json()

    events = get_message_runtime().get_events(data["session_id"], data["turn_id"])
    actions = [event.get("action") for event in events if event.get("tool") == "business_analysis"]

    assert "chart.render_dashboard" in actions


def test_interrupt_session(client, project):
    r = client.post("/api/agent/messages", json={
        "project_id": project["id"],
        "message": "帮我分析",
    })
    session_id = r.json()["session_id"]

    r2 = client.post(f"/api/agent/sessions/{session_id}/interrupt")
    assert r2.status_code == 200
    assert r2.json()["ok"] is True


def test_get_session(client, project):
    r = client.post("/api/agent/messages", json={
        "project_id": project["id"],
        "message": "hello",
    })
    session_id = r.json()["session_id"]

    r2 = client.get(f"/api/agent/sessions/{session_id}")
    assert r2.status_code == 200
    data = r2.json()["data"]
    assert data["id"] == session_id
    assert data["runtime_provider"] == "mock"


def test_session_messages_include_runtime_final_answer(client, project):
    r = client.post("/api/agent/messages", json={
        "project_id": project["id"],
        "message": "hello",
    })
    assert r.status_code == 200
    data = r.json()

    r2 = client.get(f"/api/agent/sessions/{data['session_id']}/messages")
    assert r2.status_code == 200
    messages = r2.json()["data"]
    assert messages[-1]["role"] == "assistant"
    assert "load files" in messages[-1]["content"]


def test_project_sessions_list(client, project):
    r = client.post("/api/agent/messages", json={"project_id": project["id"], "message": "hi"})
    session_id = r.json()["session_id"]

    r2 = client.get(f"/api/projects/{project['id']}/sessions")
    assert r2.status_code == 200
    data = r2.json()["data"]
    assert any(s["id"] == session_id for s in data)
