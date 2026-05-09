import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.analysis.chart_renderer import render_chart
from app.core import config
from app.core.database import init_db, reset_engine
from app.projects.service import ProjectService
from app.reports.renderer import render_report
from app.tools.result_tools import artifact_read, result_get_latest


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


@pytest.fixture
def project_with_results(isolated_backend):
    project = ProjectService().create_project("Report Realism Test", is_test=True)
    workspace = Path(project.workspace_path)
    _write_analysis_outputs(workspace)
    return project


def test_report_generate_creates_evidence_backed_markdown(project_with_results):
    workspace = Path(project_with_results.workspace_path)
    render_chart(str(workspace), "gmv_trend")
    render_chart(str(workspace), "localgap")

    result = render_report(project_with_results.id, str(workspace), project_name=project_with_results.name)

    assert result.ok is True
    assert result.artifacts[0]["metadata"]["method_status"] == "deterministic_report_plan"
    assert result.artifacts[0]["metadata"]["confidence"]["label"] in {"medium", "medium-high"}
    assert result.artifacts[0]["metadata"]["evidence_artifacts"]
    assert result.artifacts[0]["metadata"]["limitations"]
    assert result.artifacts[0]["metadata"]["recommended_follow_up"]

    report_path = workspace / "reports" / "report.md"
    metadata_path = workspace / "reports" / "report_metadata.json"
    plan_path = workspace / "reports" / "report_plan.json"
    analysis_plan_path = workspace / ".analysis" / "report_plan.json"
    assert report_path.exists()
    assert metadata_path.exists()
    assert plan_path.exists()
    assert analysis_plan_path.exists()

    content = report_path.read_text(encoding="utf-8")
    assert "# Report Realism Test 分析报告" in content
    assert "## 执行摘要" in content
    assert "## 证据覆盖" in content
    assert "## 增量与因果方向" in content
    assert "**证据文件**" in content
    assert "**建议下一步**" in content
    assert "总 GMV" in content
    assert "总增量" in content
    assert "Analysis Report" not in content
    assert "Executive Snapshot" not in content
    assert "```json" not in content
    assert "![" not in content

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert metadata["method_status"] == "deterministic_report_plan"
    assert metadata["findings"]
    assert metadata["evidence_artifacts"]
    assert metadata["limitations"]
    assert metadata["recommended_follow_up"]
    assert any("PSM-DID" in item for item in metadata["limitations"])

    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    assert all(section["findings"] for section in plan["sections"])
    assert all("evidence_artifacts" in section for section in plan["sections"])
    assert plan["sections"][0]["title"] == "执行摘要"


def test_report_partial_results_do_not_overclaim_causality(isolated_backend):
    project = ProjectService().create_project("Partial Report Test", is_test=True)
    workspace = Path(project.workspace_path)
    analysis_dir = workspace / ".analysis"
    analysis_dir.mkdir(parents=True, exist_ok=True)
    diagnostics = {
        "summary": {"total_gmv": 1000, "total_days": 2, "total_categories": 1},
        "gmv_trend": [{"date": "2026-04-01", "gmv": 400}, {"date": "2026-04-02", "gmv": 600}],
        "activity_vs_non": {"activity_avg_gmv": 600, "non_activity_avg_gmv": 400, "lift": 50},
    }
    (analysis_dir / "diagnostics_result.json").write_text(json.dumps(diagnostics), encoding="utf-8")
    (analysis_dir / "latest_result.json").write_text(json.dumps({"diagnostics": diagnostics}), encoding="utf-8")

    result = render_report(project.id, str(workspace), project_name=project.name)

    assert result.ok is True
    content = (workspace / "reports" / "report.md").read_text(encoding="utf-8")
    assert "不做因果 lift 结论" in content
    assert "运行 `analysis.run_psm_did`" in content
    metadata = json.loads((workspace / "reports" / "report_metadata.json").read_text(encoding="utf-8"))
    assert any("PSM-DID 证据缺失" in item for item in metadata["limitations"])


def test_latest_report_returns_structured_kpi_summary(project_with_results):
    render_report(project_with_results.id, project_with_results.workspace_path, project_name=project_with_results.name)

    response = TestClient(app).get(f"/api/projects/{project_with_results.id}/reports/latest")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["kpi_summary"] == {
        "total_gmv": 1984.4,
        "total_local_gap": 437.1,
        "did_estimate": -111.49,
        "incremental_lift_pct": -102.05,
    }
    assert data["metadata"]["evidence_index"]["results"]


def test_chart_render_preserves_plot_fields_and_adds_metadata(project_with_results):
    workspace = Path(project_with_results.workspace_path)

    result = render_chart(str(workspace), "activity_comparison")

    assert result.ok is True
    artifact = result.artifacts[0]
    assert artifact["method_status"] == "chart_data_rendered"
    assert artifact["confidence"]["label"] == "low-medium"
    assert artifact["evidence_artifacts"] == [".analysis/diagnostics_result.json"]
    assert artifact["limitations"]
    assert artifact["recommended_follow_up"]

    chart_data = json.loads((workspace / "artifacts" / "charts" / "activity_comparison.json").read_text(encoding="utf-8"))
    assert chart_data["type"] == "bar"
    assert chart_data["x"] == ["Activity", "Non-activity"]
    assert "metadata" in chart_data
    assert chart_data["metadata"]["chart_type"] == "activity_comparison"


