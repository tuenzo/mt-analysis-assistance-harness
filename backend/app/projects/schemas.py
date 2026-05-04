from pydantic import BaseModel, ConfigDict
from typing import Optional


class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    domain: Optional[str] = "promo_analysis"


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    workspace_path: str
    status: str
    current_stage: str


class FileUploadResponse(BaseModel):
    file_id: str
    role: str
    original_name: str
    status: str
    checksum: str


class ColumnInfo(BaseModel):
    name: str
    dtype: str
    mapped_to: Optional[str] = None
    confidence: float


class FileSchemaInfo(BaseModel):
    file_id: str
    role_guess: str
    columns: list[ColumnInfo]


class SchemaInferResponse(BaseModel):
    files: list[FileSchemaInfo]


class FieldMappingRequest(BaseModel):
    mappings: dict[str, dict[str, str]]


class ProjectFileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    role: str
    original_name: str
    current_path: str
    status: str
    checksum: str


class AgentMessageRequest(BaseModel):
    project_id: str
    session_id: Optional[str] = None
    message: str
    ui_context: Optional[dict] = None


class AgentMessageResponse(BaseModel):
    turn_id: str
    session_id: str
    status: str
    event_stream_url: str


class JobCreate(BaseModel):
    action: str
    input: Optional[dict] = None


class JobResponse(BaseModel):
    job_id: str
    status: str


class JobStateResponse(BaseModel):
    job_id: str
    action: str
    status: str
    progress: float
    current_step: Optional[str] = None


class ArtifactResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    type: str
    title: str
    path: str
