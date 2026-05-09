import json

from app.projects.models import Artifact, Job, Project, ProjectFile
from app.core.database import get_session
from app.workspace.context_summary import ContextSummaryWriter
from app.core.config import resolve_project_path
from app.agent.python_env import discover_python_environment


AVAILABLE_ACTIONS = [
    "project.get_state",
    "data.discover_source_files",
    "data.ingest",
    "data.validate",
    "schema.infer",
    "schema.apply_mapping",
    "panel.build_category_day",
    "analysis.run_diagnostics",
    "analysis.run_psm_did",
    "analysis.run_localgap",
    "analysis.run_mechanism_regression",
    "analysis.run_conversion_diagnostics",
    "analysis.run_gps_uplift",
    "analysis.run_full_pipeline",
    "result.get_latest",
    "artifact.read",
    "chart.render",
    "report.generate",
    "memory.propose_update",
]


class ContextBuilder:
    def build(self, project_id: str, ui_context: dict | None = None) -> dict:
        db = get_session()
        try:
            project = db.query(Project).filter(Project.id == project_id).first()
            if not project:
                return {"error": "project_not_found"}

            files = db.query(ProjectFile).filter(ProjectFile.project_id == project_id).all()

            workspace_path = resolve_project_path(project.workspace_path)
            ctx_content = ""
            if workspace_path.exists():
                ctx_content = ContextSummaryWriter.read(workspace_path)

            files_info = [
                {"role": f.role, "path": f.current_path, "status": f.status}
                for f in files
            ]

            data_quality = "unknown"
            if files:
                all_validated = all(f.status == "validated" for f in files)
                any_uploaded = any(f.status == "uploaded" for f in files)
                data_quality = "validated" if all_validated else ("partial" if any_uploaded else "unknown")

            schema_status = "pending"
            if files:
                mapped_count = sum(1 for f in files if f.status == "mapped")
                schema_status = f"mapped ({mapped_count}/{len(files)})"

            latest_result = None
            result_path = workspace_path / ".analysis" / "latest_result.json"
            if result_path.exists():
                latest_result = json.loads(result_path.read_text(encoding="utf-8"))

            latest_job = (
                db.query(Job)
                .filter(Job.project_id == project_id, Job.action == "analysis.run_full_pipeline")
                .order_by(Job.created_at.desc(), Job.id.desc())
                .first()
            )
            latest_pipeline = None
            if latest_job:
                try:
                    output = json.loads(latest_job.output_json or "{}")
                except json.JSONDecodeError:
                    output = {}
                latest_pipeline = {
                    "job_id": latest_job.id,
                    "status": latest_job.status,
                    "progress": latest_job.progress,
                    "steps": output.get("steps", []),
                    "finished_at": latest_job.finished_at,
                }

            recent_artifacts = (
                db.query(Artifact)
                .filter(Artifact.project_id == project_id)
                .order_by(Artifact.created_at.desc(), Artifact.id.desc())
                .limit(12)
                .all()
            )

            return {
                "project_id": project.id,
                "project_name": project.name,
                "current_stage": project.current_stage,
                "workspace_path": str(workspace_path),
                "python_environment": discover_python_environment(workspace_path).as_dict(),
                "files": files_info,
                "data_quality": data_quality,
                "schema_status": schema_status,
                "latest_result": latest_result,
                "latest_result_available": list(latest_result.keys()) if isinstance(latest_result, dict) else [],
                "latest_pipeline": latest_pipeline,
                "recent_artifacts": [
                    {"type": a.type, "title": a.title, "path": a.path}
                    for a in recent_artifacts
                ],
                "ui_view": ui_context.get("active_view") if ui_context else "agent_command_center",
                "available_actions": AVAILABLE_ACTIONS,
                "context_summary": ctx_content,
            }
        finally:
            db.close()
