import pytest
import tempfile
import shutil
import os
import uuid
import json
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import init_db, get_session
from app.tools.gateway import AnalysisToolGateway, get_gateway
from app.tools.schemas import BusinessAnalysisAction, ToolResult
from app.core.permissions import PermissionLevel
from app.projects.models import ToolCall, ApprovalRequest


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
def gateway(test_db):
    return AnalysisToolGateway()


@pytest.fixture
def project(client):
    r = client.post("/api/projects", json={"name": "GatewayTest"})
    return r.json()


def test_invalid_action_returns_error(gateway, project):
    result = gateway.execute(
        tool_call_id="tc_test",
        project_id=project["id"],
        action_str="invalid.action",
        payload={},
        reason="",
    )
    assert result.ok is False
    assert result.error["code"] == "INVALID_ACTION"
    assert "Unknown action" in result.error["message"]


def test_permission_denied_returns_error(gateway, project):
    result = gateway.execute(
        tool_call_id="tc_test",
        project_id=project["id"],
        action_str="data.ingest",
        payload={},
        reason="",
        user_permission_level=PermissionLevel.READ_STATE,
    )
    assert result.ok is False
    assert result.error["code"] == "PERMISSION_DENIED"
    assert "权限不足" in result.error["message"]


def test_safe_action_executes_successfully(gateway, project):
    result = gateway.execute(
        tool_call_id="tc_test",
        project_id=project["id"],
        action_str="project.get_state",
        payload={},
        reason="",
        user_permission_level=PermissionLevel.SAFE_COMPUTE,
    )
    assert result.ok is True
    assert result.action == "project.get_state"


def test_high_risk_action_creates_approval_request(gateway, project):
    result = gateway.execute(
        tool_call_id="tc_test_high_risk",
        project_id=project["id"],
        action_str="panel.build_category_day",
        payload={"category": "food"},
        reason="build panel for analysis",
        user_permission_level=PermissionLevel.MODIFY_WORKSPACE,
    )
    assert result.ok is True
    assert "需要用户审批" in result.summary

    db = get_session()
    try:
        approval = db.query(ApprovalRequest).filter(ApprovalRequest.project_id == project["id"]).first()
        assert approval is not None
        assert approval.action == "panel.build_category_day"
        assert approval.status == "pending"
    finally:
        db.close()


def test_memory_propose_update_creates_approval_request(gateway, project):
    result = gateway.execute(
        tool_call_id="tc_test_memory",
        project_id=project["id"],
        action_str="memory.propose_update",
        payload={"content": "test memory", "scope": "project"},
        reason="update memory",
        user_permission_level=PermissionLevel.EXTERNAL_SYNC,
    )
    assert result.ok is True
    assert "需要用户审批" in result.summary

    db = get_session()
    try:
        approval = db.query(ApprovalRequest).filter(ApprovalRequest.tool_call_id == "tc_test_memory").first()
        assert approval is not None
        assert approval.risk_level == "high"
    finally:
        db.close()


def test_data_ingest_is_not_blocked_by_approval(gateway, project):
    result = gateway.execute(
        tool_call_id="tc_test_ingest",
        project_id=project["id"],
        action_str="data.ingest",
        payload={},
        reason="import local data source",
        user_permission_level=PermissionLevel.MODIFY_WORKSPACE,
    )
    assert result.ok is False

    db = get_session()
    try:
        approval = db.query(ApprovalRequest).filter(ApprovalRequest.tool_call_id == "tc_test_ingest").first()
        assert approval is None
    finally:
        db.close()


def test_tool_call_logged_to_file(gateway, project, test_db):
    result = gateway.execute(
        tool_call_id="tc_test_logged",
        project_id=project["id"],
        action_str="project.get_state",
        payload={},
        reason="",
        user_permission_level=PermissionLevel.SAFE_COMPUTE,
    )
    assert result.ok is True

    log_path = Path("./workspaces") / "tool_calls.jsonl"
    assert log_path.exists()

    with open(log_path, "r", encoding="utf-8") as f:
        logs = [json.loads(line) for line in f]
        assert any(log["tool_call_id"] == "tc_test_logged" and log["status"] == "succeeded" for log in logs)


def test_reject_approval_returns_error(gateway, project):
    result = gateway.execute(
        tool_call_id="tc_test_reject",
        project_id=project["id"],
        action_str="panel.build_category_day",
        payload={"category": "food"},
        reason="test reject",
        user_permission_level=PermissionLevel.MODIFY_WORKSPACE,
    )
    assert result.ok is True

    db = get_session()
    try:
        approval = db.query(ApprovalRequest).filter(ApprovalRequest.tool_call_id == "tc_test_reject").first()
        assert approval is not None

        resume_result = gateway.resume_from_approval(approval.id, approved=False)
        assert resume_result.ok is False
        assert "用户拒绝" in resume_result.summary
    finally:
        db.close()


def test_approve_and_execute(gateway, project, test_db):
    tool_call_id = f"tc_{uuid.uuid4().hex[:12]}"
    db = get_session()
    try:
        tc = ToolCall(
            id=tool_call_id,
            session_id="session_test",
            turn_id="turn_test",
            project_id=project["id"],
            tool_name="panel",
            action="panel.build_category_day",
            payload_json="{}",
            payload_hash="sha256:test",
            status="pending",
            permission_level=PermissionLevel.MODIFY_WORKSPACE,
            created_at="2024-01-01T00:00:00",
        )
        db.add(tc)
        db.commit()
    finally:
        db.close()

    result = gateway.execute(
        tool_call_id=tool_call_id,
        project_id=project["id"],
        action_str="panel.build_category_day",
        payload={"category": "food"},
        reason="test approve",
        user_permission_level=PermissionLevel.MODIFY_WORKSPACE,
    )
    assert result.ok is True

    db = get_session()
    try:
        approval = db.query(ApprovalRequest).filter(ApprovalRequest.tool_call_id == tool_call_id).first()
        assert approval is not None
        approval.status = "approved"
        db.commit()

        resume_result = gateway.resume_from_approval(approval.id, approved=True)
        assert resume_result.ok is False
        assert resume_result.error["code"] == "VALIDATION_FAILED"
    finally:
        db.close()


def test_approval_not_found(gateway):
    result = gateway.resume_from_approval("nonexistent_id", approved=True)
    assert result.ok is False
    assert result.error["code"] == "NOT_FOUND"
