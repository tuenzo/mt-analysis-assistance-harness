from pathlib import Path
from app.tools.schemas import ToolResult
from app.projects.service import ProjectService
from app.analysis.pipelines.diagnostics import run_diagnostics
from app.analysis.pipelines.localgap import run_localgap
from app.analysis.pipelines.psm_did import run_psm_did


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
    return ToolResult(
        ok=True,
        action="analysis.run_gps_uplift",
        summary="GPS-Uplift 分析完成（stub）",
        artifacts=[
            {"type": "chart", "title": "gps_dose_response.png"},
            {"type": "model_output", "title": "uplift_result.json", "method_status": "stub"},
        ],
    )


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

    results = []
    all_ok = True

    from app.analysis.pipelines.build_panel import build_category_day_panel
    result = build_category_day_panel(project_id, str(workspace_path))
    results.append(("panel.build_category_day", result.ok))
    if not result.ok:
        all_ok = False

    result = run_diagnostics(project_id, str(workspace_path))
    results.append(("analysis.run_diagnostics", result.ok))
    if not result.ok:
        all_ok = False

    result = run_localgap(project_id, str(workspace_path))
    results.append(("analysis.run_localgap", result.ok))
    if not result.ok:
        all_ok = False

    result = run_psm_did(project_id, str(workspace_path))
    results.append(("analysis.run_psm_did", result.ok))
    if not result.ok:
        all_ok = False

    from app.tools.chart_tools import chart_render
    result = chart_render(project_id, {"type": "gmv_trend"})
    results.append(("chart.render", result.ok))

    from app.tools.result_tools import result_get_latest
    result = result_get_latest(project_id, {})
    results.append(("result.get_latest", result.ok))

    failed = [name for name, ok in results if not ok]
    summary = f"Full pipeline {'完成' if all_ok else '部分完成'}: {', '.join(n.split('.')[-1] for n, _ in results)}"
    if failed:
        summary += f", 失败: {', '.join(failed)}"

    return ToolResult(
        ok=all_ok,
        action="analysis.run_full_pipeline",
        summary=summary,
        artifacts=[{"type": "pipeline_result", "steps": results}],
        assistant_hint="完整 pipeline 执行完成，可以查看各步骤结果。"
    )
