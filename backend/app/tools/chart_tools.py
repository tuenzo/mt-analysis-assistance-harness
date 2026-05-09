from app.tools.schemas import ToolResult
from app.projects.service import ProjectService
from app.analysis.chart_renderer import render_chart
from app.analysis.dashboard_chart_renderer import DEFAULT_DASHBOARD_CHART_IDS, render_dashboard_chart_artifacts
from app.core.config import resolve_project_path


def chart_render(project_id: str, payload: dict) -> ToolResult:
    service = ProjectService()
    project = service.get_project(project_id)
    if not project:
        return ToolResult(
            ok=False,
            action="chart.render",
            summary="",
            error={"code": "NOT_FOUND", "message": "Project not found"},
        )

    chart_type = payload.get("type") or payload.get("chart_type") or "gmv_trend"
    workspace_path = resolve_project_path(project.workspace_path)
    return render_chart(str(workspace_path), chart_type)


def chart_render_dashboard(project_id: str, payload: dict) -> ToolResult:
    service = ProjectService()
    project = service.get_project(project_id)
    if not project:
        return ToolResult(
            ok=False,
            action="chart.render_dashboard",
            summary="",
            error={"code": "NOT_FOUND", "message": "Project not found"},
        )

    requested = payload.get("chart_ids") or payload.get("charts")
    chart_ids: list[str] | None
    if requested in (None, "", "all"):
        chart_ids = list(DEFAULT_DASHBOARD_CHART_IDS)
    elif isinstance(requested, str):
        chart_ids = [item.strip() for item in requested.split(",") if item.strip()]
    elif isinstance(requested, list):
        chart_ids = [str(item).strip() for item in requested if str(item).strip()]
    else:
        return ToolResult(
            ok=False,
            action="chart.render_dashboard",
            summary="",
            error={"code": "INVALID_PAYLOAD", "message": "charts must be 'all', a comma string, or a list of chart ids"},
        )

    workspace_path = resolve_project_path(project.workspace_path)
    return render_dashboard_chart_artifacts(project_id, workspace_path, chart_ids)
