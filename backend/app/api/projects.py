import base64
import json
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from typing import Any, Optional
from app.projects.schemas import (
    ProjectCreate, ProjectResponse,
    ProjectFileResponse, FileUploadResponse, SchemaInferResponse,
    FieldMappingRequest, DataSourceRequest, DataSourceResponse,
    DataDiscoverRequest, DataDiscoverResponse, DataIngestRequest, DataIngestResponse
)
from app.projects.service import ProjectService
from app.core.config import resolve_project_path
from app.core.database import get_session
from app.projects.models import AgentEvent, ApprovalRequest, Artifact, Job, ToolCall
from app.analysis.dashboard_chart_renderer import CHART_IDS
from app.artifacts.service import mime_type_for_path

router = APIRouter(prefix="/projects", tags=["projects"])
service = ProjectService()


@router.post("", response_model=ProjectResponse)
def create_project(body: ProjectCreate):
    project = service.create_project(body.name, body.domain, body.description, body.is_test)
    return ProjectResponse(
        id=project.id,
        name=project.name,
        workspace_path=project.workspace_path,
        status=project.status,
        current_stage=project.current_stage,
        is_test=bool(project.is_test),
        data_source_path=project.data_source_path,
    )


@router.get("")
def list_projects():
    projects = service.list_projects()
    return {"ok": True, "data": [{"id": p.id, "name": p.name, "status": p.status, "created_at": p.created_at, "is_test": bool(p.is_test), "data_source_path": p.data_source_path} for p in projects]}


@router.get("/{project_id}")
def get_project(project_id: str):
    project = service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"ok": True, "data": {
        "id": project.id,
        "name": project.name,
        "workspace_path": project.workspace_path,
        "status": project.status,
        "current_stage": project.current_stage,
        "is_test": bool(project.is_test),
        "data_source_path": project.data_source_path,
    }}


@router.get("/{project_id}/state")
def get_project_state(project_id: str):
    state = service.get_project_state(project_id)
    if "error" in state:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"ok": True, "data": state}


@router.get("/{project_id}/artifacts")
def list_artifacts(project_id: str, type: str | None = None, job_id: str | None = None, tool_call_id: str | None = None):
    db = get_session()
    try:
        query = db.query(Artifact).filter(Artifact.project_id == project_id)
        if type:
            query = query.filter(Artifact.type == type)
        if job_id:
            query = query.filter(Artifact.job_id == job_id)
        if tool_call_id:
            query = query.filter(Artifact.tool_call_id == tool_call_id)
        artifacts = query.order_by(Artifact.created_at.desc()).all()
        return {
            "ok": True,
            "data": [
                {
                    "id": artifact.id,
                    "project_id": artifact.project_id,
                    "job_id": artifact.job_id,
                    "tool_call_id": artifact.tool_call_id,
                    "type": artifact.type,
                    "title": artifact.title,
                    "path": artifact.path,
                    "mime_type": artifact.mime_type,
                    "metadata_json": artifact.metadata_json,
                    "checksum": artifact.checksum,
                    "created_at": artifact.created_at,
                }
                for artifact in artifacts
            ],
        }
    finally:
        db.close()


@router.get("/{project_id}/artifacts/content")
def read_artifact_content_by_path(project_id: str, path: str):
    project = service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    artifact_path = _resolve_workspace_path(project.workspace_path, path)
    artifact = {
        "id": f"path:{path}",
        "project_id": project_id,
        "job_id": None,
        "tool_call_id": None,
        "type": _artifact_type_for_path(path),
        "title": Path(path).name,
        "path": path,
        "mime_type": mime_type_for_path(path),
        "metadata_json": None,
        "checksum": None,
        "created_at": None,
    }
    return {"ok": True, "data": _read_artifact_file(artifact_path, artifact)}


@router.get("/{project_id}/artifacts/{artifact_id}")
def get_project_artifact(project_id: str, artifact_id: str):
    db = get_session()
    try:
        artifact = db.query(Artifact).filter(Artifact.project_id == project_id, Artifact.id == artifact_id).first()
        if not artifact:
            raise HTTPException(status_code=404, detail="Artifact not found")
        return {"ok": True, "data": _serialize_artifact(artifact)}
    finally:
        db.close()