def test_result_get_latest_writes_evidence_index(project_with_results):
    workspace = Path(project_with_results.workspace_path)

    result = result_get_latest(project_with_results.id, {})

    assert result.ok is True
    summary_artifact = result.artifacts[0]
    assert summary_artifact["method_status"] == "aggregated_latest_results"
    assert summary_artifact["confidence"]["label"] in {"medium", "medium-high"}
    assert summary_artifact["evidence_artifacts"]
    assert summary_artifact["limitations"]
    assert summary_artifact["recommended_follow_up"]

    index_path = workspace / ".analysis" / "latest_result_index.json"
    assert index_path.exists()
    index = json.loads(index_path.read_text(encoding="utf-8"))
    assert index["method_status"] == "aggregated_latest_results"
    assert "Use directional language" in " ".join(index["claim_rules"])
    assert any(item["name"] == "psm_did" for item in index["results"])


def test_artifact_read_accepts_artifact_path_alias(project_with_results):
    result = artifact_read(
        project_with_results.id,
        {"artifact_path": ".analysis/uplift_result.json"},
    )

    assert result.ok is True
    assert result.artifacts[0]["path"] == ".analysis/uplift_result.json"
    assert result.artifacts[0]["data"]["method"] == "gps_uplift"


def test_artifact_read_rejects_workspace_escape(project_with_results):
    result = artifact_read(project_with_results.id, {"path": "../outside.json"})

    assert result.ok is False
    assert result.error["code"] == "WORKSPACE_ESCAPE"


def test_report_without_results(isolated_backend):
    project = ProjectService().create_project("No Results Test", is_test=True)

    result = render_report(project.id, project.workspace_path, project_name=project.name)

    assert result.ok is False
    assert result.error["code"] == "NO_RESULTS"


def _write_analysis_outputs(workspace: Path) -> None:
    analysis_dir = workspace / ".analysis"
    analysis_dir.mkdir(parents=True, exist_ok=True)

    diagnostics = {
        "summary": {"total_gmv": 1984.4, "total_days": 4, "total_categories": 3, "activity_days": 2},
        "gmv_trend": [
            {"date": "2026-04-24", "gmv": 260.4},
            {"date": "2026-04-25", "gmv": 438.8},
            {"date": "2026-04-26", "gmv": 655.6},
            {"date": "2026-04-27", "gmv": 629.6},
        ],
        "activity_vs_non": {"activity_avg_gmv": 642.6, "non_activity_avg_gmv": 349.6, "lift": 83.81},
        "payday_overlap": {"payday_avg_gmv": 655.6, "non_payday_avg_gmv": 442.93, "lift": 48.02},
        "category_concentration": [
            {"category": "drinks", "gmv": 639.7, "share": 32.24},
            {"category": "baby", "gmv": 630.3, "share": 31.76},
        ],
    }
    localgap = {
        "method": "localgap",
        "method_status": "implemented",
        "total_actual_gmv": 655.6,
        "total_baseline_gmv": 218.5,
        "total_local_gap": 437.1,
        "categories": [
            {
                "category": "drinks",
                "baseline_gmv": 120.5,
                "actual_gmv": 519.2,
                "local_gap": 398.7,
                "exposure_gap": 221.4,
                "discount_gap": 4.68,
                "payday_gap": 53.7,
                "interaction": 118.92,
            },
            {
                "category": "baby",
                "baseline_gmv": 98.0,
                "actual_gmv": 136.4,
                "local_gap": 38.4,
                "exposure_gap": 18.2,
                "discount_gap": 6.5,
                "payday_gap": 0,
                "interaction": 13.7,
            },
        ],
    }
    psm_did = {
        "method": "psm_did",
        "method_status": "simplified",
        "estimates": {
            "did_estimate": -111.49,
            "treated_pre_avg": 0,
            "treated_post_avg": 0,
            "control_pre_avg": 109.25,
            "control_post_avg": 220.74,
        },
        "lift": {"treated_lift_pct": 0, "control_lift_pct": 102.05, "incremental_lift_pct": -102.05},
    }
    uplift = {
        "method": "gps_uplift",
        "method_status": "stub",
        "segments": [{"segment": "Persuadables", "recommendation": "Increase exposure selectively."}],
    }
    panel_summary = {
        "row_count": 12,
        "category_count": 3,
        "date_range": {"start": "2026-04-24", "end": "2026-04-27"},
    }

    payloads = {
        "diagnostics_result.json": diagnostics,
        "localgap_result.json": localgap,
        "psm_did_result.json": psm_did,
        "uplift_result.json": uplift,
        "panel_summary.json": panel_summary,
        "latest_result.json": {
            "diagnostics": diagnostics,
            "localgap": localgap,
            "psm_did": psm_did,
            "uplift": uplift,
            "recommended_actions": [
                {
                    "category": "drinks",
                    "action": "scale_exposure",
                    "reason": "Exposure contribution is the largest LocalGap driver.",
                    "guardrail": "Check conversion and inventory before scaling.",
                }
            ],
        },
    }
    for filename, payload in payloads.items():
        (analysis_dir / filename).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
