import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core import config
from app.core.database import get_session, init_db, reset_engine
from app.main import app
from app.projects.models import Artifact
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


def test_read_registered_json_artifact_content(isolated_backend):
    client = TestClient(app)
    project = ProjectService().create_project("Artifact Content Test", is_test=True)
    workspace = Path(project.workspace_path)
    chart_path = workspace / "artifacts" / "charts" / "gmv_trend.json"
    chart_path.parent.mkdir(parents=True, exist_ok=True)
    chart_payload = {
        "type": "line",
        "title": "GMV trend",
        "x": ["2026-04-01", "2026-04-02"],
        "y": [120.5, 188.0],
        "metadata": {"chart_type": "gmv_trend"},
    }
    chart_path.write_text(json.dumps(chart_payload, ensure_ascii=False), encoding="utf-8")
    _insert_artifact(project.id, "art_chart_test", "chart", "gmv_trend.json", "artifacts/charts/gmv_trend.json")

    response = client.get(f"/api/projects/{project.id}/artifacts/art_chart_test/content")

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["encoding"] == "json"
    assert payload["content_type"] == "application/json"
    assert payload["artifact"]["path"] == "artifacts/charts/gmv_trend.json"
    assert payload["data"]["type"] == "line"
    assert payload["data"]["y"] == [120.5, 188.0]


def test_read_artifact_by_path_rejects_workspace_escape(isolated_backend):
    client = TestClient(app)
    project = ProjectService().create_project("Artifact Escape Test", is_test=True)

    response = client.get(f"/api/projects/{project.id}/artifacts/content", params={"path": "../outside.json"})

    assert response.status_code == 400
    assert "workspace" in response.json()["detail"]


def _insert_artifact(project_id: str, artifact_id: str, artifact_type: str, title: str, path: str) -> None:
    db = get_session()
    try:
        db.add(
            Artifact(
                id=artifact_id,
                project_id=project_id,
                type=artifact_type,
                title=title,
                path=path,
                mime_type="application/json",
                metadata_json=json.dumps({"method_status": "chart_data_rendered"}),
                created_at="2026-05-06T12:00:00",
            )
        )
        db.commit()
    finally:
        db.close()
