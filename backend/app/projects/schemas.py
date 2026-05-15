from pydantic import BaseModel, ConfigDict
from typing import Optional


class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    domain: Optional[str] = "promo_analysis"
    is_test: Optional[bool] = None


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    workspace_path: str
    status: str
    current_stage: str
    is_test: bool = False
    data_source_path: Optional[str] = None


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


class DataSourceRequest(BaseModel):
    path: str


class DataSourceResponse(BaseModel):
    data_source_path: Optional[str] = None


class DataIngestRequest(BaseModel):
    source_path: Optional[str] = None
    mode: Optional[str] = "scan_project_source"
    roles: Optional[dict[str, str]] = None
    selected_files: Optional[list[dict[str, str]]] = None


class DataDiscoverRequest(BaseModel):
    source_path: Optional[str] = None


class SourceFileCandidate(BaseModel):
    name: str
    source_path: str
    size_bytes: Optional[int] = None
    modified_at: Optional[str] = None
    extension: str
    kind: str
    skipped: bool = False
    skip_reason: Optional[str] = None
    headers: list[str] = []
    preview: str = ""
    preview_truncated: bool = False
    role_guess: str = "unknown"
    role_confidence: float = 0.0
    role_reason: str = "not_classified"
    looks_processed_panel: bool = False


class DataDiscoverResponse(BaseModel):
    source_path: str
    candidates: list[SourceFileCandidate]
    candidate_count: int


class ImportedFileInfo(BaseModel):
    file_id: str
    role: str
    original_name: str
    current_path: str
    checksum: str
    reason: Optional[str] = None


class SkippedFileInfo(BaseModel):
    name: str
    reason: str


class DataIngestResponse(BaseModel):
    imported_count: int
    skipped_count: int
    imported: list[ImportedFileInfo]
    skipped: list[SkippedFileInfo]
    source_path: str


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
