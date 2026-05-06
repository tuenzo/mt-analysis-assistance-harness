from pathlib import Path

from app.analysis.pipelines.diagnostics import run_diagnostics
from app.analysis.pipelines.gps_uplift import run_gps_uplift
from app.analysis.pipelines.localgap import run_localgap
from app.analysis.pipelines.psm_did import run_psm_did
from app.projects.service import ProjectService
from app.tools.schemas import ToolResult


def analysis_run_diagnostics(project_id: str, payload: dict) -> ToolResult:
    service = ProjectService()
    project = service.get_project(project_id)
    if not project:
        return ToolResult(
            ok=False,
            action="analysis.run_diagnostics",
            summary="",
            error={"code": "NOT_FOUND", "message": "Project not found"},
        )

    workspace_path = Path(project.workspace_path)
    return run_diagnostics(project_id, str(workspace_path))


def analysis_run_psm_did(project_id: str, payload: dict) -> ToolResult:
    service = ProjectService()
    project = service.get_project(project_id)
    if not project:
        return ToolResult(
            ok=False,
            action="analysis.run_psm_did",
            summary="",
            error={"code": "NOT_FOUND", "message": "Project not found"},
        )

    workspace_path = Path(project.workspace_path)
    return run_psm_did(project_id, str(workspace_path))


def analysis_run_localgap(project_id: str, payload: dict) -> ToolResult:
    service = ProjectService()
    project = service.get_project(project_id)
    if not project:
        return ToolResult(
            ok=False,
            action="analysis.run_localgap",
            summary="",
            error={"code": "NOT_FOUND", "message": "Project not found"},
        )

    workspace_path = Path(project.workspace_path)
    return run_localgap(project_id, str(workspace_path))


def analysis_run_gps_uplift(project_id: str, payload: dict) -> ToolResult:
    service = ProjectService()
    project = service.get_project(project_id)
    if not project:
        return ToolResult(
            ok=False,
            action="analysis.run_gps_uplift",
            summary="",
            error={"code": "NOT_FOUND", "message": "Project not found"},
        )

    workspace_path = Path(project.workspace_path)
    return run_gps_uplift(project_id, str(workspace_path), payload)


def analysis_run_full_pipeline(project_id: str, payload: dict) -> ToolResult:
    service = ProjectService()
    project = service.get_project(project_id)
    if not project:
        return ToolResult(
            ok=False,
            action="analysis.run_full_pipeline",
            summary="",
            error={"code": "NOT_FOUND", "message": "Project not found"},
        )

    workspace_path = Path(project.workspace_path)
    results: list[tuple[str, bool]] = []
    artifacts: list[dict] = []
    all_ok = True

    def record(step_result: ToolResult) -> None:
        nonlocal all_ok
        results.append((step_result.action, step_result.ok))
        artifacts.extend(step_result.artifacts)
        if not step_result.ok:
            all_ok = False

    from app.tools.data_tools import data_validate
    record(data_validate(project_id, {}))

    from app.analysis.pipelines.build_panel import build_category_day_panel
    record(build_category_day_panel(project_id, str(workspace_path)))

    record(run_diagnostics(project_id, str(workspace_path)))
    record(run_psm_did(project_id, str(workspace_path)))
    record(run_localgap(project_id, str(workspace_path)))
    record(analysis_run_gps_uplift(project_id, {}))

    from app.tools.chart_tools import chart_render
    record(chart_render(project_id, {"type": "gmv_trend"}))
    record(chart_render(project_id, {"type": "localgap"}))

    from app.tools.result_tools import result_get_latest
    record(result_get_latest(project_id, {}))

    from app.tools.report_tools import report_generate
    record(report_generate(project_id, {"format": payload.get("format", "md")}))

    failed = [name for name, ok in results if not ok]
    summary = (
        "Full pipeline completed: "
        if all_ok
        else "Full pipeline partially completed: "
    )
    summary += ", ".join(name for name, _ in results)
    if failed:
        summary += f"; failed: {', '.join(failed)}"

    return ToolResult(
        ok=all_ok,
        action="analysis.run_full_pipeline",
        summary=summary,
        artifacts=[*artifacts, {"type": "pipeline_result", "steps": results}],
        assistant_hint="Full pipeline finished. Open Dashboard or Reports to review outputs.",
    )
