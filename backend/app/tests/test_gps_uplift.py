import csv
import json
from datetime import date, timedelta
from pathlib import Path

import pytest

from app.analysis.pipelines.build_panel import build_category_day_panel
from app.analysis.pipelines.gps_uplift import run_gps_uplift
from app.analysis.pipelines.localgap import run_localgap
from app.core import config
from app.core.database import init_db, reset_engine
from app.projects.service import ProjectService
from app.tools.result_tools import result_get_latest


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


def test_gps_uplift_produces_non_stub_outputs(isolated_backend):
    project = ProjectService().create_project("GPS Uplift Test", is_test=True)
    workspace = Path(project.workspace_path)
    _write_signal_data(workspace)

    panel_result = build_category_day_panel(project.id, str(workspace))
    assert panel_result.ok is True
    localgap_result = run_localgap(project.id, str(workspace))
    assert localgap_result.ok is True

    result = run_gps_uplift(project.id, str(workspace), {})

    assert result.ok is True
    assert "stub" not in result.summary.lower()
    gps_path = workspace / ".analysis" / "gps_uplift_result.json"
    uplift_path = workspace / ".analysis" / "uplift_result.json"
    rec_path = workspace / "artifacts" / "tables" / "category_action_recommendations.csv"
    quadrant_path = workspace / "artifacts" / "tables" / "resource_marketing_quadrants.csv"
    assert gps_path.exists()
    assert uplift_path.exists()
    assert rec_path.exists()
    assert quadrant_path.exists()

    payload = json.loads(uplift_path.read_text(encoding="utf-8"))
    assert payload["method_status"] in {"implemented", "limited"}
    assert payload["method_status"] != "stub"
    assert payload["dose_response"]["exposure"]["curve"]
    assert "supported_range" in payload["dose_response"]["exposure"]
    assert "overlap_quality" in payload["dose_response"]["exposure"]["diagnostics"]
    assert "uplift_model" in payload
    assert payload["uplift_model"]["status"] in {"ok", "insufficient_support", "insufficient_treatment_split", "insufficient_estimable_folds"}
    assert payload["uplift_ranking"]
    assert payload["resource_uplift_scores"]
    assert payload["rank_curves"]["combined"]
    assert payload["rank_curves"]["exposure"]
    assert payload["rank_curves"]["discount"]
    assert payload["marketing_quadrants"]["resource_quadrants"]
    assert payload["marketing_quadrants"]["classic_quadrants"]
    assert payload["heterogeneity"]["exposure_by_category_size"]
    assert payload["heterogeneity"]["discount_by_payday"]
    assert payload["segments"]
    assert payload["recommended_actions"]
    assert payload["diagnostics"]["row_count"] >= 21
    assert payload["evidence_artifacts"]

    with rec_path.open("r", newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    assert rows
    assert {"category", "action", "reason", "guardrail", "evidence"}.issubset(rows[0].keys())
    with quadrant_path.open("r", newline="", encoding="utf-8-sig") as handle:
        quadrant_rows = list(csv.DictReader(handle))
    assert quadrant_rows
    assert {"resource_quadrant", "classic_quadrant", "exposure_uplift", "discount_uplift"}.issubset(quadrant_rows[0].keys())

    latest = result_get_latest(project.id, {})
    assert latest.ok is True
    latest_data = latest.artifacts[0]["data"]
    assert latest_data["uplift"]["method_status"] != "stub"
    assert latest_data["recommended_actions"]
    uplift_metrics = next(item for item in latest.artifacts[0]["metadata"]["results"] if item["name"] == "uplift")
    assert uplift_metrics["key_metrics"]["recommendation_count"] == len(payload["recommended_actions"])


def test_gps_uplift_without_panel_returns_actionable_error(tmp_path):
    result = run_gps_uplift("proj_missing_panel", str(tmp_path), {})

    assert result.ok is False
    assert result.error["code"] == "PANEL_NOT_FOUND"


def _write_signal_data(workspace: Path) -> None:
    raw_dir = workspace / "data" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    categories = {
        "drinks": {"base": 180.0, "trend": 5.0, "exposure": 900.0, "activity_gain": 95.0, "coef": 0.055},
        "snacks": {"base": 150.0, "trend": 3.0, "exposure": 760.0, "activity_gain": 35.0, "coef": 0.025},
        "home": {"base": 210.0, "trend": 1.5, "exposure": 640.0, "activity_gain": -18.0, "coef": -0.005},
    }
    start = date(2026, 4, 1)
    activity_days = set(range(9, 16))

    with (raw_dir / "order_info.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["order_id", "user_id", "category", "date", "gmv", "discount"])
        writer.writeheader()
        row_id = 0
        for day in range(24):
            current_date = start + timedelta(days=day)
            for category, spec in categories.items():
                is_activity = day in activity_days
                exposure_lift = (day % 5) * 18 + (110 if is_activity and category == "drinks" else 40 if is_activity else 0)
                exposure = spec["exposure"] + exposure_lift
                discount_rate = 0.05 + (0.03 if is_activity else 0.0) + (0.01 if category == "home" else 0.0)
                activity_gain = spec["activity_gain"] if is_activity else 0.0
                gmv = spec["base"] + spec["trend"] * day + activity_gain + exposure * spec["coef"]
                discount = max(0.0, gmv * discount_rate)
                row_id += 1
                writer.writerow(
                    {
                        "order_id": f"o{row_id}",
                        "user_id": f"u{row_id % 17}",
                        "category": category,
                        "date": current_date.isoformat(),
                        "gmv": f"{gmv:.2f}",
                        "discount": f"{discount:.2f}",
                    }
                )

    with (raw_dir / "exposure_info.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["category", "date", "exposure", "buy_uv"])
        writer.writeheader()
        for day in range(24):
            current_date = start + timedelta(days=day)
            for category, spec in categories.items():
                is_activity = day in activity_days
                exposure_lift = (day % 5) * 18 + (110 if is_activity and category == "drinks" else 40 if is_activity else 0)
                exposure = spec["exposure"] + exposure_lift
                buy_uv = max(1, int(exposure * (0.07 if category == "drinks" else 0.045)))
                writer.writerow({"category": category, "date": current_date.isoformat(), "exposure": f"{exposure:.0f}", "buy_uv": buy_uv})

    with (raw_dir / "activity_timeline.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["category", "date", "payday", "activity_id"])
        writer.writeheader()
        for day in activity_days:
            current_date = start + timedelta(days=day)
            for category in categories:
                writer.writerow(
                    {
                        "category": category,
                        "date": current_date.isoformat(),
                        "payday": "1" if current_date.day == 12 else "0",
                        "activity_id": "spring_promo",
                    }
                )
