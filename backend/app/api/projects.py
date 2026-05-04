from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import Optional
from app.projects.schemas import (
    ProjectCreate, ProjectResponse,
    ProjectFileResponse, FileUploadResponse, SchemaInferResponse,
    FieldMappingRequest
)
from app.projects.service import ProjectService

router = APIRouter(prefix="/projects", tags=["projects"])
service = ProjectService()


@router.post("", response_model=ProjectResponse)
def create_project(body: ProjectCreate):
    project = service.create_project(body.name, body.domain, body.description)
    return ProjectResponse(
        id=project.id,
        name=project.name,
        workspace_path=project.workspace_path,
        status=project.status,
        current_stage=project.current_stage,
    )


@router.get("")
def list_projects():
    projects = service.list_projects()
    return {"ok": True, "data": [{"id": p.id, "name": p.name, "status": p.status, "created_at": p.created_at} for p in projects]}


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
