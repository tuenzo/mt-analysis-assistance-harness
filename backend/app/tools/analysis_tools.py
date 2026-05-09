from app.analysis.pipelines.diagnostics import run_diagnostics
from app.analysis.pipelines.gps_uplift import run_gps_uplift
from app.analysis.pipelines.localgap import run_localgap
from app.analysis.pipelines.mechanism_regression import run_conversion_diagnostics, run_mechanism_regression
from app.analysis.pipelines.psm_did import run_psm_did
from app.analysis.pipelines.user_week_hmm import run_hmm_state_path
from app.core.config import resolve_project_path
from app.projects.service import ProjectService
from app.tools.schemas import ToolResult


def analysis_run_diagnostics(project_id: str, payload: dict) -> ToolResult:
    service = ProjectService()
    project = service.get_project(project_id)
    if not project:
        return ToolResult(
            ok=False,
            action="analysis.run_diagnostics",
            summary="",
            error={"code": "NOT_FOUND", "message": "Project not found"},
        )

    workspace_path = resolve_project_path(project.workspace_path)
    return run_diagnostics(project_id, str(workspace_path))


def analysis_run_psm_did(project_id: str, payload: dict) -> ToolResult:
    service = ProjectService()
    project = service.get_project(project_id)
    if not project:
        return ToolResult(
            ok=False,
            action="analysis.run_psm_did",
            summary="",
            error={"code": "NOT_FOUND", "message": "Project not found"},
        )

    workspace_path = resolve_project_path(project.workspace_path)
    return run_psm_did(project_id, str(workspace_path))


def analysis_run_localgap(project_id: str, payload: dict) -> ToolResult:
    service = ProjectService()
    project = service.get_project(project_id)
    if not project:
        return ToolResult(
            ok=False,
            action="analysis.run_localgap",
            summary="",
            error={"code": "NOT_FOUND", "message": "Project not found"},
        )

    workspace_path = resolve_project_path(project.workspace_path)
    return run_localgap(project_id, str(workspace_path))


def analysis_run_mechanism_regression(project_id: str, payload: dict) -> ToolResult:
    service = ProjectService()
    project = service.get_project(project_id)
    if not project:
        return ToolResult(
            ok=False,
            action="analysis.run_mechanism_regression",
            summary="",
            error={"code": "NOT_FOUND", "message": "Project not found"},
        )

    workspace_path = resolve_project_path(project.workspace_path)
    return run_mechanism_regression(project_id, str(workspace_path))


def analysis_run_conversion_diagnostics(project_id: str, payload: dict) -> ToolResult:
    service = ProjectService()
    project = service.get_project(project_id)
    if not project:
        return ToolResult(
            ok=False,
            action="analysis.run_conversion_diagnostics",
            summary="",
            error={"code": "NOT_FOUND", "message": "Project not found"},
        )

    workspace_path = resolve_project_path(project.workspace_path)
    return run_conversion_diagnostics(project_id, str(workspace_path))


def analysis_run_gps_uplift(project_id: str, payload: dict) -> ToolResult:
    service = ProjectService()
    project = service.get_project(project_id)
    if not project:
        return ToolResult(
            ok=False,
            action="analysis.run_gps_uplift",
            summary="",
            error={"code": "NOT_FOUND", "message": "Project not found"},
        )

    workspace_path = resolve_project_path(project.workspace_path)
    return run_gps_uplift(project_id, str(workspace_path), payload)


def analysis_run_hmm_state_path(project_id: str, payload: dict) -> ToolResult:
    service = ProjectService()
    project = service.get_project(project_id)
    if not project:
        return ToolResult(
            ok=False,
            action="analysis.run_hmm_state_path",
            summary="",
            error={"code": "NOT_FOUND", "message": "Project not found"},
        )

    workspace_path = resolve_project_path(project.workspace_path)
    return run_hmm_state_path(project_id, str(workspace_path))


def analysis_run_full_pipeline(project_id: str, payload: dict) -> ToolResult:
    service = ProjectService()
    project = service.get_project(project_id)
    if not project:
        return ToolResult(
            ok=False,
            action="analysis.run_full_pipeline",
            summary="",
            error={"code": "NOT_FOUND", "message": "Project not found"},
        )

    from app.core.database import get_session
    from app.jobs.pipeline_runner import run_approved_full_pipeline

    db = get_session()
    try:
        result, _ = run_approved_full_pipeline(
            db,
            project_id=project_id,
            session_id=str(payload.get("session_id") or ""),
            turn_id=str(payload.get("turn_id") or ""),
            tool_call=None,
            payload=payload,
        )
        return result
    finally:
        db.close()
