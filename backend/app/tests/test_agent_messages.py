import pytest
import tempfile
import shutil
import os
import time
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import get_session, init_db, reset_engine
from app.projects.models import AgentEvent, AgentTurn, AnalysisSession


@pytest.fixture
def test_db():
    import app.agent.message_runtime as message_runtime

    old_cwd = os.getcwd()
    tmp = tempfile.mkdtemp()
    os.chdir(tmp)
    reset_engine()
    message_runtime._message_runtime = None
    init_db()
    try:
        yield
    finally:
        if message_runtime._message_runtime is not None:
            message_runtime._message_runtime.wait_for_all_turns()
        message_runtime._message_runtime = None
        reset_engine()
        os.chdir(old_cwd)
        shutil.rmtree(tmp)


@pytest.fixture
def client(test_db):
    return TestClient(app)


@pytest.fixture
def project(client):
    r = client.post("/api/projects", json={"name": "AgentTest"})
    return r.json()


def wait_for_runtime_events(session_id, turn_id, predicate, timeout=3.0):
    from app.agent.message_runtime import get_message_runtime

    runtime = get_message_runtime()
    deadline = time.time() + timeout
    collected = []
    while time.time() < deadline:
        events = runtime.get_events(session_id, turn_id)
        collected.extend(events)
        if predicate(collected):
            return collected
        time.sleep(0.05)
    return collected


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
    r = client.post("/api/agent/messages", json={
        "project_id": project["id"],
        "message": "Run the full promotion analysis pipeline.",
    })
    assert r.status_code == 200
    data = r.json()

    events = wait_for_runtime_events(
        data["session_id"],
        data["turn_id"],
        lambda collected: any(event.get("type") == "approval_requested" for event in collected),
    )
    actions = [event.get("action") for event in events if event.get("tool") == "business_analysis"]

    assert "analysis.run_full_pipeline" in actions
    assert "data.discover_source_files" not in actions
    approval_events = [event for event in events if event["type"] == "approval_requested"]
    assert approval_events
    assert approval_events[0]["reason"] == "Run the approved end-to-end promotion analysis pipeline and generate outputs."


def test_mock_dashboard_image_request_calls_render_dashboard(client, project):
    r = client.post("/api/agent/messages", json={
        "project_id": project["id"],
        "message": "请重新生成看板图片",
    })
    assert r.status_code == 200
    data = r.json()

    events = wait_for_runtime_events(
        data["session_id"],
        data["turn_id"],
        lambda collected: any(event.get("action") == "chart.render_dashboard" for event in collected),
    )
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

    wait_for_runtime_events(
        data["session_id"],
        data["turn_id"],
        lambda collected: any(event.get("type") == "final_answer" for event in collected),
    )

    r2 = client.get(f"/api/agent/sessions/{data['session_id']}/messages")
    assert r2.status_code == 200
    messages = r2.json()["data"]
    assert messages[-1]["role"] == "assistant"
    assert "load files" in messages[-1]["content"]


def test_project_sessions_list(client, project):
    r1 = client.post("/api/agent/messages", json={"project_id": project["id"], "message": "hi"})
    first_session_id = r1.json()["session_id"]
    wait_for_runtime_events(
        first_session_id,
        r1.json()["turn_id"],
        lambda collected: any(event.get("type") == "final_answer" for event in collected),
    )
    time.sleep(0.02)
    r2 = client.post("/api/agent/messages", json={"project_id": project["id"], "message": "second hi"})
    second_session_id = r2.json()["session_id"]
    wait_for_runtime_events(
        second_session_id,
        r2.json()["turn_id"],
        lambda collected: any(event.get("type") == "final_answer" for event in collected),
    )

    response = client.get(f"/api/projects/{project['id']}/sessions")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data[0]["id"] == second_session_id
    assert data[0]["project_id"] == project["id"]
    assert data[0]["message_count"] >= 1
    assert data[0]["last_message"]
    assert data[0]["last_activity_at"]
    assert any(s["id"] == first_session_id for s in data)


def test_delete_session_removes_thread_history(client, project):
    r = client.post("/api/agent/messages", json={"project_id": project["id"], "message": "delete this thread"})
    data = r.json()
    session_id = data["session_id"]

    wait_for_runtime_events(
        session_id,
        data["turn_id"],
        lambda collected: any(event.get("type") == "final_answer" for event in collected),
    )

    delete_response = client.delete(f"/api/agent/sessions/{session_id}")

    assert delete_response.status_code == 200
    assert delete_response.json()["data"]["deleted"] is True
    assert client.get(f"/api/agent/sessions/{session_id}").status_code == 404
    assert client.get(f"/api/agent/sessions/{session_id}/messages").status_code == 404

    sessions_response = client.get(f"/api/projects/{project['id']}/sessions")
    assert all(session["id"] != session_id for session in sessions_response.json()["data"])

    db = get_session()
    try:
        assert db.query(AnalysisSession).filter(AnalysisSession.id == session_id).count() == 0
        assert db.query(AgentTurn).filter(AgentTurn.session_id == session_id).count() == 0
        assert db.query(AgentEvent).filter(AgentEvent.session_id == session_id).count() == 0
    finally:
        db.close()


def test_delete_missing_session_returns_404(client):
    response = client.delete("/api/agent/sessions/session_missing")

    assert response.status_code == 404
