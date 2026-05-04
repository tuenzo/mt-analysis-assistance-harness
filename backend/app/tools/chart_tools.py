from pathlib import Path
from app.tools.schemas import ToolResult
from app.projects.service import ProjectService
from app.analysis.chart_renderer import render_chart


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

    chart_type = payload.get("type", "gmv_trend")
    workspace_path = Path(project.workspace_path)
    return render_chart(str(workspace_path), chart_type)
