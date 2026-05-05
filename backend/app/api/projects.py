import json

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import Optional
from app.projects.schemas import (
    ProjectCreate, ProjectResponse,
    ProjectFileResponse, FileUploadResponse, SchemaInferResponse,
    FieldMappingRequest, DataSourceRequest, DataSourceResponse,
    DataDiscoverRequest, DataDiscoverResponse, DataIngestRequest, DataIngestResponse
)
from app.projects.service import ProjectService
from app.core.database import get_session
from app.projects.models import AgentEvent, ApprovalRequest, Artifact, Job, ToolCall

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