@router.get("/{project_id}/artifacts/{artifact_id}/content")
def read_project_artifact_content(project_id: str, artifact_id: str):
    project = service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    db = get_session()
    try:
        artifact = db.query(Artifact).filter(Artifact.project_id == project_id, Artifact.id == artifact_id).first()
        if not artifact:
            raise HTTPException(status_code=404, detail="Artifact not found")
        artifact_path = _resolve_workspace_path(project.workspace_path, artifact.path)
        return {"ok": True, "data": _read_artifact_file(artifact_path, _serialize_artifact(artifact))}
    finally:
        db.close()


@router.get("/{project_id}/dashboard-charts/{chart_id}.png")
def read_dashboard_chart(project_id: str, chart_id: str):
    project = service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if chart_id not in CHART_IDS:
        raise HTTPException(status_code=404, detail="Dashboard chart not found")

    workspace = resolve_project_path(project.workspace_path)
    chart_path = (workspace / "artifacts" / "charts" / "dashboard" / f"{chart_id}.png").resolve()
    try:
        chart_path.relative_to(workspace)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Dashboard chart path must stay within the project workspace") from exc
    if not chart_path.exists() or not chart_path.is_file():
        raise HTTPException(status_code=404, detail="Dashboard chart has not been generated yet. Run chart.render_dashboard first.")

    return FileResponse(
        chart_path,
        media_type="image/png",
        headers={"Cache-Control": "no-store"},
    )


@router.get("/{project_id}/timeline")
def get_project_timeline(project_id: str):
    db = get_session()
    try:
        jobs = (
            db.query(Job)
            .filter(Job.project_id == project_id)
            .order_by(Job.created_at.desc(), Job.id.desc())
            .limit(30)
            .all()
        )
        tool_calls = (
            db.query(ToolCall)
            .filter(ToolCall.project_id == project_id)
            .order_by(ToolCall.created_at.desc(), ToolCall.id.desc())
            .limit(80)
            .all()
        )
        approvals = (
            db.query(ApprovalRequest)
            .filter(ApprovalRequest.project_id == project_id)
            .order_by(ApprovalRequest.created_at.desc(), ApprovalRequest.id.desc())
            .limit(40)
            .all()
        )
        events = (
            db.query(AgentEvent)
            .filter(AgentEvent.project_id == project_id)
            .order_by(AgentEvent.created_at.desc(), AgentEvent.id.desc())
            .limit(120)
            .all()
        )
        return {
            "ok": True,
            "data": {
                "jobs": [
                    {
                        "id": job.id,
                        "action": job.action,
                        "status": job.status,
                        "progress": job.progress or 0,
                        "started_at": job.started_at,
                        "finished_at": job.finished_at,
                        "created_at": job.created_at,
                        "error_message": job.error_message,
                    }
                    for job in jobs
                ],
                "tool_calls": [
                    {
                        "id": call.id,
                        "turn_id": call.turn_id,
                        "action": call.action,
                        "status": call.status,
                        "summary": _tool_call_summary(call.result_json),
                        "created_at": call.created_at,
                        "completed_at": call.completed_at,
                        "error_message": call.error_message,
                    }
                    for call in tool_calls
                ],
                "approvals": [
                    {
                        "id": approval.id,
                        "turn_id": approval.turn_id,
                        "action": approval.action,
                        "status": approval.status,
                        "risk_level": approval.risk_level,
                        "reason": approval.reason or "",
                        "created_at": approval.created_at,
                        "resolved_at": approval.resolved_at,
                    }
                    for approval in approvals
                ],
                "events": [
                    {
                        "id": event.id,
                        "turn_id": event.turn_id,
                        "type": event.type,
                        "created_at": event.created_at,
                        "payload": _event_payload(event.payload_json),
                    }
                    for event in events
                ],
            },
        }
    finally:
        db.close()


def _tool_call_summary(result_json: str | None) -> str:
    if not result_json:
        return ""
    try:
        data = json.loads(result_json)
    except json.JSONDecodeError:
        return ""
    return str(data.get("summary") or "")


def _event_payload(payload_json: str | None) -> dict:
    if not payload_json:
        return {}
    try:
        return json.loads(payload_json)
    except json.JSONDecodeError:
        return {}


