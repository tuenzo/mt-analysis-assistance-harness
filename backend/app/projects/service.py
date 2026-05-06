import json
import csv
import uuid
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional
from app.core.database import get_session
from app.core.config import get_demo_project_id, is_demo_mode, is_test_mode, settings
from app.projects.models import Project, ProjectFile
from app.workspace.manager import WorkspaceManager
from app.workspace.manifest import FileEntry, ProjectManifest, compute_file_checksum
from app.workspace.context_summary import ContextSummaryWriter


class ProjectService:
    VALID_DATA_ROLES = {"order_info", "exposure_info", "activity_timeline", "unknown"}
    PREVIEW_BYTE_LIMIT = 64 * 1024
    PREVIEW_LINE_LIMIT = 200

    def __init__(self):
        self.workspace_manager = WorkspaceManager(settings.workspace_root)

    def create_project(
        self,
        name: str,
        domain: str = "promo_analysis",
        description: Optional[str] = None,
        is_test: Optional[bool] = None,
    ) -> Project:
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
                is_test=1 if (is_test if is_test is not None else is_test_mode()) else 0,
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
            query = db.query(Project).filter(Project.id == project_id)
            if not self._can_read_hidden_project(project_id):
                query = query.filter(Project.is_test == 0)
            return query.first()
        finally:
            db.close()

    def list_projects(self) -> list[Project]:
        db = get_session()
        try:
            query = db.query(Project)
            if not is_test_mode():
                query = query.filter(Project.is_test == 0)
            return query.order_by(Project.created_at.desc()).all()
        finally:
            db.close()

    def get_project_state(self, project_id: str) -> dict:
        db = get_session()
        try:
            query = db.query(Project).filter(Project.id == project_id)
            if not self._can_read_hidden_project(project_id):
                query = query.filter(Project.is_test == 0)
            project = query.first()
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
                    "data_source_path": project.data_source_path,
                    "created_at": project.created_at,
                },
                "files": [{"id": f.id, "role": f.role, "original_name": f.original_name, "status": f.status} for f in files],
                "latest_session": {"id": sessions[-1].id, "status": sessions[-1].status} if sessions else None,
                "latest_jobs": [{"id": j.id, "action": j.action, "status": j.status} for j in jobs],
                "latest_artifacts": [{"id": a.id, "type": a.type, "title": a.title} for a in artifacts],
                "latest_report": {"id": reports[0].id, "status": reports[0].status} if reports else None,
                "memory_candidates_count": memory_count,
                "next_actions": next_actions,
                "files_count": len(files),
                "sessions_count": len(sessions),
                "artifacts_count": len(artifacts),
                "reports_count": len(reports),
                "current_stage": project.current_stage,
                "last_activity": project.updated_at,
            }
        finally:
            db.close()

    def upload_file(self, project_id: str, file_content: bytes, original_name: str, role: str) -> ProjectFile:
        db = get_session()
        try:
            query = db.query(Project).filter(Project.id == project_id)
            if not self._can_read_hidden_project(project_id):
                query = query.filter(Project.is_test == 0)
            project = query.first()
            if not project:
                raise ValueError(f"Project {project_id} not found")

            project_file = self._register_file_bytes(db, project, file_content, original_name, role)

            db.commit()
            db.refresh(project_file)
            return project_file
        finally:
            db.close()

    def get_data_source_path(self, project_id: str) -> Optional[str]:
        project = self.get_project(project_id)
        return project.data_source_path if project else None

    def set_data_source_path(self, project_id: str, source_path: str) -> str:
        db = get_session()
        try:
            project = self._query_project(db, project_id)
            if not project:
                raise ValueError(f"Project {project_id} not found")

            resolved = Path(source_path).expanduser()
            if not resolved.is_absolute():
                raise ValueError("Data source path must be an absolute path")
            if not resolved.exists() or not resolved.is_dir():
                raise ValueError("Data source path must be an existing directory")

            project.data_source_path = str(resolved)
            project.updated_at = datetime.now().isoformat()
            db.commit()
            return project.data_source_path
        finally:
            db.close()

    def ingest_data_source(
        self,
        project_id: str,
        source_path: Optional[str] = None,
        roles: Optional[dict[str, str]] = None,
        selected_files: Optional[list[dict[str, str]]] = None,
    ) -> dict:
        db = get_session()
        try:
            project = self._query_project(db, project_id)
            if not project:
                raise ValueError(f"Project {project_id} not found")

            source_dir = self._resolve_source_dir(project, source_path)
            if not selected_files:
                raise ValueError("selected_files is required; run data.discover_source_files before data.ingest")

            imported: list[dict] = []
            skipped: list[dict] = []
            role_overrides = roles or {}

            for selection in selected_files:
                raw_source = selection.get("source_path") or selection.get("path") or selection.get("name")
                if not raw_source:
                    skipped.append({"name": "", "reason": "missing_source_path"})
                    continue
                child = self._resolve_direct_child(source_dir, raw_source)
                if not child.exists() or not child.is_file():
                    skipped.append({"name": Path(raw_source).name, "reason": "not_a_file"})
                    continue
                if child.suffix.lower() != ".csv":
                    skipped.append({"name": child.name, "reason": "unsupported_file_type"})
                    continue

                role = selection.get("role") or role_overrides.get(child.name) or "unknown"
                if role not in self.VALID_DATA_ROLES:
                    skipped.append({"name": child.name, "reason": f"invalid_role:{role}"})
                    continue
                reason = selection.get("reason") or ""
                project_file = self._register_file_path(db, project, child, role)
                imported.append({
                    "file_id": project_file.id,
                    "role": project_file.role,
                    "original_name": project_file.original_name,
                    "current_path": project_file.current_path,
                    "checksum": project_file.checksum,
                    "reason": reason,
                })

            if imported:
                project.status = "data_uploaded"
                project.current_stage = "data_uploaded"
                project.updated_at = datetime.now().isoformat()
                self._sync_workspace_state(db, project)

            db.commit()
            return {
                "imported_count": len(imported),
                "skipped_count": len(skipped),
                "imported": imported,
                "skipped": skipped,
                "source_path": str(source_dir),
            }
        finally:
            db.close()

    def discover_source_files(self, project_id: str, source_path: Optional[str] = None) -> dict:
        project = self.get_project(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")

        source_dir = self._resolve_source_dir(project, source_path)
        candidates = []
        for child in sorted(source_dir.iterdir(), key=lambda p: p.name.lower()):
            candidates.append(self._build_source_candidate(child))

        return {
            "source_path": str(source_dir),
            "candidates": candidates,
            "candidate_count": len(candidates),
        }

    def list_files(self, project_id: str) -> list[ProjectFile]:
        db = get_session()
        try:
            query = db.query(Project).filter(Project.id == project_id)
            if not self._can_read_hidden_project(project_id):
                query = query.filter(Project.is_test == 0)
            if not query.first():
                return []
            return db.query(ProjectFile).filter(ProjectFile.project_id == project_id).all()
        finally:
            db.close()

    def infer_schema(self, project_id: str) -> list[dict]:
        db = get_session()
        try:
            query = db.query(Project).filter(Project.id == project_id)
            if not self._can_read_hidden_project(project_id):
                query = query.filter(Project.is_test == 0)
            project = query.first()
            if not project:
                return []

            files = db.query(ProjectFile).filter(ProjectFile.project_id == project_id).all()
            result = []
            from app.analysis.pipelines.build_panel import ROLE_ALIASES, infer_schema_from_columns

            for pf in files:
                workspace_path = Path(project.workspace_path)
                file_path = workspace_path / pf.current_path
                headers: list[str] = []

                if file_path.suffix == ".csv":
                    try:
                        with open(file_path, newline="", encoding="utf-8-sig", errors="replace") as f:
                            reader = csv.DictReader(f)
                            headers = reader.fieldnames or []
                    except Exception:
                        headers = []

                role_scores = {
                    role: len(infer_schema_from_columns(headers, role))
                    for role in ROLE_ALIASES
                }
                role_guess = pf.role if pf.role != "unknown" else max(role_scores, key=role_scores.get, default="unknown")
                recommended_mappings = infer_schema_from_columns(headers, role_guess) if role_guess in ROLE_ALIASES else {}
                mapped_sources = {source: standard for standard, source in recommended_mappings.items()}
                columns = [
                    {
                        "name": header,
                        "dtype": "string",
                        "mapped_to": mapped_sources.get(header),
                        "confidence": 0.95 if header in mapped_sources else 0.5,
                    }
                    for header in headers
                ]

                result.append({
                    "file_id": pf.id,
                    "role": pf.role,
                    "role_guess": role_guess,
                    "columns": columns,
                    "recommended_mappings": recommended_mappings,
                })

            return result
        finally:
            db.close()

    def apply_schema(self, project_id: str, mappings: dict[str, dict[str, str]]) -> dict:
        db = get_session()
        try:
            project = db.query(Project).filter(Project.id == project_id)
            if not self._can_read_hidden_project(project_id):
                project = project.filter(Project.is_test == 0)
            project = project.first()
            if not project:
                return {"status": "not_found"}

            for file_id, field_map in mappings.items():
                pf = db.query(ProjectFile).filter(ProjectFile.id == file_id, ProjectFile.project_id == project_id).first()
                if pf:
                    pf.schema_json = json.dumps(field_map)
                    pf.status = "mapped"
                    pf.updated_at = datetime.now().isoformat()

            project.current_stage = "schema_mapping"
            project.updated_at = datetime.now().isoformat()

            db.commit()
            return {"status": "mapped"}
        finally:
            db.close()

    def mark_data_validation(
        self,
        project_id: str,
        validation_ok: bool,
        file_info: dict[str, dict],
        issues: list[str],
        warnings: list[str],
    ) -> dict:
        db = get_session()
        try:
            project = self._query_project(db, project_id)
            if not project:
                return {}

            project_files = db.query(ProjectFile).filter(ProjectFile.project_id == project_id).all()
            now = datetime.now().isoformat()
            if validation_ok:
                for project_file in project_files:
                    if project_file.role in file_info:
                        project_file.status = "validated"
                        project_file.updated_at = now
                project.status = "data_validated"
                project.current_stage = "data_validated"
            else:
                project.status = "data_partial" if project_files else "created"
                project.current_stage = "data_partial" if project_files else "created"

            project.updated_at = now
            self._sync_workspace_state(
                db,
                project,
                schema_status="validated" if validation_ok else "validation_failed",
                completed_tasks="data_ingest,data_validate" if validation_ok else "data_ingest",
                next_steps=(
                    "Run panel.build_category_day"
                    if validation_ok
                    else "Fix validation issues: " + "; ".join(issues[:5])
                ),
                extra_lines=[
                    f"Validation warnings: {'; '.join(warnings[:5]) if warnings else 'none'}",
                    f"Validation issues: {'; '.join(issues[:5]) if issues else 'none'}",
                ],
            )
            db.commit()
            return {"current_stage": project.current_stage, "data_quality": "validated" if validation_ok else "partial"}
        finally:
            db.close()

    def _query_project(self, db, project_id: str) -> Optional[Project]:
        query = db.query(Project).filter(Project.id == project_id)
        if not self._can_read_hidden_project(project_id):
            query = query.filter(Project.is_test == 0)
        return query.first()

    @staticmethod
    def _can_read_hidden_project(project_id: str) -> bool:
        return is_test_mode() or project_id == get_demo_project_id()

    def _register_file_bytes(self, db, project: Project, file_content: bytes, original_name: str, role: str) -> ProjectFile:
        workspace_path = Path(project.workspace_path)
        safe_name = self._safe_filename(original_name)
        file_path = self._unique_raw_path(workspace_path, safe_name)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(file_content)

        project_file = self._create_project_file_record(
            db=db,
            project=project,
            role=role,
            original_name=original_name,
            file_path=file_path,
            size_bytes=len(file_content),
        )
        project.status = "data_uploaded"
        project.current_stage = "data_uploaded"
        project.updated_at = datetime.now().isoformat()
        self._sync_workspace_state(db, project)
        return project_file

    def _register_file_path(self, db, project: Project, source_file: Path, role: str) -> ProjectFile:
        workspace_path = Path(project.workspace_path)
        safe_name = self._safe_filename(source_file.name)
        file_path = self._unique_raw_path(workspace_path, safe_name)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_file, file_path)

        return self._create_project_file_record(
            db=db,
            project=project,
            role=role,
            original_name=source_file.name,
            file_path=file_path,
            size_bytes=file_path.stat().st_size,
        )

    def _create_project_file_record(
        self,
        db,
        project: Project,
        role: str,
        original_name: str,
        file_path: Path,
        size_bytes: int,
    ) -> ProjectFile:
        workspace_path = Path(project.workspace_path)
        now = datetime.now().isoformat()
        project_file = ProjectFile(
            project_id=project.id,
            role=role,
            original_name=original_name,
            current_path=str(file_path.relative_to(workspace_path)),
            size_bytes=size_bytes,
            checksum=compute_file_checksum(file_path),
            status="uploaded",
            created_at=now,
            updated_at=now,
        )
        db.add(project_file)
        db.flush()
        return project_file

    def _sync_workspace_state(
        self,
        db,
        project: Project,
        *,
        schema_status: str = "not_started",
        completed_tasks: str | None = None,
        next_steps: str = "Run schema.infer and data.validate",
        extra_lines: list[str] | None = None,
    ) -> None:
        workspace_path = Path(project.workspace_path)
        manifest = ProjectManifest.load(workspace_path)
        project_files = db.query(ProjectFile).filter(ProjectFile.project_id == project.id).all()
        manifest.files = [
            FileEntry(
                file_id=f.id,
                role=f.role,
                original_name=f.original_name,
                current_path=f.current_path,
                checksum=f.checksum,
                schema_hash=f.schema_hash,
                status=f.status,
                last_verified_at=f.updated_at,
            )
            for f in project_files
        ]
        manifest.current_stage = project.current_stage or project.status
        manifest.version += 1
        manifest.save(workspace_path)

        file_status = "\n".join(
            f"- {f.role}: {f.original_name} ({f.status}, {f.checksum})"
            for f in project_files
        ) or "No data files"
        ContextSummaryWriter(workspace_path).write(
            project_name=project.name,
            current_stage=manifest.current_stage,
            file_status=file_status,
            schema_status=schema_status,
            completed_tasks=completed_tasks if completed_tasks is not None else ("data_ingest" if project_files else "none"),
            next_steps=next_steps,
        )
        if extra_lines:
            summary_path = workspace_path / ".analysis" / "context_summary.md"
            with open(summary_path, "a", encoding="utf-8") as f:
                f.write("\n\n" + "\n".join(extra_lines) + "\n")

    @staticmethod
    def _safe_filename(filename: str) -> str:
        safe_name = Path(filename).name.replace("/", "_").replace("\\", "_")
        return safe_name or "unknown.csv"

    @staticmethod
    def _unique_raw_path(workspace_path: Path, safe_name: str) -> Path:
        raw_dir = workspace_path / "data" / "raw"
        candidate = raw_dir / safe_name
        if not candidate.exists():
            return candidate

        stem = candidate.stem
        suffix = candidate.suffix
        index = 2
        while True:
            next_candidate = raw_dir / f"{stem}__{index}{suffix}"
            if not next_candidate.exists():
                return next_candidate
            index += 1

    @staticmethod
    def _guess_file_role(filename: str) -> str:
        name = filename.lower()
        if "order_info" in name or "order" in name:
            return "order_info"
        if "exposure_info" in name or "exposure" in name:
            return "exposure_info"
        if "activity_timeline" in name or "activity" in name or "timeline" in name:
            return "activity_timeline"
        return "unknown"

    def _resolve_source_dir(self, project: Project, source_path: Optional[str] = None) -> Path:
        selected_source = source_path or project.data_source_path
        if not selected_source:
            raise ValueError("No data source path configured")

        source_dir = Path(selected_source).expanduser().resolve()
        if not source_dir.is_absolute():
            raise ValueError("Data source path must be an absolute path")
        if not source_dir.exists():
            raise FileNotFoundError(f"Data source path does not exist: {source_dir}")
        if not source_dir.is_dir():
            raise ValueError(f"Data source path is not a directory: {source_dir}")
        return source_dir

    def _resolve_direct_child(self, source_dir: Path, source_path: str) -> Path:
        raw_path = Path(source_path).expanduser()
        candidate = raw_path if raw_path.is_absolute() else source_dir / raw_path
        candidate = candidate.resolve()
        if candidate.parent != source_dir:
            raise ValueError(f"Selected file must be a direct child of the source directory: {source_path}")
        return candidate

    def _build_source_candidate(self, child: Path) -> dict:
        stat = child.stat()
        base = {
            "name": child.name,
            "source_path": str(child.resolve()),
            "size_bytes": stat.st_size,
            "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "extension": child.suffix.lower(),
            "kind": "directory" if child.is_dir() else "file",
            "skipped": False,
            "skip_reason": None,
            "headers": [],
            "preview": "",
            "preview_truncated": False,
        }
        if child.is_dir():
            base["skipped"] = True
            base["skip_reason"] = "directory_not_scanned"
            return base
        if not child.is_file():
            base["skipped"] = True
            base["skip_reason"] = "not_a_file"
            return base
        if child.suffix.lower() != ".csv":
            base["skipped"] = True
            base["skip_reason"] = "unsupported_file_type"
            return base

        try:
            preview, truncated = self._read_csv_preview(child)
            headers = self._read_csv_headers(child)
            base["headers"] = headers
            base["preview"] = preview
            base["preview_truncated"] = truncated
        except Exception as e:
            base["skipped"] = True
            base["skip_reason"] = f"preview_failed:{e}"
        return base

    def _read_csv_preview(self, path: Path) -> tuple[str, bool]:
        data = path.read_bytes()
        truncated_by_bytes = len(data) > self.PREVIEW_BYTE_LIMIT
        sample = data[: self.PREVIEW_BYTE_LIMIT]
        text = sample.decode("utf-8-sig", errors="replace")
        lines = text.splitlines()
        truncated_by_lines = len(lines) > self.PREVIEW_LINE_LIMIT
        if truncated_by_lines:
            text = "\n".join(lines[: self.PREVIEW_LINE_LIMIT])
        return text, truncated_by_bytes or truncated_by_lines

    @staticmethod
    def _read_csv_headers(path: Path) -> list[str]:
        with open(path, newline="", encoding="utf-8-sig", errors="replace") as f:
            reader = csv.reader(f)
            return next(reader, [])
