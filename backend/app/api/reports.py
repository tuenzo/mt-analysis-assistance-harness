import json
from typing import Any

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
    metadata = _read_report_metadata(report_path)
    return {
        "ok": True,
        "data": {
            "content": content,
            "path": str(report_path),
            "metadata": metadata,
            "kpi_summary": _extract_kpi_summary(metadata),
        },
    }


@router.post("/{project_id}/reports/export")
def export_report(project_id: str, req: ExportReportRequest):
    result = report_export(project_id, {
        "report_path": req.report_path,
        "format": req.format,
    })
    if not result.ok:
        raise HTTPException(status_code=400, detail=result.error)
    return {"ok": True, "result": result.model_dump()}


def _read_report_metadata(report_path: Path) -> dict[str, Any]:
    metadata_path = report_path.with_name("report_metadata.json")
    if not metadata_path.exists():
        return {}
    try:
        payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _extract_kpi_summary(metadata: dict[str, Any]) -> dict[str, Any]:
    results = metadata.get("evidence_index", {}).get("results", [])
    if not isinstance(results, list):
        return {}

    summary: dict[str, Any] = {}
    for result in results:
        if not isinstance(result, dict):
            continue
        name = result.get("name")
        metrics = result.get("key_metrics")
        if not isinstance(metrics, dict):
            continue
        if name == "diagnostics" and "total_gmv" in metrics:
            summary["total_gmv"] = metrics["total_gmv"]
        elif name == "localgap" and "total_local_gap" in metrics:
            summary["total_local_gap"] = metrics["total_local_gap"]
        elif name == "psm_did":
            if "did_estimate" in metrics:
                summary["did_estimate"] = metrics["did_estimate"]
            if "incremental_lift_pct" in metrics:
                summary["incremental_lift_pct"] = metrics["incremental_lift_pct"]
    return summary
