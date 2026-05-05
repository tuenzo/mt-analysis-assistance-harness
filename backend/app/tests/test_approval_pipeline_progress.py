import json
import os
import shutil
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

from app.api.approvals import approve_tool_call
from app.core.database import get_session, init_db, reset_engine
from app.main import app
from app.projects.models import AgentEvent, ApprovalRequest, Artifact, Job, Project, Report, ToolCall
from app.tools.result_tools import result_get_latest


def test_full_pipeline_approval_emits_progress_and_persists_outputs():
    original_cwd = os.getcwd()
    tmp = tempfile.mkdtemp()
    os.chdir(tmp)
    try:
        os.environ["APP_DATABASE_URL"] = "sqlite:///./business_analysis.db"
        reset_engine()
        init_db()
        client = TestClient(app)
        project = _create_project_with_raw_data(client)

        _insert_pending_full_pipeline_approval(project["id"])

        response = approve_tool_call("approval_full_pipeline_test")

        events = response["data"]["events"]
        event_types = [event["type"] for event in events]
        assert "job_started" in event_types
        assert "job_progress" in event_types
        assert "artifact_created" in event_types
        assert "job_finished" in event_types
        assert event_types[-1] == "final_answer"

        db = get_session()
        try:
            job = db.query(Job).filter(Job.project_id == project["id"]).one()
            assert job.status == "succeeded"
            assert job.progress == 1
            steps = json.loads(job.output_json)["steps"]
            assert any(step["action"] == "analysis.run_gps_uplift" and step["ok"] for step in steps)
            assert db.query(Artifact).filter(Artifact.project_id == project["id"]).count() >= 1
            assert (
                db.query(Artifact)
                .filter(Artifact.project_id == project["id"], Artifact.title == "uplift_result.json")
                .count()
                == 1
            )
            assert db.query(Report).filter(Report.project_id == project["id"], Report.status == "ready").count() == 1
            assert db.query(AgentEvent).filter(AgentEvent.turn_id == "turn_pipeline_test", AgentEvent.type == "job_progress").count() >= 1
        finally:
            db.close()

        latest = result_get_latest(project["id"], {})
        assert latest.ok
        assert latest.artifacts[0]["available"] == ["diagnostics", "localgap", "psm_did", "uplift"]
    finally:
        os.chdir(original_cwd)
        reset_engine()
        shutil.rmtree(tmp)


def _insert_pending_full_pipeline_approval(project_id: str) -> None:
    db = get_session()
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        project.current_stage = "analysis_ready"
        tc = ToolCall(
            id="tc_full_pipeline_test",
            project_id=project_id,
            session_id="sess_pipeline_test",
            turn_id="turn_pipeline_test",
            tool_name="business_analysis",
            action="analysis.run_full_pipeline",
            payload_json="{}",
            payload_hash="sha256:test",
            status="waiting_approval",
            permission_level=3,
        )
        approval = ApprovalRequest(
            id="approval_full_pipeline_test",
            project_id=project_id,
            session_id=tc.session_id,
            turn_id=tc.turn_id,
            tool_call_id=tc.id,
            action=tc.action,
            reason="Run full pipeline",
            risk_level="high",
            payload_json=json.dumps({}),
            status="pending",
        )
        db.add(tc)
        db.add(approval)
        db.commit()
    finally:
        db.close()


def _create_project_with_raw_data(client: TestClient) -> dict:
    response = client.post("/api/projects", json={"name": "ApprovalPipelineTest"})
    project = response.json()

    raw_dir = Path(project["workspace_path"]) / "data" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    (raw_dir / "order_info.csv").write_text(
        "\n".join(
            [
                "order_id,user_id,category,date,gmv,discount",
                "o1,u1,food,2024-01-01,100,10",
                "o2,u2,food,2024-01-02,160,12",
                "o3,u3,drink,2024-01-01,80,5",
                "o4,u4,drink,2024-01-02,120,8",
            ]
        ),
        encoding="utf-8",
    )
    (raw_dir / "exposure_info.csv").write_text(
        "\n".join(
            [
                "category,date,exposure",
                "food,2024-01-01,1000",
                "food,2024-01-02,1200",
                "drink,2024-01-01,700",
                "drink,2024-01-02,900",
            ]
        ),
        encoding="utf-8",
    )
    (raw_dir / "activity_timeline.csv").write_text(
        "\n".join(
            [
                "category,date,payday,activity_id",
                "food,2024-01-01,1,act1",
                "food,2024-01-02,0,act1",
                "drink,2024-01-01,1,act1",
                "drink,2024-01-02,0,",
            ]
        ),
        encoding="utf-8",
    )
    return project
