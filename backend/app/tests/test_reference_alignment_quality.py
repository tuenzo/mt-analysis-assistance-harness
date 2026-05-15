import json
from pathlib import Path

import pytest

from app.core import config
from app.core.database import get_session, init_db, reset_engine
from app.projects.models import Job
from app.projects.service import ProjectService
from app.tools.quality_tools import quality_audit_lineage, quality_score_reference_alignment


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


def test_demo_project_score_is_capped_at_20(isolated_backend):
    project = ProjectService().create_project("Demo Review", is_test=True)
    workspace = Path(project.workspace_path)
    _write_json(workspace / ".analysis" / "latest_result.json", {"demo": True, "categories": ["Beverage", "Snack"]})

    audit = quality_audit_lineage(project.id, {})
    score_result = quality_score_reference_alignment(project.id, {})
    score = _read_score(project)

    assert audit.ok is True
    assert "demo_contamination" in score["lineage_audit"]["cap_reasons"]
    assert score["final_score"] <= 20
    assert any(cap["reason"] == "demo_contamination" and cap["max_score"] == 20 for cap in score["applied_caps"])
    assert score_result.ok is True
    assert (workspace / ".analysis" / "reference_alignment_score.json").exists()
    assert (workspace / "artifacts" / "tables" / "reference_alignment_diffs.csv").exists()


def test_processed_panel_registered_as_raw_source_is_capped_at_40(isolated_backend):
    project = ProjectService().create_project("Realdata Mis-role", is_test=True)
    ProjectService().upload_file(
        project.id,
        b"category,date,gmv,view_uv,is_activity\nfood,2026-01-01,100,20,1",
        "category_date_panel.csv",
        "order_info",
    )

    score_result = quality_score_reference_alignment(project.id, {})
    score = _read_score(project)
    issue_codes = {issue["code"] for issue in score["lineage_audit"]["issues"]}

    assert score_result.ok is True
    assert {"processed_panel_as_raw", "source_roles_missing"} & issue_codes
    assert score["final_score"] <= 40
    assert any(cap["reason"] == "source_incomplete" and cap["max_score"] == 40 for cap in score["applied_caps"])


def test_valid_fixture_produces_uncapped_nonzero_trend_score(isolated_backend):
    project = ProjectService().create_project("Reference Alignment Valid Fixture", is_test=True)
    service = ProjectService()
    service.upload_file(
        project.id,
        b"order_id,user_id,category,date,gmv,discount\n1,u1,food,2026-01-01,100,10",
        "order_info.csv",
        "order_info",
    )
    service.upload_file(
        project.id,
        b"category,date,exposure,buy_uv\nfood,2026-01-01,1000,100",
        "exposure_info.csv",
        "exposure_info",
    )
    service.upload_file(
        project.id,
        b"category,date,payday,activity_id\nfood,2026-01-01,1,A1",
        "activity_timeline.csv",
        "activity_timeline",
    )
    _write_reference_like_results(Path(project.workspace_path))

    score_result = quality_score_reference_alignment(project.id, {})
    score = _read_score(project)

    assert score_result.ok is True
    assert score["applied_caps"] == []
    assert score["final_score"] >= 60
    assert score["subscores"]["core_trend"]["score"] > 0


def test_lineage_audit_tolerates_legacy_string_step_jobs(isolated_backend):
    project = ProjectService().create_project("Legacy Step Shape", is_test=True)
    db = get_session()
    try:
        db.add(
            Job(
                id="job_legacy_steps",
                project_id=project.id,
                action="analysis.run_full_pipeline",
                status="succeeded",
                progress=1,
                output_json=json.dumps({"steps": ["data.validate", "panel.build_category_day"]}),
            )
        )
        db.commit()
    finally:
        db.close()

    audit = quality_audit_lineage(project.id, {})

    assert audit.ok is True


def _write_reference_like_results(workspace: Path) -> None:
    analysis_dir = workspace / ".analysis"
    report_dir = workspace / "reports"
    analysis_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)
    _write_json(analysis_dir / "diagnostics_result.json", {"method_status": "implemented", "summary": {"activity_lift_pct": 12.5}, "payday_overlap": {"peak": True}})
    _write_json(analysis_dir / "psm_did_result.json", {"method_status": "implemented", "estimates": {"did_estimate": 4.2}})
    _write_json(
        analysis_dir / "localgap_result.json",
        {
            "method_status": "implemented",
            "total_local_gap": 120.0,
            "lmdi_decomposition": {"overall": {"order_contribution": 80.0, "aov_contribution": 20.0}},
            "categories": [{"category": "food", "exposure_gap": 90.0, "discount_gap": 20.0}],
            "notes": "payday window included",
        },
    )
    _write_json(analysis_dir / "mechanism_regression_result.json", {"method_status": "implemented", "discount": {"effect": "tiered"}})
    _write_json(analysis_dir / "conversion_diagnostics_result.json", {"method_status": "implemented", "exposure_tiers": ["low", "mid", "high"], "discount": {"caution": True}})
    _write_json(
        analysis_dir / "uplift_result.json",
        {
            "method_status": "implemented",
            "dose_response": {"exposure": {"curve": [1, 2]}, "discount": {"curve": [1, 3]}},
            "rank_curves": {"exposure": [{"rank": 1, "uplift": 0.2}]},
            "marketing_quadrants": [{"category": "food", "quadrant": "prioritize"}],
        },
    )
    _write_json(analysis_dir / "latest_result_index.json", {"limitations": ["sample fixture"], "quality_gates": {"localgap": {"status": "ready"}}})
    (report_dir / "report.md").write_text("All claims cite artifacts and method_status caveats; evidence is limited.", encoding="utf-8")


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _read_score(project) -> dict:
    return json.loads((Path(project.workspace_path) / ".analysis" / "reference_alignment_score.json").read_text(encoding="utf-8"))
