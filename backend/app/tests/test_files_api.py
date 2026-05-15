import pytest
import tempfile
import shutil
import os
from io import BytesIO
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import init_db, reset_engine
from app.core.permissions import PermissionLevel
from app.projects.models import ProjectFile
from app.core.database import get_session
from app.tools.gateway import AnalysisToolGateway
from app.workspace.manifest import ProjectManifest


@pytest.fixture
def test_db(monkeypatch):
    tmp = tempfile.mkdtemp()
    original_cwd = os.getcwd()
    db_path = Path(tmp) / "test.db"
    monkeypatch.setenv("APP_DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    os.chdir(tmp)
    reset_engine()
    init_db()
    yield
    os.chdir(original_cwd)
    reset_engine()
    shutil.rmtree(tmp)


@pytest.fixture
def client(test_db):
    return TestClient(app)


@pytest.fixture
def project(client):
    r = client.post("/api/projects", json={"name": "FileTest"})
    return r.json()


def test_upload_file(client, project):
    proj_id = project["id"]
    content = b"order_id,gmv,date\n1,100,2026-01-01"
    r = client.post(
        f"/api/projects/{proj_id}/files",
        files={"file": ("order_info.csv", BytesIO(content), "text/csv")},
        data={"role": "order_info"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["role"] == "order_info"
    assert data["checksum"].startswith("sha256:")


def test_list_files(client, project):
    proj_id = project["id"]
    client.post(
        f"/api/projects/{proj_id}/files",
        files={"file": ("test.csv", BytesIO(b"a,b\n1,2"), "text/csv")},
        data={"role": "unknown"},
    )
    r = client.get(f"/api/projects/{proj_id}/files")
    assert r.status_code == 200
    assert len(r.json()) >= 1


def test_infer_schema(client, project):
    proj_id = project["id"]
    content = b"order_id,pay_time,gmv,discount,category\n1,2026-01-01,100,10,food"
    client.post(
        f"/api/projects/{proj_id}/files",
        files={"file": ("order_info.csv", BytesIO(content), "text/csv")},
        data={"role": "order_info"},
    )
    r = client.post(f"/api/projects/{proj_id}/files/infer-schema")
    assert r.status_code == 200
    data = r.json()["data"]["files"]
    assert len(data) >= 1
    assert "columns" in data[0]


def test_apply_schema(client, project):
    proj_id = project["id"]
    content = b"order_id,gmv\n1,100"
    upload = client.post(
        f"/api/projects/{proj_id}/files",
        files={"file": ("order.csv", BytesIO(content), "text/csv")},
        data={"role": "unknown"},
    )
    file_id = upload.json()["file_id"]

    r = client.post(f"/api/projects/{proj_id}/schema/apply", json={
        "mappings": {file_id: {"order_id": "order_id", "gmv": "gmv"}}
    })
    assert r.status_code == 200
    assert r.json()["data"]["status"] == "mapped"


def test_set_data_source_path(client, project):
    proj_id = project["id"]
    source = Path.cwd() / "source_data"
    source.mkdir()

    r = client.put(f"/api/projects/{proj_id}/data-source", json={"path": str(source)})
    assert r.status_code == 200
    assert r.json()["data"]["data_source_path"] == str(source)

    get_r = client.get(f"/api/projects/{proj_id}/data-source")
    assert get_r.status_code == 200
    assert get_r.json()["data"]["data_source_path"] == str(source)


def test_ingest_data_source_imports_csv_and_refreshes_manifest(client, project):
    proj_id = project["id"]
    source = Path.cwd() / "source_data"
    source.mkdir()
    (source / "order_info.csv").write_text("order_id,gmv,date\n1,100,2026-01-01", encoding="utf-8")
    (source / "exposure_info.csv").write_text("date,exposure\n2026-01-01,10", encoding="utf-8")
    (source / "activity_timeline.csv").write_text("activity_id,payday\nA1,2026-01-01", encoding="utf-8")

    client.put(f"/api/projects/{proj_id}/data-source", json={"path": str(source)})
    discover = client.post(f"/api/projects/{proj_id}/data-source/discover", json={})
    assert discover.status_code == 200
    candidates = discover.json()["data"]["candidates"]
    assert len(candidates) == 3
    assert all(c["headers"] for c in candidates)
    assert "order_id,gmv,date" in next(c for c in candidates if c["name"] == "order_info.csv")["preview"]

    r = client.post(f"/api/projects/{proj_id}/data-source/ingest", json={
        "selected_files": [
            {"source_path": str(source / "order_info.csv"), "role": "order_info", "reason": "order headers"},
            {"source_path": str(source / "exposure_info.csv"), "role": "exposure_info", "reason": "exposure headers"},
            {"source_path": str(source / "activity_timeline.csv"), "role": "activity_timeline", "reason": "activity headers"},
        ]
    })

    assert r.status_code == 200
    data = r.json()["data"]
    assert data["imported_count"] == 3
    assert {f["role"] for f in data["imported"]} == {"order_info", "exposure_info", "activity_timeline"}

    files_r = client.get(f"/api/projects/{proj_id}/files")
    files = files_r.json()
    assert len(files) == 3
    assert all(f["current_path"].startswith("data") for f in files)

    project_r = client.get(f"/api/projects/{proj_id}")
    workspace_path = Path(project_r.json()["data"]["workspace_path"])
    manifest = ProjectManifest.load(workspace_path)
    assert manifest.current_stage == "data_uploaded"
    assert len(manifest.files) == 3
    assert (workspace_path / ".analysis" / "context_summary.md").read_text(encoding="utf-8")


def test_discover_and_ingest_protect_processed_panel_from_raw_role(client, project):
    proj_id = project["id"]
    source = Path.cwd() / "panel_source"
    source.mkdir()
    (source / "category_date_panel.csv").write_text(
        "category,date,gmv,view_uv,is_activity\nfood,2026-01-01,100,20,1",
        encoding="utf-8",
    )

    client.put(f"/api/projects/{proj_id}/data-source", json={"path": str(source)})
    discover = client.post(f"/api/projects/{proj_id}/data-source/discover", json={})

    assert discover.status_code == 200
    candidate = discover.json()["data"]["candidates"][0]
    assert candidate["role_guess"] == "category_day_panel"
    assert candidate["looks_processed_panel"] is True

    ingest = client.post(f"/api/projects/{proj_id}/data-source/ingest", json={
        "selected_files": [
            {"source_path": str(source / "category_date_panel.csv"), "role": "order_info", "reason": "mistaken raw order"}
        ]
    })

    assert ingest.status_code == 200
    data = ingest.json()["data"]
    assert data["imported_count"] == 0
    assert data["skipped"][0]["reason"] == "processed_panel_not_raw_source"


def test_data_validate_marks_ingested_files_validated(client, project):
    proj_id = project["id"]
    source = Path.cwd() / "valid_source"
    source.mkdir()
    (source / "order_info.csv").write_text(
        "order_id,user_id,category,date,gmv,discount\n1,u1,food,2026-01-01,100,10",
        encoding="utf-8",
    )
    (source / "exposure_info.csv").write_text(
        "category,date,exposure\nfood,2026-01-01,30",
        encoding="utf-8",
    )
    (source / "activity_timeline.csv").write_text(
        "category,date,payday,activity_id\nfood,2026-01-01,1,A1",
        encoding="utf-8",
    )

    client.put(f"/api/projects/{proj_id}/data-source", json={"path": str(source)})
    ingest = client.post(f"/api/projects/{proj_id}/data-source/ingest", json={
        "selected_files": [
            {"source_path": str(source / "order_info.csv"), "role": "order_info", "reason": "order headers"},
            {"source_path": str(source / "exposure_info.csv"), "role": "exposure_info", "reason": "exposure headers"},
            {"source_path": str(source / "activity_timeline.csv"), "role": "activity_timeline", "reason": "activity headers"},
        ]
    })
    assert ingest.status_code == 200

    result = AnalysisToolGateway().execute(
        tool_call_id="tc_validate_status",
        project_id=proj_id,
        action_str="data.validate",
        payload={},
        reason="validate after ingest",
        user_permission_level=PermissionLevel.SAFE_COMPUTE,
    )

    assert result.ok is True
    assert result.state_patch["current_stage"] == "data_validated"

    db = get_session()
    try:
        files = db.query(ProjectFile).filter(ProjectFile.project_id == proj_id).all()
        assert files
        assert {file.status for file in files} == {"validated"}
    finally:
        db.close()

    state = client.get(f"/api/projects/{proj_id}/state").json()["data"]
    assert state["current_stage"] == "data_validated"


def test_ingest_data_source_skips_non_csv_and_subdirectories(client, project):
    proj_id = project["id"]
    source = Path.cwd() / "mixed_source"
    source.mkdir()
    (source / "order_info.csv").write_text("order_id,gmv\n1,100", encoding="utf-8")
    (source / "notes.txt").write_text("ignore", encoding="utf-8")
    (source / "nested").mkdir()

    client.put(f"/api/projects/{proj_id}/data-source", json={"path": str(source)})
    discover = client.post(f"/api/projects/{proj_id}/data-source/discover", json={})

    assert discover.status_code == 200
    candidates = discover.json()["data"]["candidates"]
    skipped = {item["skip_reason"] for item in candidates if item["skipped"]}
    assert skipped == {"unsupported_file_type", "directory_not_scanned"}

    r = client.post(f"/api/projects/{proj_id}/data-source/ingest", json={
        "selected_files": [{"source_path": str(source / "order_info.csv"), "role": "order_info", "reason": "confirmed"}]
    })
    assert r.status_code == 200
    assert r.json()["data"]["imported_count"] == 1


def test_ingest_data_source_uses_unique_names(client, project):
    proj_id = project["id"]
    source = Path.cwd() / "source_data"
    source.mkdir()
    (source / "order_info.csv").write_text("order_id,gmv\n1,100", encoding="utf-8")

    client.put(f"/api/projects/{proj_id}/data-source", json={"path": str(source)})
    payload = {"selected_files": [{"source_path": str(source / "order_info.csv"), "role": "order_info", "reason": "confirmed"}]}
    client.post(f"/api/projects/{proj_id}/data-source/ingest", json=payload)
    r = client.post(f"/api/projects/{proj_id}/data-source/ingest", json=payload)

    assert r.status_code == 200
    files = client.get(f"/api/projects/{proj_id}/files").json()
    paths = {f["current_path"] for f in files}
    assert any(path.endswith("order_info.csv") for path in paths)
    assert any(path.endswith("order_info__2.csv") for path in paths)


def test_ingest_data_source_rejects_missing_directory(client, project):
    proj_id = project["id"]
    missing = Path.cwd() / "missing_source"

    r = client.post(f"/api/projects/{proj_id}/data-source/ingest", json={"source_path": str(missing)})

    assert r.status_code == 400
    assert "does not exist" in r.json()["detail"]


def test_ingest_requires_selected_files(client, project):
    proj_id = project["id"]
    source = Path.cwd() / "source_data"
    source.mkdir()
    client.put(f"/api/projects/{proj_id}/data-source", json={"path": str(source)})

    r = client.post(f"/api/projects/{proj_id}/data-source/ingest", json={})

    assert r.status_code == 400
    assert "selected_files is required" in r.json()["detail"]


def test_ingest_rejects_file_outside_source_directory(client, project):
    proj_id = project["id"]
    source = Path.cwd() / "source_data"
    source.mkdir()
    outside = Path.cwd() / "outside.csv"
    outside.write_text("order_id,gmv\n1,100", encoding="utf-8")
    client.put(f"/api/projects/{proj_id}/data-source", json={"path": str(source)})

    r = client.post(f"/api/projects/{proj_id}/data-source/ingest", json={
        "selected_files": [{"source_path": str(outside), "role": "order_info", "reason": "outside"}]
    })

    assert r.status_code == 400
    assert "direct child" in r.json()["detail"]
