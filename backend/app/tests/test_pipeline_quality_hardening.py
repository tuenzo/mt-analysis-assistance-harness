import json
from pathlib import Path

import pytest

from app.core import config, database
from app.core.database import get_session, init_db, reset_engine
from app.jobs.pipeline_runner import run_approved_full_pipeline
from app.projects.models import Artifact, Job, Report
from app.projects.service import ProjectService


@pytest.fixture
def isolated_backend(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    workspace_root = tmp_path / "workspaces"
    monkeypatch.setenv("APP_DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    monkeypatch.setenv("APP_TEST_MODE", "true")
    monkeypatch.setattr(config.settings, "workspace_root", workspace_root)
    reset_engine()
    init_db()
    yield workspace_root
    reset_engine()


def test_default_database_url_is_stable_across_working_directories(monkeypatch):
    monkeypatch.delenv("APP_DATABASE_URL", raising=False)
    monkeypatch.chdir(database.PROJECT_ROOT)
    from_root = database._resolve_database_url()
    monkeypatch.chdir(database.BACKEND_ROOT)
    from_backend = database._resolve_database_url()

    assert from_root == from_backend
    assert from_root.endswith("/business_analysis.db")
    assert Path(from_root.removeprefix("sqlite:///")).parent == database.PROJECT_ROOT


def test_full_pipeline_stops_after_validation_failure(isolated_backend):
    project = ProjectService().create_project("Pipeline Fail Fast Validation", is_test=True)
    service = ProjectService()
    service.upload_file(project.id, b"order_id,user_id,category,date\n1,u1,food,2026-01-01", "order_info.csv", "order_info")
    service.upload_file(project.id, b"category,date,exposure\nfood,2026-01-01,1000", "exposure_info.csv", "exposure_info")
    service.upload_file(project.id, b"category,date,payday,activity_id\nfood,2026-01-01,1,A1", "activity_timeline.csv", "activity_timeline")

    db = get_session()
    try:
        result, events = run_approved_full_pipeline(
            db,
            project_id=project.id,
            session_id="sess_fail_fast",
            turn_id="turn_fail_fast",
            tool_call=None,
            payload={},
        )
        job = db.query(Job).filter(Job.project_id == project.id).one()
        steps = json.loads(job.output_json)["steps"]
        artifact_count = db.query(Artifact).filter(Artifact.project_id == project.id).count()
        report_count = db.query(Report).filter(Report.project_id == project.id).count()
    finally:
        db.close()

    assert result.ok is False
    assert [step["action"] for step in steps] == ["quality.audit_lineage", "data.validate"]
    assert steps[-1]["ok"] is False
    assert not any(event.get("action") == "panel.build_category_day" for event in events)
    assert artifact_count == 0
    assert report_count == 0
