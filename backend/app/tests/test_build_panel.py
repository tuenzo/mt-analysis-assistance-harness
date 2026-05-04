import pytest
import tempfile
import shutil
import os
import csv
import json
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import init_db
from app.analysis.pipelines.build_panel import build_category_day_panel, validate_files


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
def project_with_all_data(client):
    r = client.post("/api/projects", json={"name": "PanelTest"})
    project = r.json()

    workspace_path = Path(f"./workspaces/{project['id']}")
    data_dir = workspace_path / "data" / "raw"
    data_dir.mkdir(parents=True, exist_ok=True)

    order_csv = data_dir / "order_info.csv"
    with open(order_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["order_id", "user_id", "category", "date", "gmv", "discount"])
        writer.writeheader()
        writer.writerows([
            {"order_id": "o1", "user_id": "u1", "category": "food", "date": "2024-01-01", "gmv": "100", "discount": "10"},
            {"order_id": "o2", "user_id": "u2", "category": "food", "date": "2024-01-01", "gmv": "200", "discount": "20"},
            {"order_id": "o3", "user_id": "u3", "category": "electronics", "date": "2024-01-01", "gmv": "500", "discount": "50"},
        ])

    exposure_csv = data_dir / "exposure_info.csv"
    with open(exposure_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["category", "date", "exposure"])
        writer.writeheader()
        writer.writerows([
            {"category": "food", "date": "2024-01-01", "exposure": "500"},
            {"category": "electronics", "date": "2024-01-01", "exposure": "300"},
        ])

    activity_csv = data_dir / "activity_timeline.csv"
    with open(activity_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["category", "date", "payday", "activity_id"])
        writer.writeheader()
        writer.writerows([
            {"category": "food", "date": "2024-01-01", "payday": "1", "activity_id": "act1"},
            {"category": "electronics", "date": "2024-01-01", "payday": "0", "activity_id": ""},
        ])

    return project


def test_build_panel_generates_json(project_with_all_data):
    workspace_path = Path(f"./workspaces/{project_with_all_data['id']}")
    result = build_category_day_panel(project_with_all_data["id"], str(workspace_path))

    assert result.ok is True
    assert "artifacts" in result.model_dump()

    panel_path = workspace_path / "data" / "processed" / "category_day_panel.json"
    assert panel_path.exists()

    with open(panel_path, "r", encoding="utf-8") as f:
        panel_data = json.load(f)

    assert len(panel_data) > 0
    assert all(key in panel_data[0] for key in ["date", "category", "gmv", "discount", "exposure", "is_payday", "is_activity"])


def test_build_panel_validates_data_first(project_with_all_data):
    workspace_path = Path(f"./workspaces/{project_with_all_data['id']}")
    val_result = validate_files(workspace_path)
    assert val_result.ok is True


def test_build_panel_without_data(project_with_all_data):
    workspace_path = Path(f"./workspaces/{project_with_all_data['id']}")
    empty_workspace = Path(f"./workspaces/{project_with_all_data['id']}_empty")
    empty_workspace.mkdir(parents=True, exist_ok=True)
    empty_workspace.mkdir(parents=True, exist_ok=True)

    result = build_category_day_panel("nonexistent", str(empty_workspace))
    assert result.ok is False
