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
from app.analysis.pipelines.diagnostics import run_diagnostics
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
    r = client.post("/api/projects", json={"name": "DiagnosticsTest"})
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


def test_diagnostics_produces_trend_data(project_with_panel):
    workspace_path = Path(f"./workspaces/{project_with_panel['id']}")
    result = run_diagnostics(project_with_panel["id"], str(workspace_path))

    assert result.ok is True
    assert "gmv_trend" in result.summary or "诊断完成" in result.summary
    output_path = workspace_path / ".analysis" / "diagnostics_result.json"
    assert output_path.exists()

    import json

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["method_status"] in {"implemented", "limited"}
    assert "weekday_context" in payload
    assert "quality" in payload
    assert "warnings" in payload


def test_diagnostics_without_panel(client):
    r = client.post("/api/projects", json={"name": "NoPanelDiagTest"})
    project = r.json()

    workspace_path = Path(f"./workspaces/{project['id']}")
    result = run_diagnostics(project["id"], str(workspace_path))

    assert result.ok is False
    assert "PANEL_NOT_FOUND" in str(result.error)
