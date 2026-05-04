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
from app.analysis.pipelines.build_panel import build_category_day_panel
from app.analysis.pipelines.diagnostics import run_diagnostics
from app.reports.renderer import render_report


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
def project_with_results(client):
    r = client.post("/api/projects", json={"name": "ReportTest"})
    project = r.json()

    workspace_path = Path(f"./workspaces/{project['id']}")
    data_dir = workspace_path / "data" / "raw"
    data_dir.mkdir(parents=True, exist_ok=True)

    order_csv = data_dir / "order_info.csv"
    with open(order_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["order_id", "user_id", "category", "date", "gmv", "discount"])
        writer.writeheader()
        for i in range(5):
            writer.writerow({
                "order_id": f"o{i}", "user_id": f"u{i}",
                "category": "food", "date": f"2024-01-{i+1:02d}",
                "gmv": str(100 * (i + 1)), "discount": str(10 * (i + 1))
            })

    exposure_csv = data_dir / "exposure_info.csv"
    with open(exposure_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["category", "date", "exposure"])
        writer.writeheader()
        for i in range(5):
            writer.writerow({"category": "food", "date": f"2024-01-{i+1:02d}", "exposure": "500"})

    activity_csv = data_dir / "activity_timeline.csv"
    with open(activity_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["category", "date", "payday", "activity_id"])
        writer.writeheader()
        for i in range(5):
            writer.writerow({
                "category": "food", "date": f"2024-01-{i+1:02d}",
                "payday": "1" if i == 0 else "0",
                "activity_id": f"act{i}" if i < 2 else ""
            })

    build_category_day_panel(project["id"], str(workspace_path))
    run_diagnostics(project["id"], str(workspace_path))

    latest_path = workspace_path / ".analysis" / "latest_result.json"
    latest_result = {
        "diagnostics": {"summary": {"total_gmv": 1500, "total_days": 5, "total_categories": 1}},
        "localgap": {"categories": [], "total_actual_gmv": 1500, "total_baseline_gmv": 1000, "total_local_gap": 500},
        "psm_did": {},
    }
    latest_path.parent.mkdir(parents=True, exist_ok=True)
    latest_path.write_text(json.dumps(latest_result), encoding="utf-8")

    return project


def test_report_generate_creates_markdown(project_with_results):
    workspace_path = Path(f"./workspaces/{project_with_results['id']}")
    result = render_report(project_with_results["id"], str(workspace_path))

    assert result.ok is True
    assert "report.md" in result.summary or "报告已生成" in result.summary

    report_path = workspace_path / "reports" / "report.md"
    assert report_path.exists()

    content = report_path.read_text(encoding="utf-8")
    assert "商业分析报告" in content
    assert "摘要" in content or "数据概况" in content


def test_report_without_results(client):
    r = client.post("/api/projects", json={"name": "NoResultsTest"})
    project = r.json()

    workspace_path = Path(f"./workspaces/{project['id']}")
    result = render_report(project["id"], str(workspace_path))

    assert result.ok is False
    assert "NO_RESULTS" in str(result.error)
