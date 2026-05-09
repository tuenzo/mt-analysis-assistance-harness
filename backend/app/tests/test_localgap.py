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
    output_path = workspace_path / ".analysis" / "localgap_result.json"
    enriched_path = workspace_path / "data" / "processed" / "localgap_enriched_panel.csv"
    assert output_path.exists()
    assert enriched_path.exists()

    import json

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["method_status"] in {"implemented", "limited"}
    assert "baseline_method" in payload
    assert "coverage_rate" in payload["diagnostics"]
    assert "baseline_quality" in payload["diagnostics"]


def test_localgap_without_panel(client):
    r = client.post("/api/projects", json={"name": "NoPanelLGTest"})
    project = r.json()

    workspace_path = Path(f"./workspaces/{project['id']}")
    result = run_localgap(project["id"], str(workspace_path))

    assert result.ok is False
    assert "PANEL_NOT_FOUND" in str(result.error)


def test_localgap_adds_component_lmdi_decomposition(client):
    r = client.post("/api/projects", json={"name": "LocalGapLmdiTest"})
    project = r.json()
    workspace_path = Path(f"./workspaces/{project['id']}")
    data_dir = workspace_path / "data" / "raw"
    data_dir.mkdir(parents=True, exist_ok=True)

    from datetime import date, timedelta

    start = date(2026, 1, 1)
    activity_days = {28, 29, 30}
    with open(data_dir / "order_info.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["order_id", "user_id", "category", "date", "gmv", "discount", "order_count"],
        )
        writer.writeheader()
        for day in range(35):
            current = start + timedelta(days=day)
            is_activity = day in activity_days
            order_count = 18 if is_activity else 10 + (day % 3)
            aov = 14.0 if is_activity else 12.0 + (day % 2)
            gmv = order_count * aov
            writer.writerow(
                {
                    "order_id": f"o{day}",
                    "user_id": f"u{day}",
                    "category": "drinks",
                    "date": current.isoformat(),
                    "gmv": f"{gmv:.2f}",
                    "discount": f"{gmv * 0.08:.2f}",
                    "order_count": str(order_count),
                }
            )

    with open(data_dir / "exposure_info.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["category", "date", "exposure", "buy_uv"])
        writer.writeheader()
        for day in range(35):
            current = start + timedelta(days=day)
            writer.writerow({"category": "drinks", "date": current.isoformat(), "exposure": "1000", "buy_uv": "80"})

    with open(data_dir / "activity_timeline.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["date", "activity_id"])
        writer.writeheader()
        for day in activity_days:
            writer.writerow({"date": (start + timedelta(days=day)).isoformat(), "activity_id": "payday_promo"})

    panel_result = build_category_day_panel(project["id"], str(workspace_path))
    assert panel_result.ok is True
    result = run_localgap(project["id"], str(workspace_path))
    assert result.ok is True

    payload = json.loads((workspace_path / ".analysis" / "localgap_result.json").read_text(encoding="utf-8"))
    assert "non_sparse_sample" in payload
    assert payload["non_sparse_sample"]["component_estimable_rows"] > 0
    lmdi = payload["lmdi_decomposition"]
    assert lmdi["method"] == "additive_lmdi_order_aov"
    assert lmdi["overall"]["zero_handling_flag"] == "exact_positive"
    assert abs(lmdi["overall"]["lmdi_residual_check"]) < 1e-5
    assert lmdi["overall"]["order_contribution"] != 0
    assert lmdi["overall"]["aov_contribution"] != 0
