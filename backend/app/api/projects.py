from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import Optional
from app.projects.schemas import (
    ProjectCreate, ProjectResponse,
    ProjectFileResponse, FileUploadResponse, SchemaInferResponse,
    FieldMappingRequest, DataSourceRequest, DataSourceResponse,
    DataDiscoverRequest, DataDiscoverResponse, DataIngestRequest, DataIngestResponse
)
from app.projects.service import ProjectService

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
