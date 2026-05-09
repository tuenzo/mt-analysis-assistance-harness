import csv
import json
from datetime import date, timedelta
from pathlib import Path

import pytest

from app.analysis.pipelines.build_panel import build_category_day_panel
from app.analysis.pipelines.psm_did import run_psm_did
from app.core import config
from app.core.database import init_db, reset_engine
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


def test_psm_did_uses_resource_lift_matching_and_event_windows(isolated_backend):
    project = ProjectService().create_project("PSM DID Test", is_test=True)
    workspace = Path(project.workspace_path)
    _write_psm_signal_data(workspace)

    panel_result = build_category_day_panel(project.id, str(workspace))
    assert panel_result.ok is True

    result = run_psm_did(project.id, str(workspace))

    assert result.ok is True
    assert "simplified" not in result.summary.lower()
    output_path = workspace / ".analysis" / "psm_did_result.json"
    assert output_path.exists()

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["method"] == "psm_did"
    assert payload["method_status"] in {"implemented", "limited"}
    assert payload["primary_treatment"] in {"exposure", "discount"}
    assert payload["estimates"]["did_estimate"] != 0
    assert payload["lift"]["incremental_lift_pct"] != 0
    assert payload["treated_categories_count"] >= 1
    assert payload["control_categories_count"] >= 1

    exposure = payload["treatments"]["exposure"]
    assert exposure["treatment_definition"]["lift_column"] == "view_lift"
    assert exposure["matched_counts"]["matched_pairs"] >= 1
    assert exposure["balance"]["before_matching"]["covariates"]
    assert exposure["balance"]["after_matching"]["covariates"]
    assert exposure["event_study"]["matched"]["windows"]
    assert exposure["event_study"]["matched"]["primary_did"] is not None
    assert exposure["placebo"]["shift_days"] == -7
    assert "LocalGap remains the main increment accounting layer" in payload["interpretation"]["guardrail"]


def test_psm_did_without_panel_returns_actionable_error(tmp_path):
    result = run_psm_did("missing_project", str(tmp_path))

    assert result.ok is False
    assert result.error["code"] == "PANEL_NOT_FOUND"


def _write_psm_signal_data(workspace: Path) -> None:
    raw_dir = workspace / "data" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    categories = [f"cat_{index}" for index in range(8)]
    start = date(2026, 3, 1)
    activity_days = set(range(24, 30))

    with (raw_dir / "order_info.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["order_id", "user_id", "category", "date", "gmv", "discount"])
        writer.writeheader()
        row_id = 0
        for day in range(36):
            current = start + timedelta(days=day)
            is_activity = day in activity_days
            for idx, category in enumerate(categories):
                high_exposure = idx in {0, 1}
                high_discount = idx in {2, 3}
                base = 160 + idx * 12 + day * 1.5
                activity_gain = 140 if is_activity and high_exposure else 75 if is_activity and high_discount else 15 if is_activity else 0
                gmv = base + activity_gain
                discount_rate = 0.04 + (0.08 if is_activity and high_discount else 0.02 if is_activity else 0.0)
                row_id += 1
                writer.writerow(
                    {
                        "order_id": f"o{row_id}",
                        "user_id": f"u{row_id % 31}",
                        "category": category,
                        "date": current.isoformat(),
                        "gmv": f"{gmv:.2f}",
                        "discount": f"{gmv * discount_rate:.2f}",
                    }
                )

    with (raw_dir / "exposure_info.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["category", "date", "exposure", "buy_uv"])
        writer.writeheader()
        for day in range(36):
            current = start + timedelta(days=day)
            is_activity = day in activity_days
            for idx, category in enumerate(categories):
                high_exposure = idx in {0, 1}
                exposure = 900 + idx * 45 + (720 if is_activity and high_exposure else 110 if is_activity else 0)
                buy_uv = int(exposure * (0.08 if high_exposure else 0.05))
                writer.writerow({"category": category, "date": current.isoformat(), "exposure": f"{exposure:.0f}", "buy_uv": buy_uv})

    with (raw_dir / "activity_timeline.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["date", "activity_id", "payday"])
        writer.writeheader()
        for day in activity_days:
            current = start + timedelta(days=day)
            writer.writerow({"date": current.isoformat(), "activity_id": "spring_campaign", "payday": "1" if current.day == 27 else "0"})
