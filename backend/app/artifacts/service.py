import json
import mimetypes
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional
from app.core.database import get_session
from app.projects.models import Artifact, Project, Report
from app.tools.schemas import ToolResult
from app.workspace.manifest import AssetEntry, ProjectManifest, compute_file_checksum


def mime_type_for_path(path: str) -> str:
    guessed, _ = mimetypes.guess_type(path)
    if guessed:
        return guessed
    if path.lower().endswith(".json"):
        return "application/json"
    return "application/octet-stream"


def persist_tool_result_artifacts(
    db,
    *,
    project_id: str,
    result: ToolResult,
    job_id: str | None = None,
    tool_call_id: str | None = None,
    commit: bool = True,
) -> list[Artifact]:
    persisted: list[Artifact] = []
    for item in result.artifacts or []:
        path = item.get("path")
        if not path:
            continue
        path = str(path)
        artifact = (
            db.query(Artifact)
            .filter(Artifact.project_id == project_id, Artifact.path == path)
            .first()
        )
        if not artifact:
            artifact = Artifact(
                id=f"art_{uuid.uuid4().hex[:12]}",
                project_id=project_id,
                path=path,
                created_at=datetime.now().isoformat(),
            )
            db.add(artifact)

        artifact.job_id = job_id
        artifact.tool_call_id = tool_call_id
        artifact.type = str(item.get("type") or "artifact")
        artifact.title = str(item.get("title") or path)
        artifact.mime_type = str(item.get("mime_type") or mime_type_for_path(path))
        artifact.metadata_json = json.dumps(
            {key: value for key, value in item.items() if key not in {"type", "title", "path", "mime_type"}},
            ensure_ascii=False,
        )
        artifact.checksum = _artifact_checksum(db, project_id, path)
        db.add(artifact)
        persisted.append(artifact)

        if artifact.type == "report":
            report = (
                db.query(Report)
                .filter(Report.project_id == project_id, Report.source_md_path == artifact.path)
                .first()
            )
            if not report:
                report = Report(
                    id=f"rep_{uuid.uuid4().hex[:12]}",
                    project_id=project_id,
                    source_md_path=artifact.path,
                    created_at=datetime.now().isoformat(),
                )
                db.add(report)
            report.job_id = job_id
            report.status = "ready"
            report.title = artifact.title
            report.metadata_json = json.dumps({"artifact_id": artifact.id}, ensure_ascii=False)
            report.updated_at = datetime.now().isoformat()

    _sync_manifest_assets(db, project_id, persisted)
    if commit:
        db.commit()
        for artifact in persisted:
            db.refresh(artifact)
    return persisted


def _artifact_checksum(db, project_id: str, artifact_path: str) -> str | None:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        return None

    workspace = Path(project.workspace_path).resolve()
    candidate = Path(artifact_path)
    resolved = candidate.resolve() if candidate.is_absolute() else (workspace / candidate).resolve()
    try:
        resolved.relative_to(workspace)
    except ValueError:
        return None
    if not resolved.exists() or not resolved.is_file():
        return None
    return compute_file_checksum(resolved)


def _sync_manifest_assets(db, project_id: str, artifacts: list[Artifact]) -> None:
    if not artifacts:
        return

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        return

    workspace = Path(project.workspace_path)
    try:
        manifest = ProjectManifest.load(workspace)
    except FileNotFoundError:
        return

    by_path: dict[str, AssetEntry] = {}
    ordered_paths: list[str] = []
    for entry in manifest.derived_assets:
        path = entry.get("path") if isinstance(entry, dict) else getattr(entry, "path", None)
        if not path:
            continue
        ordered_paths.append(path)
        by_path[path] = _asset_entry_from_manifest(entry)

    for artifact in artifacts:
        if artifact.path not in ordered_paths:
            ordered_paths.append(artifact.path)
        by_path[artifact.path] = AssetEntry(
            asset_id=artifact.id,
            role=artifact.type,
            path=artifact.path,
            checksum=artifact.checksum,
            created_at=artifact.created_at,
        )

    manifest.derived_assets = [by_path[path] for path in ordered_paths if path in by_path]
    manifest.version += 1
    manifest.save(workspace)


def _asset_entry_from_manifest(entry) -> AssetEntry:
    if isinstance(entry, AssetEntry):
        return entry
    return AssetEntry(
        asset_id=str(entry.get("asset_id") or entry.get("id") or ""),
        role=str(entry.get("role") or "artifact"),
        path=str(entry.get("path") or ""),
        source_file_ids=list(entry.get("source_file_ids") or []),
        checksum=entry.get("checksum"),
        created_at=entry.get("created_at"),
    )


class ArtifactService:
    """Artifact 注册与管理"""

    def register_artifact(
        self,
        project_id: str,
        artifact_type: str,
        title: str,
        path: str,
        metadata: Optional[dict] = None,
    ) -> Artifact:
        db = get_session()
        try:
            artifact = Artifact(
                id=f"art_{uuid.uuid4().hex[:12]}",
                project_id=project_id,
                type=artifact_type,
                title=title,
                path=path,
                mime_type=mime_type_for_path(path),
                metadata_json=json.dumps(metadata or {}, ensure_ascii=False),
                created_at=datetime.now().isoformat(),
            )
            db.add(artifact)
            db.commit()
            db.refresh(artifact)
            return artifact
        finally:
            db.close()

    def list_artifacts(self, project_id: str, artifact_type: Optional[str] = None) -> list[Artifact]:
        db = get_session()
        try:
            query = db.query(Artifact).filter(Artifact.project_id == project_id)
            if artifact_type:
                query = query.filter(Artifact.type == artifact_type)
            return query.order_by(Artifact.created_at.desc()).all()
        finally:
            db.close()

    def get_artifact(self, artifact_id: str) -> Optional[Artifact]:
        db = get_session()
        try:
            return db.query(Artifact).filter(Artifact.id == artifact_id).first()
        finally:
            db.close()
