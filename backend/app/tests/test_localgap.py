import pytest
import tempfile
import shutil
import os
import csv
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import init_db
from app.analysis.pipelines.localgap import run_localgap
from app.analysis.pipelines.build_panel import build_category_day_panel


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
def project_with_panel(client):
    r = client.post("/api/projects", json={"name": "LocalGapTest"})
    project = r.json()

    workspace_path = Path(f"./workspaces/{project['id']}")
    data_dir = workspace_path / "data" / "raw"
    data_dir.mkdir(parents=True, exist_ok=True)

    order_csv = data_dir / "order_info.csv"
    with open(order_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["order_id", "user_id", "category", "date", "gmv", "discount"])
        writer.writeheader()
        for i in range(10):
            writer.writerow({
                "order_id": f"o{i}", "user_id": f"u{i}",
                "category": "food" if i < 5 else "electronics",
                "date": f"2024-01-{i+1:02d}", "gmv": str(100 * (i + 1)), "discount": str(10 * (i + 1))
            })

    exposure_csv = data_dir / "exposure_info.csv"
    with open(exposure_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["category", "date", "exposure"])
        writer.writeheader()
        for i in range(10):
            writer.writerow({"category": "food" if i < 5 else "electronics", "date": f"2024-01-{i+1:02d}", "exposure": "500"})

    activity_csv = data_dir / "activity_timeline.csv"
    with open(activity_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["category", "date", "payday", "activity_id"])
        writer.writeheader()
        for i in range(10):
            writer.writerow({
                "category": "food" if i < 5 else "electronics",
                "date": f"2024-01-{i+1:02d}",
                "payday": "1" if i == 5 else "0",
                "activity_id": f"act{i}" if i < 3 else ""
            })

    build_category_day_panel(project["id"], str(workspace_path))
    return project


def test_localgap_produces_decomposition(project_with_panel):
    workspace_path = Path(f"./workspaces/{project_with_panel['id']}")
    result = run_localgap(project_with_panel["id"], str(workspace_path))

    assert result.ok is True
    assert "artifacts" in result.model_dump()


def test_localgap_without_panel(client):
    r = client.post("/api/projects", json={"name": "NoPanelLGTest"})
    project = r.json()

    workspace_path = Path(f"./workspaces/{project['id']}")
    result = run_localgap(project["id"], str(workspace_path))

    assert result.ok is False
    assert "PANEL_NOT_FOUND" in str(result.error)
