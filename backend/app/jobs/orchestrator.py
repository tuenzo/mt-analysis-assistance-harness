import uuid
import json
from datetime import datetime
from typing import Optional
from app.tools.schemas import ToolResult
from app.projects.service import ProjectService
from app.core.database import get_session
from app.projects.models import Job


class JobOrchestrator:
    """长任务编排器"""

    def run_pipeline(self, project_id: str, pipeline_name: str, **kwargs) -> dict:
        """
        执行 pipeline，返回 Job 信息

        步骤:
        1. 创建 Job 记录 (status: queued)
        2. 执行 pipeline 逻辑
        3. 更新 Job 状态
        """
        service = ProjectService()
        project = service.get_project(project_id)
        if not project:
            return {"ok": False, "error": "Project not found"}
        if pipeline_name == "full_pipeline":
            return self._run_full_pipeline(project_id, kwargs)

        db = get_session()
        try:
            job = Job(
                id=f"job_{uuid.uuid4().hex[:12]}",
                project_id=project_id,
                action=pipeline_name,
                status="running",
                progress=0,
                input_json=json.dumps(kwargs, ensure_ascii=False),
                started_at=datetime.now().isoformat(),
                created_at=datetime.now().isoformat(),
            )
            db.add(job)
            db.commit()
            db.refresh(job)

            result = self._execute_pipeline(project_id, pipeline_name, kwargs)

            job.status = "succeeded" if result.ok else "failed"
            job.progress = 1
            job.output_json = json.dumps(result.model_dump(), ensure_ascii=False)
            job.finished_at = datetime.now().isoformat()
            db.commit()

            return {
                "ok": result.ok,
                "job_id": job.id,
                "result": result.model_dump(),
            }
        finally:
            db.close()

    def _run_full_pipeline(self, project_id: str, kwargs: dict) -> dict:
        db = get_session()
        try:
            from app.jobs.pipeline_runner import run_approved_full_pipeline

            result, events = run_approved_full_pipeline(
                db,
                project_id=project_id,
                session_id=str(kwargs.get("session_id") or ""),
                turn_id=str(kwargs.get("turn_id") or ""),
                tool_call=None,
                payload=kwargs,
            )
            job_id = next((event.get("job_id") for event in events if event.get("type") == "job_started"), "")
            return {
                "ok": result.ok,
                "job_id": job_id,
                "result": result.model_dump(),
            }
        finally:
            db.close()

    def _execute_pipeline(self, project_id: str, pipeline_name: str, kwargs: dict) -> ToolResult:
        if pipeline_name == "full_pipeline":
            from app.tools.analysis_tools import analysis_run_full_pipeline
            return analysis_run_full_pipeline(project_id, kwargs)
        elif pipeline_name == "panel_build":
            from app.tools.panel_tools import panel_build_category_day
            return panel_build_category_day(project_id, kwargs)
        elif pipeline_name == "diagnostics":
            from app.tools.analysis_tools import analysis_run_diagnostics
            return analysis_run_diagnostics(project_id, kwargs)
        elif pipeline_name == "localgap":
            from app.tools.analysis_tools import analysis_run_localgap
            return analysis_run_localgap(project_id, kwargs)
        elif pipeline_name == "psm_did":
            from app.tools.analysis_tools import analysis_run_psm_did
            return analysis_run_psm_did(project_id, kwargs)
        else:
            return ToolResult(
                ok=False,
                action=pipeline_name,
                summary="",
                error={"code": "UNKNOWN_PIPELINE", "message": f"Unknown pipeline: {pipeline_name}"},
            )

    def get_job_status(self, job_id: str) -> Optional[dict]:
        db = get_session()
        try:
            job = db.query(Job).filter(Job.id == job_id).first()
            if not job:
                return None
            return {
                "id": job.id,
                "project_id": job.project_id,
                "pipeline": job.action,
                "status": job.status,
                "created_at": job.created_at,
                "completed_at": job.finished_at,
                "result": json.loads(job.output_json) if job.output_json else None,
            }
        finally:
            db.close()
