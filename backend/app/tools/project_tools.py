from app.tools.schemas import ToolResult
from app.projects.service import ProjectService


def project_get_state(project_id: str, payload: dict) -> ToolResult:
    service = ProjectService()
    project = service.get_project(project_id)
    if not project:
        return ToolResult(ok=False, action="project.get_state", summary="", error={"code": "NOT_FOUND", "message": f"Project {project_id} not found"})
    state = service.get_project_state(project_id)
    return ToolResult(
        ok=True,
        action="project.get_state",
        summary=f"项目「{project.name}」当前阶段：{project.current_stage}",
        artifacts=[],
        state_patch={"current_stage": project.current_stage, "status": project.status},
        assistant_hint="你可以向用户解释当前项目状态。"
    )
