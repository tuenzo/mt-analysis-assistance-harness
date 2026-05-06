from pathlib import Path
from app.tools.schemas import ToolResult
from app.projects.service import ProjectService
from app.reports.renderer import render_report, export_report as do_export


def report_generate(project_id: str, payload: dict) -> ToolResult:
    service = ProjectService()
    project = service.get_project(project_id)
    if not project:
        return ToolResult(
            ok=False,
            action="report.generate",
            summary="",
            error={"code": "NOT_FOUND", "message": "Project not found"},
        )

    fmt = payload.get("format", "md")
    workspace_path = Path(project.workspace_path)
    return render_report(project_id, str(workspace_path), fmt, project_name=project.name)


def report_export(project_id: str, payload: dict) -> ToolResult:
    service = ProjectService()
    project = service.get_project(project_id)
    if not project:
        return ToolResult(
            ok=False,
            action="report.export",
            summary="",
            error={"code": "NOT_FOUND", "message": "Project not found"},
        )

    report_path = payload.get("report_path", "")
    export_format = payload.get("format", "md")

    workspace_path = Path(project.workspace_path)
    if report_path:
        full_path = workspace_path / report_path
    else:
        full_path = workspace_path / "reports" / "report.md"

    if not full_path.exists():
        return ToolResult(
            ok=False,
            action="report.export",
            summary="",
            error={"code": "NOT_FOUND", "message": "报告文件不存在"},
        )

    return do_export(str(full_path), export_format)
