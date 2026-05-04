from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from app.projects.schemas import FileUploadResponse, SchemaInferResponse, FieldMappingRequest
from app.projects.service import ProjectService

router = APIRouter(prefix="/projects", tags=["files"])
service = ProjectService()


@router.post("/{project_id}/files", response_model=FileUploadResponse)
async def upload_file(project_id: str, file: UploadFile = File(...), role: str = Form("unknown")):
    try:
        content = await file.read()
        pf = service.upload_file(project_id, content, file.filename or "unknown", role)
        return FileUploadResponse(
            file_id=pf.id,
            role=pf.role,
            original_name=pf.original_name,
            status=pf.status,
            checksum=pf.checksum,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{project_id}/files/infer-schema")
def infer_schema(project_id: str):
    result = service.infer_schema(project_id)
    return {"ok": True, "data": {"files": result}}


@router.post("/{project_id}/schema/apply")
def apply_schema(project_id: str, body: FieldMappingRequest):
    result = service.apply_schema(project_id, body.mappings)
    return {"ok": True, "data": result}
