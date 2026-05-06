from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.analysis.dashboard_chart_renderer import DEFAULT_DASHBOARD_CHART_IDS
from app.core import config
from app.core.database import get_session, init_db, reset_engine
from app.core.permissions import PermissionLevel
from app.main import app
from app.projects.models import Artifact
from app.projects.service import ProjectService
from app.tools.chart_tools import chart_render_dashboard
from app.tools.gateway import AnalysisToolGateway


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


def test_dashboard_chart_endpoint_renders_png(isolated_backend):
    client = TestClient(app)
    project = ProjectService().create_project("Dashboard Chart Test", is_test=True)

    response = client.get(f"/api/projects/{project.id}/dashboard-charts/pareto.png")

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content.startswith(b"\x89PNG\r\n\x1a\n")
    assert (Path(project.workspace_path) / "artifacts" / "charts" / "dashboard" / "pareto.png").exists()


def test_dashboard_period_overview_chart_endpoint_renders_png(isolated_backend):
    client = TestClient(app)
    project = ProjectService().create_project("Dashboard Chart Test", is_test=True)

    response = client.get(f"/api/projects/{project.id}/dashboard-charts/period_overview.png")

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content.startswith(b"\x89PNG\r\n\x1a\n")
    assert (Path(project.workspace_path) / "artifacts" / "charts" / "dashboard" / "period_overview.png").exists()


def test_dashboard_chart_endpoint_rejects_unknown_chart(isolated_backend):
    client = TestClient(app)
    project = ProjectService().create_project("Dashboard Chart Test", is_test=True)

    response = client.get(f"/api/projects/{project.id}/dashboard-charts/not_real.png")

    assert response.status_code == 404


def test_dashboard_chart_tool_renders_all_png_artifacts(isolated_backend):
    project = ProjectService().create_project("Dashboard Chart Tool Test", is_test=True)

    result = chart_render_dashboard(project.id, {"charts": "all"})

    assert result.ok is True
    assert result.action == "chart.render_dashboard"
    assert len(result.artifacts) == len(DEFAULT_DASHBOARD_CHART_IDS)
    for artifact in result.artifacts:
        assert artifact["type"] == "dashboard_chart"
        assert artifact["mime_type"] == "image/png"
        chart_path = Path(project.workspace_path) / artifact["path"]
        assert chart_path.exists()
        assert chart_path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")


def test_dashboard_chart_tool_is_exposed_through_gateway_and_persists_artifact(isolated_backend):
    project = ProjectService().create_project("Dashboard Chart Gateway Test", is_test=True)

    result = AnalysisToolGateway().execute(
        tool_call_id="tc_dashboard_chart_test",
        project_id=project.id,
        action_str="chart.render_dashboard",
        payload={"chart_ids": ["pareto"]},
        reason="regenerate dashboard images",
        user_permission_level=PermissionLevel.WRITE_ARTIFACT,
    )

    assert result.ok is True
    assert [artifact["chart_id"] for artifact in result.artifacts] == ["pareto"]
    db = get_session()
    try:
        artifact = (
            db.query(Artifact)
            .filter(Artifact.project_id == project.id, Artifact.type == "dashboard_chart")
            .one()
        )
        assert artifact.path == "artifacts/charts/dashboard/pareto.png"
        assert artifact.mime_type == "image/png"
    finally:
        db.close()
