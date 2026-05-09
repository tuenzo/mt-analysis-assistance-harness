import json
from pathlib import Path

import pytest

from app.core import config
from app.core.database import init_db, reset_engine
from app.projects.service import ProjectService
from app.reports.renderer import render_report
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


def test_latest_results_and_report_include_reference_flow_outputs(isolated_backend):
    project = ProjectService().create_project("Reference Flow Report", is_test=True)
    workspace = Path(project.workspace_path)
    _write_reference_flow_outputs(workspace)

    latest = result_get_latest(project.id, {})

    assert latest.ok is True
    assert set(latest.artifacts[0]["available"]) >= {
        "user_week",
        "hmm_state_path",
        "mechanism",
        "conversion",
        "localgap",
        "psm_did",
    }
    index = latest.artifacts[0]["metadata"]
    assert any(item["name"] == "mechanism" for item in index["results"])
    assert any(item["name"] == "conversion" for item in index["results"])
    assert "mechanism" not in index["missing_results"]
    assert "conversion" not in index["missing_results"]

    report = render_report(project.id, str(workspace), project_name=project.name)

    assert report.ok is True
    metadata = json.loads((workspace / "reports" / "report_metadata.json").read_text(encoding="utf-8"))
    result_names = [item["name"] for item in metadata["evidence_index"]["results"]]
    assert "mechanism" in result_names
    assert "conversion" in result_names
    assert ".analysis/mechanism_regression_result.json" in metadata["evidence_artifacts"]
    assert ".analysis/conversion_diagnostics_result.json" in metadata["evidence_artifacts"]
    assert ".analysis/user_week_panel_result.json" in metadata["evidence_artifacts"]
    assert ".analysis/hmm_state_path_result.json" in metadata["evidence_artifacts"]

    plan = json.loads((workspace / "reports" / "report_plan.json").read_text(encoding="utf-8"))
    section_ids = [section["section_id"] for section in plan["sections"]]
    assert "mechanism_conversion" in section_ids
    assert "user_state_path" in section_ids
    assert section_ids.index("increment_causal_direction") < section_ids.index("mechanism_conversion")
    assert section_ids.index("mechanism_conversion") < section_ids.index("action_plan")
    assert section_ids.index("mechanism_conversion") < section_ids.index("user_state_path")
    assert section_ids.index("user_state_path") < section_ids.index("action_plan")
    mechanism_section = next(section for section in plan["sections"] if section["section_id"] == "mechanism_conversion")
    assert mechanism_section["evidence_artifacts"] == [
        ".analysis/mechanism_regression_result.json",
        ".analysis/conversion_diagnostics_result.json",
    ]
    assert any(call["action"] == "analysis.run_mechanism_regression" for call in mechanism_section["tool_calls"])
    assert any(call["action"] == "analysis.run_conversion_diagnostics" for call in mechanism_section["tool_calls"])
    user_state_section = next(section for section in plan["sections"] if section["section_id"] == "user_state_path")
    assert any(call["action"] == "panel.build_user_week" for call in user_state_section["tool_calls"])
    assert any(call["action"] == "analysis.run_hmm_state_path" for call in user_state_section["tool_calls"])


def _write_reference_flow_outputs(workspace: Path) -> None:
    analysis_dir = workspace / ".analysis"
    analysis_dir.mkdir(parents=True, exist_ok=True)
    diagnostics = {
        "method": "diagnostics",
        "method_status": "implemented",
        "summary": {"total_gmv": 1000, "total_days": 10, "total_categories": 3},
        "activity_vs_non": {"lift": 12.5},
    }
    psm_did = {
        "method": "psm_did",
        "method_status": "implemented",
        "estimates": {"did_estimate": 88.2},
        "lift": {"incremental_lift_pct": 6.1},
    }
    localgap = {
        "method": "localgap",
        "method_status": "implemented",
        "total_actual_gmv": 620.0,
        "total_baseline_gmv": 500.0,
        "total_local_gap": 120.0,
        "categories": [{"category": "drinks", "local_gap": 90.0, "exposure_gap": 70.0, "discount_gap": 20.0}],
    }
    mechanism = {
        "method": "twfe_mechanism_regression",
        "method_status": "implemented",
        "models": [
            {
                "model_id": "gmv_level",
                "outcome": "gmv",
                "status": "ok",
                "r_squared_within": 0.42,
                "coefficients": [
                    {"term": "discount_rate_pp", "coefficient": 1.25},
                    {"term": "log_view_uv", "coefficient": 22.5},
                ],
            }
        ],
    }
    conversion = {
        "method": "conversion_discount_by_exposure_tier",
        "method_status": "implemented",
        "exposure_tiers": [
            {
                "tier": "low_exposure",
                "category_count": 1,
                "row_count": 10,
                "avg_conversion_per_10k_uv": 400,
                "discount_slope_per_pp": 1.2,
                "model": {"status": "ok"},
            },
            {
                "tier": "mid_exposure",
                "category_count": 1,
                "row_count": 10,
                "avg_conversion_per_10k_uv": 510,
                "discount_slope_per_pp": 0.8,
                "model": {"status": "ok"},
            },
            {
                "tier": "high_exposure",
                "category_count": 1,
                "row_count": 10,
                "avg_conversion_per_10k_uv": 620,
                "discount_slope_per_pp": 0.3,
                "model": {"status": "ok"},
            },
        ],
    }
    user_week = {
        "method": "user_week_panel",
        "method_status": "implemented",
        "summary": {"row_count": 12, "user_count": 3, "week_count": 4, "total_gmv": 680.0},
    }
    hmm_state_path = {
        "method": "hmm_state_path_interface",
        "method_status": "limited",
        "state_count": 3,
        "states": [{"state": "core", "rows": 4, "avg_gmv": 80.0}],
        "transitions": [{"from_state": "active", "to_state": "core", "count": 3, "share": 0.5}],
        "sample": {"row_count": 12, "user_count": 3, "week_count": 4},
    }
    uplift = {
        "method": "gps_uplift",
        "method_status": "implemented",
        "segments": [{"segment": "Persuadables", "recommendation": "Scale exposure selectively."}],
    }
    panel_summary = {
        "row_count": 30,
        "category_count": 3,
        "date_range": {"start": "2026-04-01", "end": "2026-04-10"},
    }
    payloads = {
        "diagnostics_result.json": diagnostics,
        "psm_did_result.json": psm_did,
        "localgap_result.json": localgap,
        "user_week_panel_result.json": user_week,
        "hmm_state_path_result.json": hmm_state_path,
        "mechanism_regression_result.json": mechanism,
        "conversion_diagnostics_result.json": conversion,
        "uplift_result.json": uplift,
        "panel_summary.json": panel_summary,
    }
    for filename, payload in payloads.items():
        (analysis_dir / filename).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
