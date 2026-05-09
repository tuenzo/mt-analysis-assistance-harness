import csv
import json
from datetime import date, timedelta
from pathlib import Path

import pytest

from app.analysis.pipelines.build_panel import build_category_day_panel
from app.analysis.pipelines.localgap import run_localgap
from app.analysis.pipelines.mechanism_regression import run_conversion_diagnostics, run_mechanism_regression
from app.core import config
from app.core.database import init_db, reset_engine
from app.projects.service import ProjectService
from app.tools.registry import get_registry
from app.tools.schemas import BusinessAnalysisAction


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


def test_mechanism_regression_and_conversion_outputs(isolated_backend):
    project = ProjectService().create_project("Mechanism Test", is_test=True)
    workspace = Path(project.workspace_path)
    _write_mechanism_signal_data(workspace)

    panel_result = build_category_day_panel(project.id, str(workspace))
    assert panel_result.ok is True
    localgap_result = run_localgap(project.id, str(workspace))
    assert localgap_result.ok is True

    mechanism_result = run_mechanism_regression(project.id, str(workspace))
    conversion_result = run_conversion_diagnostics(project.id, str(workspace))

    assert mechanism_result.ok is True
    assert conversion_result.ok is True

    mechanism_path = workspace / ".analysis" / "mechanism_regression_result.json"
    conversion_path = workspace / ".analysis" / "conversion_diagnostics_result.json"
    mechanism_table = workspace / "artifacts" / "tables" / "mechanism_regression_summary.csv"
    conversion_table = workspace / "artifacts" / "tables" / "conversion_by_exposure_tier.csv"
    assert mechanism_path.exists()
    assert conversion_path.exists()
    assert mechanism_table.exists()
    assert conversion_table.exists()

    mechanism_payload = json.loads(mechanism_path.read_text(encoding="utf-8"))
    assert mechanism_payload["method"] == "twfe_mechanism_regression"
    assert mechanism_payload["method_status"] in {"implemented", "limited"}
    assert mechanism_payload["sample"]["category_count"] == 6
    assert {model["model_id"] for model in mechanism_payload["models"]} >= {"gmv_level", "order_log", "aov_log"}
    assert any(model["status"] == "ok" for model in mechanism_payload["models"])
    assert mechanism_payload["resource_decomposition"]

    with mechanism_table.open("r", newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    assert rows
    assert {"model_id", "outcome", "term", "coefficient", "r_squared_within"}.issubset(rows[0].keys())
    assert any(row["term"] == "discount_rate_pp" for row in rows)

    conversion_payload = json.loads(conversion_path.read_text(encoding="utf-8"))
    assert conversion_payload["method"] == "conversion_discount_by_exposure_tier"
    assert conversion_payload["method_status"] in {"implemented", "limited"}
    assert [item["tier"] for item in conversion_payload["exposure_tiers"]] == [
        "low_exposure",
        "mid_exposure",
        "high_exposure",
    ]
    assert any(item["model"]["status"] == "ok" for item in conversion_payload["exposure_tiers"])
    assert all("discount_slope_per_pp" in item for item in conversion_payload["exposure_tiers"])

    with conversion_table.open("r", newline="", encoding="utf-8-sig") as handle:
        tier_rows = list(csv.DictReader(handle))
    assert len(tier_rows) == 3
    assert {"tier", "discount_slope_per_pp", "model_status"}.issubset(tier_rows[0].keys())


def test_mechanism_actions_are_registered():
    registry = get_registry()

    assert registry.get_tool(BusinessAnalysisAction.ANALYSIS_RUN_MECHANISM_REGRESSION) is not None
    assert registry.get_tool(BusinessAnalysisAction.ANALYSIS_RUN_CONVERSION_DIAGNOSTICS) is not None


def test_mechanism_regression_without_panel_returns_actionable_error(tmp_path):
    result = run_mechanism_regression("proj_missing_panel", str(tmp_path))

    assert result.ok is False
    assert result.error["code"] == "PANEL_NOT_FOUND"


def _write_mechanism_signal_data(workspace: Path) -> None:
    raw_dir = workspace / "data" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    categories = [
        ("value", 220.0, 280.0, 0.035, 26.0, 0.75),
        ("fresh", 260.0, 360.0, 0.04, 28.0, 0.7),
        ("snack", 310.0, 620.0, 0.045, 31.0, 0.6),
        ("drink", 340.0, 760.0, 0.05, 32.0, 0.55),
        ("beauty", 430.0, 1020.0, 0.055, 38.0, 0.42),
        ("home", 480.0, 1180.0, 0.06, 40.0, 0.36),
    ]
    start = date(2026, 3, 1)
    activity_days = set(range(14, 24))

    with (raw_dir / "order_info.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["order_id", "user_id", "category", "date", "gmv", "discount", "order_count"],
        )
        writer.writeheader()
        row_id = 0
        for day in range(36):
            current_date = start + timedelta(days=day)
            for idx, (category, base_gmv, base_exposure, base_conversion, aov, discount_response) in enumerate(categories):
                is_activity = day in activity_days
                exposure = base_exposure + (day % 6) * 18 + (140 + idx * 15 if is_activity else 0)
                discount_rate = 0.025 + idx * 0.004 + (0.018 + idx * 0.003 + (day % 3) * 0.004 if is_activity else 0)
                conversion_rate = base_conversion + discount_rate * discount_response + (0.004 if is_activity and idx < 4 else -0.001 if is_activity else 0)
                order_count = max(1, int(exposure * conversion_rate))
                gmv = base_gmv + order_count * aov + (day % 7) * 9 + (65 if is_activity and idx < 3 else 20 if is_activity else 0)
                discount = max(0.0, gmv * discount_rate)
                row_id += 1
                writer.writerow(
                    {
                        "order_id": f"o{row_id}",
                        "user_id": f"u{row_id % 31}",
                        "category": category,
                        "date": current_date.isoformat(),
                        "gmv": f"{gmv:.2f}",
                        "discount": f"{discount:.2f}",
                        "order_count": order_count,
                    }
                )

    with (raw_dir / "exposure_info.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["category", "date", "exposure", "buy_uv"])
        writer.writeheader()
        for day in range(36):
            current_date = start + timedelta(days=day)
            for idx, (category, _, base_exposure, base_conversion, _, discount_response) in enumerate(categories):
                is_activity = day in activity_days
                exposure = base_exposure + (day % 6) * 18 + (140 + idx * 15 if is_activity else 0)
                discount_rate = 0.025 + idx * 0.004 + (0.018 + idx * 0.003 + (day % 3) * 0.004 if is_activity else 0)
                conversion_rate = base_conversion + discount_rate * discount_response + (0.004 if is_activity and idx < 4 else -0.001 if is_activity else 0)
                buy_uv = max(1, int(exposure * conversion_rate))
                writer.writerow({"category": category, "date": current_date.isoformat(), "exposure": f"{exposure:.0f}", "buy_uv": buy_uv})

    with (raw_dir / "activity_timeline.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["category", "date", "payday", "activity_id"])
        writer.writeheader()
        for day in activity_days:
            current_date = start + timedelta(days=day)
            for category, *_ in categories:
                writer.writerow(
                    {
                        "category": category,
                        "date": current_date.isoformat(),
                        "payday": "1" if current_date.day == 27 else "0",
                        "activity_id": "spring_mechanism",
                    }
                )
