from pathlib import Path
from app.tools.schemas import ToolResult
from app.projects.service import ProjectService
from app.analysis.pipelines.build_panel import build_category_day_panel


def panel_build_category_day(project_id: str, payload: dict) -> ToolResult:
    service = ProjectService()
    project = service.get_project(project_id)
    if not project:
        return ToolResult(
            ok=False,
            action="panel.build_category_day",
            summary="",
            error={"code": "NOT_FOUND", "message": "Project not found"},
        )

    workspace_path = Path(project.workspace_path)
    return build_category_day_panel(project_id, str(workspace_path))
