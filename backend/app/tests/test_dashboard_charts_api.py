from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core import config
from app.core.database import init_db, reset_engine
from app.main import app
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