def _serialize_artifact(artifact: Artifact) -> dict[str, Any]:
    metadata_json = artifact.metadata_json
    if metadata_json is not None and not isinstance(metadata_json, str):
        metadata_json = json.dumps(metadata_json, ensure_ascii=False)
    return {
        "id": artifact.id,
        "project_id": artifact.project_id,
        "job_id": artifact.job_id,
        "tool_call_id": artifact.tool_call_id,
        "type": artifact.type,
        "title": artifact.title,
        "path": artifact.path,
        "mime_type": artifact.mime_type,
        "metadata_json": metadata_json,
        "checksum": artifact.checksum,
        "created_at": artifact.created_at,
    }


def _resolve_workspace_path(workspace_path: str, artifact_path: str) -> Path:
    workspace = resolve_project_path(workspace_path)
    candidate = Path(artifact_path)
    resolved = candidate.resolve() if candidate.is_absolute() else (workspace / candidate).resolve()
    try:
        resolved.relative_to(workspace)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Artifact path must stay within the project workspace") from exc
    if not resolved.exists() or not resolved.is_file():
        raise HTTPException(status_code=404, detail="Artifact file not found")
    return resolved


def _read_artifact_file(path: Path, artifact: dict[str, Any]) -> dict[str, Any]:
    content_type = artifact.get("mime_type") or mime_type_for_path(str(path))
    size_bytes = path.stat().st_size
    if content_type == "application/json" or path.suffix.lower() == ".json":
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail=f"Artifact JSON could not be parsed: {exc}") from exc
        encoding = "json"
    elif content_type.startswith("text/") or path.suffix.lower() in {".md", ".csv", ".txt", ".log", ".yaml", ".yml"}:
        data = path.read_text(encoding="utf-8")
        encoding = "text"
    else:
        data = base64.b64encode(path.read_bytes()).decode("ascii")
        encoding = "base64"

    return {
        "artifact": artifact,
        "content_type": content_type,
        "encoding": encoding,
        "data": data,
        "size_bytes": size_bytes,
    }


def _artifact_type_for_path(path: str) -> str:
    lower = path.lower()
    if "/charts/" in lower.replace("\\", "/") or lower.endswith("_chart.json"):
        return "chart"
    if lower.endswith(".csv"):
        return "table"
    if lower.endswith(".md"):
        return "report"
    if lower.endswith(".png") or lower.endswith(".jpg") or lower.endswith(".jpeg") or lower.endswith(".webp"):
        return "image"
    return "artifact"


@router.get("/{project_id}/files", response_model=list[ProjectFileResponse])
def list_files(project_id: str):
    files = service.list_files(project_id)
    return [{"id": f.id, "role": f.role, "original_name": f.original_name, "current_path": f.current_path, "status": f.status, "checksum": f.checksum} for f in files]


@router.get("/{project_id}/data-source")
def get_data_source(project_id: str):
    project = service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"ok": True, "data": DataSourceResponse(data_source_path=project.data_source_path).model_dump()}


@router.put("/{project_id}/data-source")
def set_data_source(project_id: str, body: DataSourceRequest):
    try:
        path = service.set_data_source_path(project_id, body.path)
        return {"ok": True, "data": DataSourceResponse(data_source_path=path).model_dump()}
    except ValueError as e:
        message = str(e)
        status_code = 404 if "not found" in message.lower() else 400
        raise HTTPException(status_code=status_code, detail=message)


@router.post("/{project_id}/data-source/ingest")
def ingest_data_source(project_id: str, body: DataIngestRequest | None = None):
    body = body or DataIngestRequest()
    try:
        result = service.ingest_data_source(project_id, body.source_path, body.roles, body.selected_files)
        return {"ok": True, "data": DataIngestResponse(**result).model_dump()}
    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        message = str(e)
        status_code = 404 if "not found" in message.lower() else 400
        raise HTTPException(status_code=status_code, detail=message)


@router.post("/{project_id}/data-source/discover")
def discover_data_source(project_id: str, body: DataDiscoverRequest | None = None):
    body = body or DataDiscoverRequest()
    try:
        result = service.discover_source_files(project_id, body.source_path)
        return {"ok": True, "data": DataDiscoverResponse(**result).model_dump()}
    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        message = str(e)
        status_code = 404 if "not found" in message.lower() else 400
        raise HTTPException(status_code=status_code, detail=message)
