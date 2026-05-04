import json
import csv
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional
from app.core.database import get_session
from app.core.config import settings
from app.projects.models import Project, ProjectFile
from app.workspace.manager import WorkspaceManager
from app.workspace.manifest import compute_file_checksum


class ProjectService:
    def __init__(self):
        self.workspace_manager = WorkspaceManager(settings.workspace_root)

    def create_project(self, name: str, domain: str = "promo_analysis", description: Optional[str] = None) -> Project:
        db = get_session()
        try:
            project_id = f"proj_{uuid.uuid4().hex[:12]}"
            workspace_path = self.workspace_manager.create_workspace(project_id)

            project = Project(
                id=project_id,
                name=name,
                description=description,
                workspace_path=str(workspace_path),
                domain=domain,
                status="created",
                current_stage="created",
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat(),
            )
            db.add(project)
            db.commit()
            db.refresh(project)
            return project
        finally:
            db.close()

    def get_project(self, project_id: str) -> Optional[Project]:
        db = get_session()
        try:
            return db.query(Project).filter(Project.id == project_id).first()
        finally:
            db.close()

    def list_projects(self) -> list[Project]:
        db = get_session()
        try:
            return db.query(Project).all()
        finally:
            db.close()

    def get_project_state(self, project_id: str) -> dict:
        db = get_session()
        try:
            project = db.query(Project).filter(Project.id == project_id).first()
            if not project:
                return {"error": "not_found"}

            files = db.query(ProjectFile).filter(ProjectFile.project_id == project_id).all()

            from app.projects.models import AnalysisSession, Job, Artifact, Report, MemoryCandidate
            sessions = db.query(AnalysisSession).filter(AnalysisSession.project_id == project_id).all()
            jobs = db.query(Job).filter(Job.project_id == project_id).order_by(Job.created_at.desc()).limit(5).all()
            artifacts = db.query(Artifact).filter(Artifact.project_id == project_id).order_by(Artifact.created_at.desc()).limit(10).all()
            reports = db.query(Report).filter(Report.project_id == project_id).order_by(Report.created_at.desc()).limit(1).all()
            memory_count = db.query(MemoryCandidate).filter(MemoryCandidate.project_id == project_id, MemoryCandidate.status == "pending").count()

            next_actions = []
            if not files:
                next_actions.append("upload_required_files")
            elif not any(f.role in ("order_info", "exposure_info", "activity_timeline") for f in files):
                next_actions.append("validate_data")

            return {
                "project": {
                    "id": project.id,
                    "name": project.name,
                    "status": project.status,
                    "current_stage": project.current_stage,
                    "created_at": project.created_at,
                },
                "files": [{"id": f.id, "role": f.role, "original_name": f.original_name, "status": f.status} for f in files],
                "latest_session": {"id": sessions[-1].id, "status": sessions[-1].status} if sessions else None,
                "latest_jobs": [{"id": j.id, "action": j.action, "status": j.status} for j in jobs],
                "latest_artifacts": [{"id": a.id, "type": a.type, "title": a.title} for a in artifacts],
                "latest_report": {"id": r.id, "status": r.status} if reports else None,
                "memory_candidates_count": memory_count,
                "next_actions": next_actions,
            }
        finally:
            db.close()

    def upload_file(self, project_id: str, file_content: bytes, original_name: str, role: str) -> ProjectFile:
        db = get_session()
        try:
            project = db.query(Project).filter(Project.id == project_id).first()
            if not project:
                raise ValueError(f"Project {project_id} not found")

            workspace_path = Path(project.workspace_path)
            safe_name = original_name.replace("/", "_").replace("\\", "_")
            file_path = workspace_path / "data" / "raw" / safe_name
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_bytes(file_content)

            checksum = compute_file_checksum(file_path)
            size_bytes = len(file_content)

            project_file = ProjectFile(
                project_id=project_id,
                role=role,
                original_name=original_name,
                current_path=str(file_path.relative_to(workspace_path)),
                size_bytes=size_bytes,
                checksum=checksum,
                status="uploaded",
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat(),
            )
            db.add(project_file)

            project.status = "data_uploaded"
            project.updated_at = datetime.now().isoformat()

            db.commit()
            db.refresh(project_file)
            return project_file
        finally:
            db.close()

    def list_files(self, project_id: str) -> list[ProjectFile]:
        db = get_session()
        try:
            return db.query(ProjectFile).filter(ProjectFile.project_id == project_id).all()
        finally:
            db.close()

    def infer_schema(self, project_id: str) -> list[dict]:
        db = get_session()
        try:
            files = db.query(ProjectFile).filter(ProjectFile.project_id == project_id).all()
            result = []

            KNOWN_COLUMNS = {
                "order_id": 0.98,
                "pay_time": 0.95,
                "date": 0.90,
                "gmv": 0.95,
                "discount": 0.90,
                "discount_amount": 0.85,
                "category": 0.95,
                "category_name": 0.90,
                "exposure": 0.90,
                "exposure_count": 0.85,
                "user_id": 0.90,
                "activity_id": 0.90,
                "activity_name": 0.85,
                "payday": 0.90,
            }

            ROLE_GUESS_KEYWORDS = {
                "order_info": ["order_id", "gmv", "pay_time", "discount"],
                "exposure_info": ["exposure", "exposure_count"],
                "activity_timeline": ["activity_id", "activity_name", "payday"],
            }

            for pf in files:
                workspace_path = Path(db.query(Project).filter(Project.id == project_id).first().workspace_path)
                file_path = workspace_path / pf.current_path

                columns = []
                role_guess = "unknown"

                if file_path.suffix == ".csv":
                    try:
                        with open(file_path, newline="", encoding="utf-8") as f:
                            reader = csv.DictReader(f)
                            headers = reader.fieldnames or []
                            for h in headers:
                                h_lower = h.lower().strip()
                                mapped = h
                                confidence = 0.5

                                for known, conf in KNOWN_COLUMNS.items():
                                    if known in h_lower:
                                        mapped = known
                                        confidence = conf
                                        break

                                columns.append({"name": h, "dtype": "string", "mapped_to": mapped, "confidence": confidence})

                            for role, keywords in ROLE_GUESS_KEYWORDS.items():
                                if all(any(k in h.lower() for h in headers) for k in keywords[:2]):
                                    role_guess = role
                                    break

                    except Exception:
                        columns = [{"name": "error", "dtype": "unknown", "mapped_to": None, "confidence": 0.0}]

                result.append({
                    "file_id": pf.id,
                    "role_guess": role_guess,
                    "columns": columns,
                })

            return result
        finally:
            db.close()

    def apply_schema(self, project_id: str, mappings: dict[str, dict[str, str]]) -> dict:
        db = get_session()
        try:
            for file_id, field_map in mappings.items():
                pf = db.query(ProjectFile).filter(ProjectFile.id == file_id, ProjectFile.project_id == project_id).first()
                if pf:
                    pf.schema_json = json.dumps(field_map)
                    pf.status = "mapped"
                    pf.updated_at = datetime.now().isoformat()

            project = db.query(Project).filter(Project.id == project_id).first()
            if project:
                project.current_stage = "schema_mapping"
                project.updated_at = datetime.now().isoformat()

            db.commit()
            return {"status": "mapped"}
        finally:
            db.close()
