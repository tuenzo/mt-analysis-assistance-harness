import csv
import json
from datetime import date, timedelta
from pathlib import Path

import pytest

from app.analysis.pipelines.user_week_hmm import build_user_week_panel, run_hmm_state_path
from app.core import config
from app.core.database import init_db, reset_engine
from app.jobs.pipeline_runner import PIPELINE_STEPS
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


def test_user_week_panel_and_hmm_interface_outputs(isolated_backend):
    project = ProjectService().create_project("User Week HMM Test", is_test=True)
    workspace = Path(project.workspace_path)
    _write_user_orders(workspace)

    panel_result = build_user_week_panel(project.id, str(workspace))
    hmm_result = run_hmm_state_path(project.id, str(workspace))

    assert panel_result.ok is True
    assert hmm_result.ok is True
    panel_path = workspace / "data" / "processed" / "user_week_panel.csv"
    panel_result_path = workspace / ".analysis" / "user_week_panel_result.json"
    hmm_path = workspace / ".analysis" / "hmm_state_path_result.json"
    state_path = workspace / "artifacts" / "tables" / "hmm_state_paths.csv"
    assert panel_path.exists()
    assert panel_result_path.exists()
    assert hmm_path.exists()
    assert state_path.exists()

    panel_payload = json.loads(panel_result_path.read_text(encoding="utf-8"))
    assert panel_payload["method"] == "user_week_panel"
    assert panel_payload["method_status"] == "implemented"
    assert panel_payload["summary"]["user_count"] == 4
    assert panel_payload["summary"]["week_count"] >= 4

    hmm_payload = json.loads(hmm_path.read_text(encoding="utf-8"))
    assert hmm_payload["method"] == "hmm_state_path_interface"
    assert hmm_payload["method_status"] == "limited"
    assert hmm_payload["state_model"] == "quantile_proxy_pending_hmm_dependency"
    assert hmm_payload["states"]
    assert hmm_payload["transitions"]
    assert "standard pipeline" in " ".join(hmm_payload["interpretation_rules"])


def test_user_week_and_hmm_actions_are_registered_but_not_standard_pipeline():
    registry = get_registry()

    assert registry.get_tool(BusinessAnalysisAction.PANEL_BUILD_USER_WEEK) is not None
    assert registry.get_tool(BusinessAnalysisAction.ANALYSIS_RUN_HMM_STATE_PATH) is not None
    pipeline_actions = [action for _, action, _, _ in PIPELINE_STEPS]
    assert "panel.build_user_week" not in pipeline_actions
    assert "analysis.run_hmm_state_path" not in pipeline_actions


def test_user_week_panel_without_user_id_writes_limited_artifact(isolated_backend):
    project = ProjectService().create_project("Limited User Week Test", is_test=True)
    workspace = Path(project.workspace_path)
    raw_dir = workspace / "data" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    (raw_dir / "order_info.csv").write_text(
        "\n".join(
            [
                "order_id,category,date,gmv,discount",
                "o1,drinks,2026-04-01,100,10",
                "o2,drinks,2026-04-08,120,12",
            ]
        ),
        encoding="utf-8",
    )

    result = build_user_week_panel(project.id, str(workspace))

    assert result.ok is True
    payload = json.loads((workspace / ".analysis" / "user_week_panel_result.json").read_text(encoding="utf-8"))
    assert payload["method_status"] == "limited"
    assert any("user_id" in warning for warning in payload["warnings"])
    assert not (workspace / "data" / "processed" / "user_week_panel.csv").exists()


def _write_user_orders(workspace: Path) -> None:
    raw_dir = workspace / "data" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    start = date(2026, 4, 6)
    users = ["u1", "u2", "u3", "u4"]
    with (raw_dir / "order_info.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["order_id", "user_id", "category", "date", "gmv", "discount", "order_count", "quantity"],
        )
        writer.writeheader()
        row_id = 0
        for week in range(5):
            for user_index, user_id in enumerate(users):
                for day_offset in [0, 2, 5]:
                    current_date = start + timedelta(days=week * 7 + day_offset)
                    row_id += 1
                    base = 35 + user_index * 18 + week * 9
                    gmv = base + day_offset * 3
                    discount = gmv * (0.03 + user_index * 0.005)
                    writer.writerow(
                        {
                            "order_id": f"o{row_id}",
                            "user_id": user_id,
                            "category": "drinks" if user_index % 2 == 0 else "snacks",
                            "date": current_date.isoformat(),
                            "gmv": f"{gmv:.2f}",
                            "discount": f"{discount:.2f}",
                            "order_count": 1,
                            "quantity": 1 + user_index,
                        }
                    )
