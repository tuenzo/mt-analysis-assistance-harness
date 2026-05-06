import json
import os
import shutil
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.database import init_db, reset_engine
from app.core.permissions import PermissionLevel, action_to_permission_level
from app.main import app
from app.tools.gateway import AnalysisToolGateway
from app.tools.schemas import BusinessAnalysisAction


@pytest.fixture
def test_db():
    previous_cwd = os.getcwd()
    tmp = tempfile.mkdtemp()
    os.chdir(tmp)
    reset_engine()
    init_db()
    yield
    reset_engine()
    os.chdir(previous_cwd)
    shutil.rmtree(tmp)


@pytest.fixture
def client(test_db):
    return TestClient(app)


@pytest.fixture
def project(client):
    response = client.post("/api/projects", json={"name": "StrategyLabTest"})
    assert response.status_code == 200
    return response.json()


def test_strategy_blueprint_creates_isolated_artifact(project):
    gateway = AnalysisToolGateway()

    result = gateway.execute(
        tool_call_id="tc_strategy_blueprint",
        project_id=project["id"],
        action_str="strategy.design_blueprint",
        payload=_blueprint_payload(),
        reason="Design strategy before changing backend flow.",
        session_id="sess_strategy",
        turn_id="turn_strategy",
        user_permission_level=PermissionLevel.WRITE_ARTIFACT,
    )

    assert result.ok is True
    artifact = result.artifacts[0]
    assert artifact["type"] == "strategy_blueprint"
    assert artifact["path"].startswith(".analysis/strategy_lab/blueprints/")

    artifact_path = Path(project["workspace_path"]) / artifact["path"]
    assert artifact_path.exists()
    saved = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert saved["artifact_type"] == "strategy_blueprint"
    assert saved["content"]["objective"] == _blueprint_payload()["objective"]
    assert saved["source"]["session_id"] == "sess_strategy"
    assert saved["source"]["turn_id"] == "turn_strategy"


def test_strategy_blueprint_rejects_missing_required_fields(project):
    gateway = AnalysisToolGateway()

    result = gateway.execute(
        tool_call_id="tc_strategy_invalid",
        project_id=project["id"],
        action_str="strategy.design_blueprint",
        payload={"objective": "Missing required lists."},
        reason="Invalid payload test.",
        user_permission_level=PermissionLevel.WRITE_ARTIFACT,
    )

    assert result.ok is False
    assert result.error["code"] == "VALIDATION_FAILED"
    lab_root = Path(project["workspace_path"]) / ".analysis" / "strategy_lab"
    assert not lab_root.exists()


def test_strategy_flow_requires_stage_mapping(project):
    gateway = AnalysisToolGateway()

    result = gateway.execute(
        tool_call_id="tc_strategy_flow_invalid",
        project_id=project["id"],
        action_str="strategy.design_flow",
        payload={
            "title": "Invalid flow",
            "stages": [{"name": "No mapping"}],
        },
        reason="Invalid stage mapping test.",
        user_permission_level=PermissionLevel.WRITE_ARTIFACT,
    )

    assert result.ok is False
    assert result.error["code"] == "VALIDATION_FAILED"


def test_strategy_flow_and_backend_change_stay_workspace_local(project):
    gateway = AnalysisToolGateway()

    flow = gateway.execute(
        tool_call_id="tc_strategy_flow",
        project_id=project["id"],
        action_str="strategy.design_flow",
        payload=_flow_payload(),
        reason="Design an isolated analysis flow.",
        user_permission_level=PermissionLevel.WRITE_ARTIFACT,
    )
    proposal = gateway.execute(
        tool_call_id="tc_strategy_backend_change",
        project_id=project["id"],
        action_str="strategy.propose_backend_change",
        payload=_backend_change_payload(),
        reason="Describe required backend framework change.",
        user_permission_level=PermissionLevel.WRITE_ARTIFACT,
    )

    assert flow.ok is True
    assert proposal.ok is True
    for result in (flow, proposal):
        artifact_path = (Path(project["workspace_path"]) / result.artifacts[0]["path"]).resolve()
        artifact_path.relative_to(Path(project["workspace_path"]).resolve())
        assert ".analysis" in artifact_path.parts
        assert "strategy_lab" in artifact_path.parts

    backend_source = Path(__file__).parents[1] / "tools" / "strategy_tools.py"
    assert backend_source.exists()


def test_strategy_actions_have_write_artifact_permission():
    assert action_to_permission_level(BusinessAnalysisAction.STRATEGY_DESIGN_BLUEPRINT) == PermissionLevel.WRITE_ARTIFACT
    assert action_to_permission_level(BusinessAnalysisAction.STRATEGY_DESIGN_FLOW) == PermissionLevel.WRITE_ARTIFACT
    assert (
        action_to_permission_level(BusinessAnalysisAction.STRATEGY_PROPOSE_BACKEND_CHANGE)
        == PermissionLevel.WRITE_ARTIFACT
    )


def _blueprint_payload() -> dict:
    return {
        "strategy_id": "promo_strategy",
        "version": "v1",
        "title": "Promotion analysis strategy",
        "objective": "Determine which promotion strategy is directionally worth scaling.",
        "decision_questions": ["Which categories have incremental impact?"],
        "assumptions": ["Uploaded files are the project fact source."],
        "success_criteria": ["Every recommendation cites an artifact path."],
        "candidate_methods": ["diagnostics", "LocalGap"],
    }


def _flow_payload() -> dict:
    return {
        "flow_id": "promo_flow",
        "version": "v1",
        "title": "Promotion strategy flow",
        "stages": [
            {
                "name": "Inspect state",
                "purpose": "Check data readiness.",
                "action": "project.get_state",
                "outputs": ["project status"],
            },
            {
                "name": "Profile selection",
                "purpose": "Make strategy profiles executable later.",
                "proposed_backend_change": "Add selectable strategy profile configs.",
                "outputs": ["backend change proposal"],
            },
        ],
    }


def _backend_change_payload() -> dict:
    return {
        "proposal_id": "strategy_profiles",
        "version": "v1",
        "title": "Strategy profile execution support",
        "objective": "Allow reviewed strategy flows to become selectable pipeline profiles.",
        "affected_modules": ["backend/app/jobs", "backend/app/tools"],
        "desired_behavior": ["Register approved strategy profiles as explicit backend configs."],
        "risks": ["Generated strategies may drift from implemented pipeline capabilities."],
        "source_write_instructions": ["Do not directly write source in strategy lab actions."],
    }
