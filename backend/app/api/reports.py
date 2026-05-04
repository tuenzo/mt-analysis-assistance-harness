from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.projects.service import ProjectService
from app.tools.report_tools import report_generate, report_export
from pathlib import Path

router = APIRouter(prefix="/projects", tags=["reports"])


class GenerateReportRequest(BaseModel):
    format: str = "md"


class ExportReportRequest(BaseModel):
    report_path: str = ""
    format: str = "md"


@router.post("/{project_id}/reports/generate")
def generate_report(project_id: str, req: GenerateReportRequest):
    result = report_generate(project_id, {"format": req.format})
    if not result.ok:
        raise HTTPException(status_code=400, detail=result.error)
    return {"ok": True, "result": result.model_dump()}


@router.get("/{project_id}/reports/latest")
def get_latest_report(project_id: str):
    service = ProjectService()
    project = service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    report_path = Path(project.workspace_path) / "reports" / "report.md"
    if not report_path.exists():
        raise HTTPException(status_code=404, detail="Report not found")

    content = report_path.read_text(encoding="utf-8")
    return {"ok": True, "data": {"content": content, "path": str(report_path)}}


@router.post("/{project_id}/reports/export")
def export_report(project_id: str, req: ExportReportRequest):
    result = report_export(project_id, {
        "report_path": req.report_path,
        "format": req.format,
    })
    if not result.ok:
        raise HTTPException(status_code=400, detail=result.error)
    return {"ok": True, "result": result.model_dump()}
